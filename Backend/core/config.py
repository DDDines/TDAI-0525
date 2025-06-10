# Backend/core/config.py
import os
import logging
from dotenv import load_dotenv
from typing import List, Union, Optional
from pydantic_settings import BaseSettings
from pydantic import AnyHttpUrl, ValidationError, Field
from pathlib import Path
from .logging_config import get_logger

logger = get_logger(__name__)


dotenv_path = Path(__file__).resolve().parent.parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path)
else:
    logger.warning(
        "Arquivo .env não encontrado em %s. Usando valores padrão ou variáveis de ambiente do sistema.",
        dotenv_path,
    )

def env_var_name_with_prefix(field_name: str) -> str:
    return field_name

class Settings(BaseSettings):
    PROJECT_NAME: str = "CatalogAI - Transformador de Dados Assistido por IA"
    PROJECT_VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    DATABASE_URL: Optional[str] = os.getenv("DATABASE_URL")
    SQLITE_DB_FILE: str = os.getenv("SQLITE_DB_FILE", "catalogai_app.db")

    SECRET_KEY: str = os.getenv("SECRET_KEY", "super-secret-key-deve-ser-alterada-imediatamente")
    REFRESH_SECRET_KEY: str = os.getenv("REFRESH_SECRET_KEY", "super-refresh-secret-change-me")

    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24 * 1)) # Default 1 dia
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv("PASSWORD_RESET_TOKEN_EXPIRE_HOURS", 1))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", 7))

    # ``cors_origins_str`` captura o valor cru da variável de ambiente
    # ``BACKEND_CORS_ORIGINS``. ``BACKEND_CORS_ORIGINS`` em si utiliza um alias
    # inexistente para evitar que o ``BaseSettings`` tente processá-la
    # automaticamente (o que falharia quando o valor não está em formato JSON).
    cors_origins_str: Optional[str] = Field(default=None, alias="BACKEND_CORS_ORIGINS")
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list, alias="BACKEND_CORS_ORIGINS_PARSED")

    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "<ADMIN_EMAIL>")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "<ADMIN_PASSWORD>")
    ADMIN_IDIOMA_PREFERIDO: Optional[str] = os.getenv("ADMIN_IDIOMA_PREFERIDO", "pt-BR")
    FIRST_SUPERUSER_EMAIL: str = os.getenv("FIRST_SUPERUSER_EMAIL", "<FIRST_SUPERUSER_EMAIL>")
    FIRST_SUPERUSER_PASSWORD: str = os.getenv("FIRST_SUPERUSER_PASSWORD", "<FIRST_SUPERUSER_PASSWORD>")

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
    MAIL_FROM_NAME: Optional[str] = os.getenv("MAIL_FROM_NAME", "CatalogAI Platform")

    # When True, functions like send_password_reset_email will raise an
    # exception instead of returning silently if the email configuration is
    # incomplete. Defaults to False for backward compatibility.
    RAISE_ON_MISSING_EMAIL_CONFIG: bool = os.getenv("RAISE_ON_MISSING_EMAIL_CONFIG", "False").lower() in ("true", "1", "t", "yes")

    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/v1/auth/google/callback")

    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv("FACEBOOK_CLIENT_ID")
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv("FACEBOOK_CLIENT_SECRET")
    FACEBOOK_REDIRECT_URI: Optional[str] = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/api/v1/auth/facebook/callback")

    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173")
    UPLOAD_DIRECTORY: str = os.getenv("UPLOAD_DIRECTORY", "static/uploads")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv("GOOGLE_GEMINI_API_KEY")
    CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI: int = int(os.getenv("CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI", 1))
    GOOGLE_CSE_API_KEY: Optional[str] = os.getenv("GOOGLE_CSE_API_KEY")
    GOOGLE_CSE_ID: Optional[str] = os.getenv("GOOGLE_CSE_ID")
    
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
    logger.info("DATABASE_URL não encontrada no .env. Usando SQLite em: %s", settings.DATABASE_URL)
else:
    logger.info("DATABASE_URL carregada do .env: %s", settings.DATABASE_URL)

# CORS
if settings.cors_origins_str:
    try:
        raw_origins = [origin.strip() for origin in settings.cors_origins_str.split(",") if origin.strip()]
        valid_origins = []
        for origin_str in raw_origins:
            try:
                valid_origins.append(AnyHttpUrl(origin_str))
            except ValidationError:
                logger.warning("Origem CORS inválida '%s' em BACKEND_CORS_ORIGINS. Será ignorada.", origin_str)
        settings.BACKEND_CORS_ORIGINS = valid_origins
    except Exception as e:
        logger.error("Erro ao processar BACKEND_CORS_ORIGINS do .env: %s. Usando fallback.", e)
        settings.BACKEND_CORS_ORIGINS = []
else:
    # Padrão
    default_origins_httpurl = []
    default_list = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost",
    ]
    for origin_url in default_list:
        try:
            default_origins_httpurl.append(AnyHttpUrl(origin_url))
        except ValidationError:
            pass
    settings.BACKEND_CORS_ORIGINS = default_origins_httpurl
    logger.info("Usando CORS origins padrão: %s", [str(o) for o in settings.BACKEND_CORS_ORIGINS])

logger.info("Usando CORS origins de settings: %s", [str(o) for o in settings.BACKEND_CORS_ORIGINS])

from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
