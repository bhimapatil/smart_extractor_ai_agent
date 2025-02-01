import os
import sys
import tempfile
from fastapi import UploadFile, File, HTTPException, APIRouter, BackgroundTasks, Depends
from pydantic_core import ValidationError
from starlette.responses import JSONResponse, PlainTextResponse
from AI_Agent.prompt_builder import build_prompt, text_extractor_prompt_builder, static_field_extractor
from API.utility import PromptRequest, temp_dir, handle_table_operations, process_images_in_background, extract_zip, validate_extracted_data
from db.db import engine
from db.table_handler import TableData
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import settings
from AI_Agent.agent import BedrockClient
from auth.auth_handler import verify_auth


router = APIRouter()

client = BedrockClient(access_key=settings.bedrock_access_key,secret_key=settings.bedrock_secret_access_key,)

temp_dir = tempfile.TemporaryDirectory()


@router.post("/generate-response")
async def generate_response(
    request: PromptRequest,
    username: str = Depends(verify_auth)):
    try:
        print("request",request)
        table_name = request.table_name.strip()
        columns = request.columns  # This is now a dictionary
        input_text = request.input_text.strip()
        if not table_name:
            raise HTTPException(
                status_code=400,
                detail="Table name cannot be empty. Please provide a valid table name."
            )
        if not columns or not isinstance(columns, dict):
            raise HTTPException(
                status_code=400,
                detail="Columns cannot be empty and must be a dictionary with column names as keys and their types as values."
            )
        if not input_text:
            raise HTTPException(
                status_code=400,
                detail="Input text cannot be empty. Please provide the input text."
            )
        # Validate 'relation' type columns in the dictionary
        for column_name, column_info in columns.items():
            if isinstance(column_info, dict):
                data_type = column_info.get("data_type")
                if data_type == "relation":
                    reference_table = column_info.get("reference_table")
                    print("reference_table",reference_table)
                    on_column_name = column_info.get("on_column_name")
                    print("on_column_name",on_column_name)
                    if not reference_table or not on_column_name:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Column '{column_name}' is of type 'relation'. "
                                "Please provide 'reference_table' and 'on_column_name' for this column."
                            )
                        )

        # Build the prompt using the dictionary structure
        prompt = build_prompt(table_name, columns, input_text)
        print("Final prompt:", prompt)

        response = client.get_response_from_bedrock(prompt)
        print(response)
        if not response:
            raise HTTPException(status_code=500, detail="Failed to generate a response from the external service.")
        return {"response": response}

    except ValidationError as ve:
        # Handles validation errors from Pydantic
        raise HTTPException(status_code=422, detail=ve.errors())
    except Exception as e:
        # Catch-all for other exceptions
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")







@router.post("/upload-and-extract-text/")
async def upload_and_extract_text(
    file: UploadFile = File(...),
    username: str = Depends(verify_auth)
):
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
        prompt = text_extractor_prompt_builder()
        response = client.get_response_from_bedrock(prompt, file_path)
        print("Response from Bedrock:", response)  # Debugging line

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

        if not extracted_text:
            raise HTTPException(status_code=500, detail="No text extracted from the image.")

        return PlainTextResponse(content=extracted_text)

    except HTTPException as e:
        raise e
    except Exception as e:
        import traceback
        error_message = f"An error occurred: {str(e)}\n{traceback.format_exc()}"
        print(error_message)  # Log the full error for debugging
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/push-data/")
async def push_data(
    payload: TableData,
    username: str = Depends(verify_auth)
):
    try:
        table_name = payload.table_name
        print("table_name",table_name)
        data = payload.data
        print("data",data)
        column_definitions = payload.column_definitions
        print("column_definitions",column_definitions)
        create_new = payload.create_new

        # Validation
        if not table_name or not data:
            raise HTTPException(status_code=422, detail="Table name and data are required.")
        if create_new and not column_definitions:
            raise HTTPException(
                status_code=422,
                detail="Column definitions are required to create a new table.",
            )

        # Call the handler
        result = handle_table_operations(engine, data, column_definitions, table_name)
        print("result",result)
        return {"message": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")



@router.post("/preprocess-text")
async def preprocess_text_api(
    file: UploadFile = File(...),
    username: str = Depends(verify_auth)
):
    try:
        if file.content_type != "text/plain":
            raise HTTPException(status_code=400, detail="Only plain text files are allowed.")
        content = await file.read()
        if len(content) > 2 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="File size exceeds 2MB limit.")
        text_data = content.decode("utf-8")
        processed_data = text_data.upper()
        return {"processed_data": processed_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from uuid import uuid4
from API.utility import update_task_status, get_task_status

@router.post("/process-bulk-images/")
async def process_images(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    username: str = Depends(verify_auth)
):
    try:
        if not file.filename.endswith(".zip"):
            raise HTTPException(status_code=400, detail="Uploaded file must be a .zip file")
        
        # Generate unique task ID
        task_id = str(uuid4())
        
        # Extract zip file
        extract_zip(file)
        
        # Get prompt for field extraction
        prompt = static_field_extractor()
        
        # Start background processing (validation happens automatically after processing)
        background_tasks.add_task(
            process_images_in_background,
            task_id,
            "./images",
            prompt
        )
        
        return {
            "status": "processing",
            "message": "Processing started (validation will run automatically after processing)",
            "task_id": task_id
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing images: {str(e)}")

@router.get("/process-status/{task_id}")
async def get_processing_status(
    task_id: str,
    username: str = Depends(verify_auth)
):
    """Get the status of a background processing task"""
    status = get_task_status(task_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    return status



@router.get("/validation-results/{task_id}")
async def get_validation_results(
    task_id: str,
    username: str = Depends(verify_auth)
):
    """Get the validation results for a specific task"""
    status = get_task_status(task_id)
    if status["status"] == "not_found":
        raise HTTPException(status_code=404, detail="Task not found")
    
    if "validation_results" not in status:
        return {
            "status": "pending",
            "message": "Validation not completed yet"
        }
    
    return {
        "status": "completed",
        "validation_results": status["validation_results"]
    }