from pydantic_settings import BaseSettings
from dotenv import load_dotenv
load_dotenv(verbose=True)

class Settings(BaseSettings):
    bedrock_access_key:str
    bedrock_secret_access_key:str
    mysql_database_url:str
    admin_username:str
    admin_password:str

    class Config:
        env_file = ".env"

settings = Settings()