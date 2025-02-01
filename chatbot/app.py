from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi import APIRouter
from AI_Agent.agent import BedrockClient
from auth.auth_handler import verify_auth
from collections import deque
from typing import Dict, List, Iterator, Any
import json
import asyncio
from chatbot.utlity import extract_text_from_image, extract_text_from_pdf, extract_text_from_excel, extract_text_from_csv, extract_text_from_doc,client
from enum import Enum


router = APIRouter()
extracted_content = None
chat_history = deque(maxlen=10)


class SupportedMimeTypes(str, Enum):
    PDF = "application/pdf"
    EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    EXCEL_LEGACY = "application/vnd.ms-excel"
    CSV = "text/csv"
    DOC = "application/msword"



@router.post("/upload/")
async def upload_file(
    file: UploadFile = File(...),
    username: str = Depends(verify_auth)) -> Dict[str, Any]:
   
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        content_type = file.content_type or ""
        
        # Map content types to extraction functions
        extractors = {
            SupportedMimeTypes.PDF: extract_text_from_pdf,
            SupportedMimeTypes.EXCEL: extract_text_from_excel,
            SupportedMimeTypes.EXCEL_LEGACY: extract_text_from_excel,
            SupportedMimeTypes.CSV: extract_text_from_csv,
            SupportedMimeTypes.DOC: extract_text_from_doc,
        }

        if content_type.startswith("image/"):
            extracted_content = await extract_text_from_image(file)
        else:
            if content_type not in extractors:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {content_type}"
                )
            
            extracted_content = await extractors[content_type](file)

        if not extracted_content:
            raise HTTPException(
                status_code=422,
                detail="Failed to extract content from file"
            )

        return JSONResponse(content={
            "message": "File processed successfully",
            "filename": file.filename,
            "content_type": content_type,
            "extracted_text": extracted_content,  
            "total_length": len(extracted_content)
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    



@router.post("/chat/")
async def chat_with_file(
    query: str,
    username: str = Depends(verify_auth)
):
    if not extracted_content:
        raise HTTPException(status_code=400, detail="No content available. Upload a file first.")
    prompt = f"Context: {extracted_content}\n\nQuestion: {query}\n\nPlease provide a response based on the context above."

    async def generate_stream():
        full_response = ""
        buffer = ""
        
        for chunk in client.get_response_streaming_from_bedrock(prompt):
            if chunk:
                buffer += chunk
                # Stream complete sentences or phrases
                if any(c in buffer for c in ['.', '!', '?', '\n']):
                    await asyncio.sleep(0.3)  # Add 300ms delay between chunks
                    yield json.dumps({
                        "chunk": buffer,
                        "status": "streaming"
                    }) + "\n"
                    full_response += buffer
                    buffer = ""
        
        # Send any remaining buffer
        if buffer:
            await asyncio.sleep(0.3)  # Add delay for final chunk
            yield json.dumps({
                "chunk": buffer,
                "status": "streaming"
            }) + "\n"
            full_response += buffer
        
        # Store the complete response in chat history
        chat_history.append({
            "query": query,
            "response": full_response,
        })
        # Send end message
        yield json.dumps({"status": "done"}) + "\n"

    return StreamingResponse(
        generate_stream(),
        media_type="application/x-ndjson"
    )

@router.get("/chat-history/")
async def get_chat_history(username: str = Depends(verify_auth)):
    """Retrieve the last 10 conversations."""
    return JSONResponse(content={"history": list(chat_history)})
