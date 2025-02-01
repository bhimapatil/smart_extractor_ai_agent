from fastapi import HTTPException, Depends
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import secrets
from config import settings

security = HTTPBasic()

# Static credentials (in production, these should be in environment variables)
admin_username = settings.admin_username
admin_password = settings.admin_password

def verify_auth(credentials: HTTPBasicCredentials = Depends(security)):
    is_username_correct = secrets.compare_digest(credentials.username, admin_username)
    is_password_correct = secrets.compare_digest(credentials.password, admin_password)
    
    if not (is_username_correct and is_password_correct):
        raise HTTPException(
            status_code=401,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username
