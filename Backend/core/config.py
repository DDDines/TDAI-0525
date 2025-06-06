# Backend/core/config.py
import os
from dotenv import load_dotenv
from typing import List, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, ValidationError, Field
from pathlib import Path

dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"AVISO: Arquivo .env não encontrado em {dotenv_path}. Usando valores padrão ou variáveis de ambiente do sistema.")

def env_var_name_with_prefix(field_name: str) -> str:
    return field_name

class Settings(BaseSettings):
    PROJECT_NAME: str = "TDAI - Transformador de Dados Assistido por IA"
    PROJECT_VERSION: str = "1.0.0"

    # Add this line:
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    SQLITE_DB_FILE: str = os.getenv("SQLITE_DB_FILE", "tdai_app.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-deve-ser-alterada-imediatamente")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 1)) # Default 1 dia
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    _cors_origins_str: Optional[str] = os.getenv("BACKEND_CORS_ORIGINS")
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "adminpassword")
    ADMIN_IDIOMA_PREFERIDO: Optional[str] = os.getenv("ADMIN_IDIOMA_PREFERIDO", "pt-BR")

    DEFAULT_LIMIT_PRODUTOS_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_PRODUTOS_SEM_PLANO", 50))
    DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO", 10))
    DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO: int = int(os.getenv("DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO", 20))

    MAIL_USERNAME: Optional[str] = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD: Optional[str] = os.getenv("MAIL_PASSWORD")
    MAIL_FROM: Optional[str] = os.getenv("MAIL_FROM")
    MAIL_PORT: int = int(os.getenv("MAIL_PORT", 587))
    MAIL_SERVER: Optional[str] = os.getenv("MAIL_SERVER")
    MAIL_STARTTLS: bool = os.getenv("MAIL_STARTTLS", "True").lower() in ("true", "1", "t")
    MAIL_SSL_TLS: bool = os.getenv("MAIL_SSL_TLS", "False").lower() in ("true", "1", "t")
    USE_CREDENTIALS: bool = bool(os.getenv("MAIL_USERNAME") and os.getenv("MAIL_PASSWORD"))
    VALIDATE_CERTS: bool = True
    MAIL_FROM_NAME: Optional[str] = os.getenv("MAIL_FROM_NAME", "TDAI Platform")

    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback")

    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
    FACEBOOK_REDIRECT_URI: Optional[str] = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/facebook/callback")

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "static/uploads")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    # Chave para acessar a API Google Gemini (modelo generativo)
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv("GOOGLE_GEMINI_API_KEY")
    
    ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES: bool = Field(default=False, validation_alias=env_var_name_with_prefix('ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES'))
    ALLOW_USERS_TO_DELETE_GLOBAL_PRODUCT_TYPES: bool = Field(default=False, validation_alias=env_var_name_with_prefix('ALLOW_USERS_TO_DELETE_GLOBAL_PRODUCT_TYPES'))
    
    class Config:
        case_sensitive = True
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = 'ignore'

settings = Settings()

if settings.DATABASE_URL is None:
    backend_dir = Path(__file__).resolve().parent.parent
    sqlite_file_path = backend_dir / settings.SQLITE_DB_FILE
    settings.DATABASE_URL = f"sqlite:///{sqlite_file_path.resolve()}"
    print(f"INFO: DATABASE_URL não encontrada no .env. Usando SQLite em: {settings.DATABASE_URL}")
else:
    print(f"INFO: DATABASE_URL carregada do .env: {settings.DATABASE_URL}")

if settings._cors_origins_str:
    try:
        raw_origins = [origin.strip() for origin in settings._cors_origins_str.split(",") if origin.strip()]
        valid_origins = []
        for origin_str in raw_origins:
            try:
                valid_origins.append(AnyHttpUrl(origin_str))
            except ValidationError:
                print(f"AVISO: Origem CORS inválida '{origin_str}' em BACKEND_CORS_ORIGINS. Será ignorada.")
        settings.BACKEND_CORS_ORIGINS = valid_origins
    except Exception as e:
        print(f"ERRO ao processar BACKEND_CORS_ORIGINS do .env: {e}. Usando fallback.")
        settings.BACKEND_CORS_ORIGINS = []

if not settings.BACKEND_CORS_ORIGINS:
    default_origins_httpurl = []
    default_list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
    ]
    for origin_url in default_list:
        try: default_origins_httpurl.append(AnyHttpUrl(origin_url))
        except ValidationError: pass
    settings.BACKEND_CORS_ORIGINS = default_origins_httpurl
    print(f"INFO: Usando CORS origins padrão: {[str(o) for o in settings.BACKEND_CORS_ORIGINS]}")
else:
    print(f"INFO: Usando CORS origins de settings: {[str(o) for o in settings.BACKEND_CORS_ORIGINS]}")

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")