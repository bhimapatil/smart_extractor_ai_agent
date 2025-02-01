from enum import Enum
import os
import tempfile
from typing import Optional, Union, Dict, Any
import pdfplumber
import pandas as pd
from fastapi import UploadFile
import aiofiles
from pathlib import Path
from AI_Agent.prompt_builder import text_extractor_prompt_builder
from AI_Agent.agent import BedrockClient
from config import settings

client = BedrockClient(access_key=settings.bedrock_access_key,secret_key=settings.bedrock_secret_access_key,)





async def save_upload_file_temporarily(upload_file: UploadFile) -> Path:
    """Save an upload file temporarily and return the path."""
    try:
        suffix = Path(upload_file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            async with aiofiles.open(tmp.name, 'wb') as out_file:
                content = await upload_file.read()
                await out_file.write(content)
            return Path(tmp.name)
    except Exception as e:
        raise RuntimeError(f"Error saving temporary file: {str(e)}")

async def extract_text_from_pdf(file: UploadFile) -> str:
    """Extract text from PDF files."""
    try:
        temp_path = await save_upload_file_temporarily(file)
        text = []
        with pdfplumber.open(temp_path) as pdf:
            for page in pdf.pages:
                extracted = page.extract_text()
                if extracted:
                    text.append(extracted)
        return "\n".join(text).strip()
    finally:
        if 'temp_path' in locals():
            os.unlink(temp_path)

async def extract_text_from_excel(file: UploadFile) -> str:
    """Extract text from Excel files."""
    try:
        temp_path = await save_upload_file_temporarily(file)
        df = pd.read_excel(temp_path)
        return df.to_string(index=False)
    finally:
        if 'temp_path' in locals():
            os.unlink(temp_path)

async def extract_text_from_csv(file: UploadFile) -> str:
    """Extract text from CSV files."""
    try:
        temp_path = await save_upload_file_temporarily(file)
        df = pd.read_csv(temp_path)
        return df.to_string(index=False)
    finally:
        if 'temp_path' in locals():
            os.unlink(temp_path)

async def extract_text_from_doc(file: UploadFile) -> str:
    """Extract text from DOC files."""
    try:
        content = await file.read()
        return content.decode('utf-8', errors='ignore')
    except Exception as e:
        raise RuntimeError(f"Error processing DOC file: {str(e)}")

async def extract_text_from_image(file: UploadFile) -> str:
    """Extract text from image files using Bedrock client."""
    try:
        temp_path = await save_upload_file_temporarily(file)
        
        if not file.content_type.startswith("image/"):
            raise ValueError("File must be an image")

        prompt = text_extractor_prompt_builder()  # Assuming this function exists
        response = client.get_response_from_bedrock(prompt, str(temp_path))  # Assuming client exists

        if isinstance(response, str):
            extracted_text = response.replace("Here's the extracted text from the image:", "").strip()
        elif isinstance(response, dict) and "content" in response:
            if isinstance(response["content"], list):
                extracted_text = response["content"][0].get("text", "").strip()
            else:
                extracted_text = str(response["content"]).strip()
        else:
            extracted_text = str(response).strip()

        if not extracted_text:
            raise ValueError("No text extracted from the image")

        return extracted_text

    except Exception as e:
        raise RuntimeError(f"Error processing image: {str(e)}")
    finally:
        if 'temp_path' in locals():
            os.unlink(temp_path)