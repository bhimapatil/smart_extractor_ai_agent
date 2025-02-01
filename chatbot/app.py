from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi import APIRouter
from config import settings
from AI_Agent.agent import BedrockClient
from chatbot.utlity import extract_text_from_pdf, extract_text_from_excel
from collections import deque
from typing import Dict, List

router = APIRouter()
extracted_content = None
chat_history = deque(maxlen=10)  # Store last 10 conversations

@router.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    global extracted_content
    
    if file.content_type == "application/pdf":
        extracted_content = extract_text_from_pdf(file)
    elif file.content_type in ["application/vnd.ms-excel", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"]:
        extracted_content = extract_text_from_excel(file)
  
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    return JSONResponse(content={"message": "File uploaded successfully", "extracted_text": extracted_content[:500]})

@router.post("/chat/")
async def chat_with_file(query: str):
    if not extracted_content:
        raise HTTPException(status_code=400, detail="No content available. Upload a file first.")
    
    client = BedrockClient(access_key=settings.bedrock_access_key,secret_key=settings.bedrock_secret_access_key,)
    
    prompt = f"Context: {extracted_content}\n\nQuestion: {query}\n\nPlease provide a response based on the context above."
    response = client.get_response_from_bedrock(prompt)
    
    if not response:
        raise HTTPException(status_code=500, detail="Failed to get response from Bedrock")
    
    # Store the conversation in chat history
    chat_history.append({
        "query": query,
        "response": response,
    })
    return JSONResponse(content={"response": response})

@router.get("/chat-history/")
async def get_chat_history():
    """Retrieve the last 10 conversations."""
    return JSONResponse(content={"history": list(chat_history)})