# Backend/core/config.py
import os
from typing import Optional 
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
from pathlib import Path
from passlib.context import CryptContext

dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env" 
load_dotenv(dotenv_path=dotenv_path)

class Settings(BaseSettings):
    PROJECT_NAME: str = "TDAI API"
    PROJECT_VERSION: str = "1.0.0"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./tdai_app.db") 
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey") 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", str(60 * 24 * 7))) 
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    MAIL_USERNAME: Optional[str] = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: Optional[str] = os.getenv("MAIL_FROM")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER: Optional[str] = os.getenv("MAIL_SERVER")
    MAIL_FROM_NAME: str = os.getenv("MAIL_FROM_NAME", "TDAI Suporte")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"
    USE_CREDENTIALS: bool = os.getenv("USE_CREDENTIALS", "True").lower() == "true"
    VALIDATE_CERTS: bool = os.getenv("VALIDATE_CERTS", "True").lower() == "true"
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000") 

    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI", f"{FRONTEND_URL}/auth/google/callback")

    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
    FACEBOOK_REDIRECT_URI: Optional[str] = os.getenv("FACEBOOK_REDIRECT_URI", f"{FRONTEND_URL}/auth/facebook/callback")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv("GOOGLE_GEMINI_API_KEY")
    OPENAI_ORG_ID: Optional[str] = os.getenv("OPENAI_ORG_ID") 

    DEFAULT_LIMIT_PRODUTOS_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_PRODUTOS_SEM_PLANO", 10))
    # CORREÇÃO DO TYPO APLICADA AQUI:
    DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO", 5)) 
    DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO", 20))
    
    UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "Backend/static/product_images") 

    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "adminpassword")


    class Config:
        pass

settings = Settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_settings() -> Settings:
    return settings