# Backend/core/config.py
import os
from typing import Optional
from dotenv import load_dotenv

# Importações atualizadas para Pydantic v2 e pydantic-settings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import EmailStr, PostgresDsn, AnyHttpUrl

from passlib.context import CryptContext # <--- ADICIONADO: Importar CryptContext

load_dotenv()

# Definição do pwd_context para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto") # <--- ADICIONADO

class Settings(BaseSettings):
    PROJECT_NAME: str = "TDAI Backend"
    PROJECT_VERSION: str = "0.1.0"
    
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/tdai_db")
    TEST_DATABASE_URL: str = os.getenv("TEST_DATABASE_URL", "postgresql://user:password@localhost:5432/tdai_test_db")
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "supersecretkey")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7 # 7 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30 # 30 days

    # Email settings
    MAIL_USERNAME: Optional[str] = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: Optional[EmailStr] = os.getenv("MAIL_FROM") 
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", "587")) 
    MAIL_SERVER: Optional[str] = os.getenv("MAIL_SERVER")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() in ("true", "1", "t")
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() in ("true", "1", "t")
    
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    # OpenAI API Key
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    OPENAI_ORG_ID: Optional[str] = os.getenv("OPENAI_ORG_ID")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore' 
    )

settings = Settings()

if settings.GOOGLE_REDIRECT_URI is None and settings.FRONTEND_URL:
    settings.GOOGLE_REDIRECT_URI = f"{settings.FRONTEND_URL}/auth/google/callback"