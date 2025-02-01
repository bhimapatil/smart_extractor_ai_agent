import os
import tempfile
from tkinter import Image
import traceback
from fastapi import HTTPException, UploadFile, File
from pydantic import BaseModel, Field
from typing import Dict, Union
from AI_Agent.agent import BedrockClient
from AI_Agent.agents_client import BedrockAgent
from common_utilty.utility import ImageProcessor
from config import settings
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import Integer, String, Float, DateTime, VARCHAR, BOOLEAN, TEXT, DATE, TIME, DECIMAL, SMALLINT, \
    MetaData, inspect, create_engine, Table, Column, ForeignKey


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



def process_images_in_background(folder_location: str, prompt: str):
    processor = ImageProcessor(
        folder_paths=[folder_location],
        prompt_template=prompt,
        max_workers=5
    )
    results_df = processor.process_images()
    results_df.to_csv("processed_images.csv", index=False)
    if results_df.empty:
        print("No images processed.")
        return
    results = results_df.to_dict(orient="records")
    print("Processed results:", results)








