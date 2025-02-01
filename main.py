import time
import uvicorn
from fastapi import FastAPI,Request
from API.app import router as agent_router
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.middleware.cors import CORSMiddleware
from chatbot.app import router as chatbot_router



app = FastAPI( )
app.include_router(agent_router, tags=["agent_router"])
app.include_router(chatbot_router, tags=["chatbot_router"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:63342","http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("prompt/health")
async def heath_check_api():
   return {"success":True}

if __name__ == '__main__':
    uvicorn.run('main:app', host="127.0.0.1", port=8089)