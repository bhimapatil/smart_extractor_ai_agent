import time
import uvicorn
from fastapi import FastAPI, Request, Depends
from fastapi.security import HTTPBasic
from API.app import router as agent_router
import os, sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from fastapi.middleware.cors import CORSMiddleware
from chatbot.app import router as chatbot_router
from auth.auth_handler import verify_auth


app = FastAPI() 
security = HTTPBasic()
app.include_router(agent_router, tags=["agent_router"])
app.include_router(chatbot_router, tags=["chatbot_router"])
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],
)


# Protected health check
@app.get("/prompt/health")
async def heath_check_api(username: str = Depends(verify_auth)):
    return {"success": True}

# Corrected single Uvicorn run
if __name__ == '__main__':
    uvicorn.run('main:app', host="0.0.0.0", port=8089)