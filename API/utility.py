import os
import shutil
import tempfile
import traceback
import zipfile
from datetime import datetime
from io import BytesIO
from tkinter import Image
from typing import Dict, Union, List, Any
import pandas as pd
from pandas import DataFrame
from fastapi import HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import Integer, String, Float, DateTime, VARCHAR, BOOLEAN, TEXT, DATE, TIME, DECIMAL, SMALLINT, \
    MetaData, inspect, Table, Column, ForeignKey
from sqlalchemy.exc import SQLAlchemyError
from AI_Agent.agent import BedrockClient
from common_utilty.utility import ImageProcessor
from config import settings
import json
from typing import Dict



class ColumnRelation(BaseModel):
    data_type: str
    reference_table: str
    on_column_name: str
    column_definition:str

class PromptRequest(BaseModel):
    table_name: str
    columns: Dict[str, Union[str, ColumnRelation]]  # Allow both simple types and relation columns
    input_text: str

client = BedrockClient(access_key=settings.bedrock_access_key,secret_key=settings.bedrock_secret_access_key,)



def convert_image_to_png(input_image_path, output_image_path="temp_image.png"):
    try:
        with Image.open(input_image_path) as img:
            img = img.convert("RGB")
            img.save(output_image_path, format="PNG")
            print(f"Image converted to PNG and saved as {output_image_path}.")
            return output_image_path
    except Exception as e:
        print(f"Error converting image to PNG: {str(e)}")
        return None


temp_dir = tempfile.TemporaryDirectory()

async def extract_text_from_image_with_bedrock(file: UploadFile = File(...)) -> str:
    try:
        # Check if the file is an image
        if not file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="File must be an image.")

        # Save the uploaded file to a temporary directory
        file_path = os.path.join(temp_dir.name, file.filename)
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Process the file with Bedrock client
        prompt = "extract text from given image"
        response = client.get_response_from_bedrock(prompt, file_path)

        # Handle the response based on its type
        if isinstance(response, str):
            # If response is a string, use it directly
            extracted_text = response.replace("Here's the extracted text from the image:", "").strip()
        elif isinstance(response, dict) and "content" in response:
            # Handle the dictionary format if that's what Bedrock returns
            if isinstance(response["content"], list):
                extracted_text = response["content"][0].get("text", "").strip()
            else:
                extracted_text = str(response["content"]).strip()
        else:
            # If response is in an unexpected format, try to convert it to string
            extracted_text = str(response).strip()

        # Check if text was successfully extracted
        if not extracted_text:
            raise HTTPException(status_code=500, detail="No text extracted from the image.")

        return extracted_text

    except Exception as e:
        # Log the full error for debugging
        error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        print(error_message)
        raise HTTPException(status_code=500, detail=f"Error extracting text from image: {str(e)}")



# Type mapping for SQLAlchemy column types
type_mapping = {
    "String": String(255),
    "VARCHAR": VARCHAR(255),
    "Integer": Integer,
    "Int": Integer,
    "Float": Float,
    "DateTime": DateTime,
    "Boolean": BOOLEAN,
    "Text": TEXT,
    "Date": DATE,
    "Time": TIME,
    "Decimal": DECIMAL(10, 2),
    "SmallInt": SMALLINT,
    "BigInt": Integer,
    "TINYINT": Integer,
    "BLOB": String,
    "CHAR": String(1),
}


def handle_table_operations(engine, data, table_schema, table_name, reference_info=None):
    metadata = MetaData()
    inspector = inspect(engine)

    try:
        # Check if the reference table exists and validate data if applicable
        if reference_info:
            reference_table = reference_info.get("reference_table")
            reference_column = reference_info.get("reference_column")
            reference_value = reference_info.get("reference_value")

            if reference_table and reference_column and reference_value:
                if reference_table not in inspector.get_table_names():
                    raise ValueError(f"Reference table '{reference_table}' does not exist.")

                # Validate reference value exists in the reference table
                with engine.connect() as conn:
                    query = f"SELECT * FROM {reference_table} WHERE {reference_column} = :value"
                    result = conn.execute(query, {"value": reference_value}).fetchone()
                    if not result:
                        raise ValueError(
                            f"Reference value '{reference_value}' not found in table '{reference_table}'."
                        )

        # Exclude unwanted columns from schema and data
        excluded_columns = {"reference_table", "on_column_name"}
        filtered_schema = {
            col: dtype for col, dtype in table_schema.items() if col not in excluded_columns
        }

        # Check if the table exists
        if table_name in inspector.get_table_names():
            print(f"Table '{table_name}' exists. Checking schema...")
            existing_columns = {
                col['name']: col['type'].__visit_name__ for col in inspector.get_columns(table_name)
            }

            # Identify schema differences
            schema_diff = {
                col: dtype for col, dtype in filtered_schema.items()
                if col not in existing_columns or existing_columns[col] != dtype
            }

            if schema_diff:
                return {"message": "Schema mismatch found.", "differences": schema_diff}

            print(f"Schema matches for '{table_name}'. Proceeding with insertion...")
        else:
            print(f"Table '{table_name}' does not exist. Creating table...")

            # Create table with filtered schema
            columns = [
                Column(name, type_mapping.get(dtype, String(255)))
                for name, dtype in filtered_schema.items()
            ]
            if reference_info:
                # Add a ForeignKey column if there's a reference
                columns.append(
                    Column(reference_info["reference_column"], Integer,
                           ForeignKey(f"{reference_info['reference_table']}.id"))
                )
            table = Table(table_name, metadata, *columns)
            metadata.create_all(engine)

        # Filter out excluded columns from data before insertion
        filtered_data = [
            {k: v for k, v in row.items() if k not in excluded_columns}
            for row in data
        ]

        # Insert data into the table
        with engine.connect() as conn:
            with conn.begin() as transaction:
                table = Table(table_name, metadata, autoload_with=engine)
                print(f"Inserting data: {filtered_data}")
                result = conn.execute(table.insert(), filtered_data)
                print(f"Rows inserted: {result.rowcount}")
                transaction.commit()

        return {"message": f"Data inserted into '{table_name}' successfully."}

    except SQLAlchemyError as e:
        return {"error": str(e)}
    except ValueError as ve:
        return {"validation_error": str(ve)}





# def process_invoice_data(result):
#     data = []
#     for entry in result:
#         invoice = entry["invoice_data"]
#         for item in invoice["items"]:
#             data.append({
#                 "Image Path": entry["image_path"],
#                 "Filename": entry["filename"],
#                 "Invoice Number": invoice["invoice_number"],
#                 "Invoice Date": invoice["invoice_date"],
#                 "Company Name": invoice["company_name"],
#                 "Company Address": invoice["company_address"],
#                 "Company Phone": invoice["company_phone"],
#                 "Company Email": invoice["company_email"],
#                 "Company Website": invoice["company_website"],
#                 "Item": item["item"],
#                 "Quantity": item["quantity"],
#                 "Price": item["price"],
#                 "Total": item["total"],
#                 "Tax": invoice["tax"],
#                 "Discount": invoice["discount"],
#                 "Grand Total": invoice["grand_total"],
#                 "Due Date": invoice["due_date"],
#                 "Payment Terms": invoice["payment_terms"],
#                 "Notes": invoice["notes"]
#             })

#     return pd.DataFrame(data)



def process_extracted_fields(results: List[Dict[str, Any]]) -> DataFrame:
    """Process extracted fields and convert to DataFrame with flattened structure"""
    flattened_data = []
    
    for result in results:
        try:
            # Parse the JSON result if it's a string
            data = result if isinstance(result, dict) else json.loads(result)
            
            # Create a flat dictionary for each document - removed specified fields
            flat_dict = {
                'document_type': data.get('metadata', {}).get('document_type'),
                'invoice_number': data.get('invoice_details', {}).get('invoice_number'),
                'invoice_date': data.get('invoice_details', {}).get('invoice_date'),
                'due_date': data.get('invoice_details', {}).get('due_date'),
                'subtotal': data.get('amounts', {}).get('subtotal'),
                'tax': data.get('amounts', {}).get('tax'),
                'discount': data.get('amounts', {}).get('discount'),
                'shipping': data.get('amounts', {}).get('shipping'),
                'total': data.get('amounts', {}).get('total'),
                'company_name': data.get('company', {}).get('name'),
                'street': data.get('company', {}).get('address', {}).get('street'),
                'city': data.get('company', {}).get('address', {}).get('city'),
                'state': data.get('company', {}).get('address', {}).get('state'),
                'postal_code': data.get('company', {}).get('address', {}).get('postal_code'),
                'country': data.get('company', {}).get('address', {}).get('country'),
                'phone': data.get('company', {}).get('contact', {}).get('phone'),
                'email': data.get('company', {}).get('contact', {}).get('email'),
                'website': data.get('company', {}).get('contact', {}).get('website'),
                'tax_id': data.get('company', {}).get('tax_id'),
                'notes': data.get('notes'),
                'payment_method': data.get('payment_info', {}).get('payment_method')
            }
            
            # Handle line items separately
            line_items = data.get('line_items', [])
            if line_items:
                for item in line_items:
                    item_dict = flat_dict.copy()
                    item_dict.update({
                        'item': item.get('item'),
                        'description': item.get('description'),
                        'quantity': item.get('quantity'),
                        'unit_price': item.get('unit_price'),
                        'line_total': item.get('total')
                    })
                    flattened_data.append(item_dict)
            else:
                flattened_data.append(flat_dict)
                
        except Exception as e:
            print(f"Error processing result: {e}")
            continue
    # Create DataFrame
    df = pd.DataFrame(flattened_data)
    if not os.path.exists("extracted_data"):
        os.makedirs("extracted_data")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = os.path.join("extracted_data","processed_data.csv")
    print(f"Saving processed data to {csv_filename}")

    df.to_csv(csv_filename, index=False)
    print(f"Data saved to {csv_filename}")
    return df

background_tasks: Dict[str, Dict] = {}

def update_task_status(task_id: str, status: str, message: str = None, result: dict = None, validation_results: dict = None):
    """Updated to include validation results"""
    background_tasks[task_id] = {
        "status": status,
        "message": message,
        "result": result,
        "validation_results": validation_results,
        "timestamp": datetime.now().isoformat()
    }

def get_task_status(task_id: str) -> dict:
    """Get the status of a background task"""
    return background_tasks.get(task_id, {"status": "not_found"})

def process_images_in_background(task_id: str, folder_location: str, prompt: str):
    """Modified to handle background processing with status updates and automatic validation"""
    try:
        update_task_status(task_id, "processing", "Starting image processing...")
        
        processor = ImageProcessor(
            folder_paths=[folder_location],
            prompt_template=prompt,
            max_workers=5
        )
        results = processor.process_images()
        
        if results:
            df = process_extracted_fields(results)
            print("Processed results shape:", df.shape)
            
            # Clean up the images directory
            output_dir = "images"
            try:
                for filename in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print(f"Successfully cleaned up {output_dir} directory")
            except Exception as e:
                print(f"Error cleaning up {output_dir} directory: {str(e)}")
            
            result_data = {
                "rows_processed": len(df),
                "columns": list(df.columns),
                "preview": df.head(5).to_dict(orient='records')
            }
            update_task_status(task_id, "completed", "Processing completed successfully", result_data)
            return df
        else:
            update_task_status(task_id, "completed", "No images processed")
            return pd.DataFrame()
            
    except Exception as e:
        error_msg = f"Error during processing: {str(e)}"
        update_task_status(task_id, "failed", error_msg)
        raise e












def validate_extracted_data(task_id: str) -> Dict[str, Any]:
    """Validates extracted data against master data. This is a synchronous function."""
    try:
        task_status = get_task_status(task_id)
        if task_status["status"] != "completed":
            return {"status": "validation_pending", "message": "Waiting for processing to complete"}
        
        try:
            master_df = pd.read_csv("extracted_data_20250202_004225.csv")
            # Group master data by invoice_number and get first occurrence of totals
            master_grouped = master_df.groupby('invoice_number').agg({
                'subtotal': 'first',
                'tax': 'first',
                'total': 'first'
            }).reset_index()
        except FileNotFoundError:
            return {"status": "error", "message": "Master data file not found"}

        try:
            processed_df = pd.read_csv("extracted_data/processed_data.csv")
            # Group processed data by invoice_number and get first occurrence of totals
            processed_grouped = processed_df.groupby('invoice_number').agg({
                'subtotal': 'first',
                'tax': 'first',
                'total': 'first'
            }).reset_index()
        except FileNotFoundError:
            return {"status": "error", "message": "Processed data file not found"}

        if processed_grouped.empty:
            return {"status": "error", "message": "Processed data is empty"}

        validation_results = []
        
        # Validate at invoice level using grouped data
        for _, row in processed_grouped.iterrows():
            try:
                invoice_num = str(row['invoice_number'])
                
                validation_record = {
                    "invoice_number": invoice_num,
                    "is_valid": True,
                    "discrepancies": [],
                    "totals": {
                        "master": {},
                        "processed": {},
                        "differences": {}
                    },
                    "line_items": []
                }

                # Find matching invoice in master data
                master_row = master_grouped[master_grouped['invoice_number'].astype(str) == invoice_num]
                if master_row.empty:
                    validation_record["is_valid"] = False
                    validation_record["discrepancies"].append("Invoice not found in master data")
                    validation_results.append(validation_record)
                    continue

                master_row = master_row.iloc[0]

                # Validate invoice totals
                for field in ['subtotal', 'tax', 'total']:
                    try:
                        master_value = float(master_row[field]) if pd.notnull(master_row[field]) else 0.0
                        processed_value = float(row[field]) if pd.notnull(row[field]) else 0.0
                        
                        validation_record["totals"]["master"][field] = master_value
                        validation_record["totals"]["processed"][field] = processed_value
                        validation_record["totals"]["differences"][field] = abs(master_value - processed_value)

                        if abs(master_value - processed_value) > 0.01:
                            validation_record["is_valid"] = False
                            validation_record["discrepancies"].append(
                                f"{field} mismatch: master={master_value}, processed={processed_value}"
                            )
                    except (ValueError, TypeError) as e:
                        validation_record["is_valid"] = False
                        validation_record["discrepancies"].append(f"Error comparing {field}: {str(e)}")

                # Get line items for this invoice
                master_items = master_df[master_df['invoice_number'] == invoice_num]
                processed_items = processed_df[processed_df['invoice_number'] == invoice_num]

                # Validate line items
                for _, p_item in processed_items.iterrows():
                    item_match = master_items[master_items['item'] == p_item['item']]
                    item_validation = {
                        "item": p_item['item'],
                        "quantity": {
                            "master": float(item_match['quantity'].iloc[0]) if not item_match.empty else None,
                            "processed": float(p_item['quantity'])
                        },
                        "unit_price": {
                            "master": float(item_match['unit_price'].iloc[0]) if not item_match.empty else None,
                            "processed": float(p_item['unit_price'])
                        },
                        "line_total": {
                            "master": float(item_match['line_total'].iloc[0]) if not item_match.empty else None,
                            "processed": float(p_item['line_total'])
                        }
                    }
                    validation_record["line_items"].append(item_validation)

                validation_results.append(validation_record)
            except Exception as e:
                print(f"Error processing invoice {invoice_num}: {str(e)}")
                continue

        # Create summary
        summary = {
            "total_invoices": len(validation_results),
            "valid_invoices": sum(1 for r in validation_results if r["is_valid"]),
            "invalid_invoices": sum(1 for r in validation_results if not r["is_valid"]),
            "invoices_with_discrepancies": len([r for r in validation_results if r["discrepancies"]])
        }

        return {
            "status": "validation_completed",
            "summary": summary,
            "validation_results": validation_results
        }

    except Exception as e:
        print(f"Debug: Validation error occurred: {str(e)}")
        return {
            "status": "validation_failed",
            "message": str(e),
            "error_details": traceback.format_exc()
        }

def save_image(image_data: BytesIO) -> str:
    output_dir = "images"
    os.makedirs(output_dir, exist_ok=True)
    base_filename = "invoice"
    filename = f"{base_filename}-{datetime.now().timestamp()}.png"
    file_path = os.path.join(output_dir, filename)
    
    with open(file_path, "wb") as f:
        f.write(image_data.getvalue())
    return filename

def extract_zip(file: UploadFile) -> list:
    extracted_images = []
    with zipfile.ZipFile(BytesIO(file.file.read())) as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.lower().endswith(('png', 'jpg', 'jpeg')):
                saved_filename = save_image(BytesIO(zip_ref.read(file_name)))
    return extracted_images