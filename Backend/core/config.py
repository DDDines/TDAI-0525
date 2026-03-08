"""Document config module responsibilities and runtime integration points."""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv


class _SettingsBaseLoader:
    """Resolve the settings base implementation for the current environment."""

    @staticmethod
    def load():
        """Load the settings base implementation compatible with the current install."""
        try:
            from pydantic_settings import BaseSettings, SettingsConfigDict
            return BaseSettings, SettingsConfigDict
        except ModuleNotFoundError:
            from pydantic.v1 import BaseSettings
            return BaseSettings, dict


BaseSettings, SettingsConfigDict = _SettingsBaseLoader.load()
from pydantic import AnyHttpUrl, Field, TypeAdapter, ValidationError
from .logging_config import get_logger
logger = get_logger(__name__)
http_url_adapter = TypeAdapter(AnyHttpUrl)

class Settings(BaseSettings):
    """Represent Settings and centralize its responsibilities inside this module."""
    PROJECT_NAME: str = 'CatalogAI - Transformador de Dados Assistido por IA'
    PROJECT_VERSION: str = '1.0.0'
    API_V1_STR: str = '/api/v1'
    DATABASE_URL: Optional[str] = os.getenv('DATABASE_URL')
    SQLITE_DB_FILE: str = os.getenv('SQLITE_DB_FILE', 'catalogai_app.db')
    SECRET_KEY: str = os.getenv('SECRET_KEY', 'super-secret-key-deve-ser-alterada-imediatamente')
    REFRESH_SECRET_KEY: str = os.getenv('REFRESH_SECRET_KEY', 'super-refresh-secret-change-me')
    ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 60 * 24 * 1))
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = int(os.getenv('PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 1))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 7))
    cors_origins_str: Optional[str] = Field(default=None, alias='BACKEND_CORS_ORIGINS')
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = Field(default_factory=list, alias='BACKEND_CORS_ORIGINS_PARSED')
    ADMIN_EMAIL: str = os.getenv('ADMIN_EMAIL', '<ADMIN_EMAIL>')
    ADMIN_PASSWORD: str = os.getenv('ADMIN_PASSWORD', '<ADMIN_PASSWORD>')
    ADMIN_IDIOMA_PREFERIDO: Optional[str] = os.getenv('ADMIN_IDIOMA_PREFERIDO', 'pt-BR')
    FIRST_SUPERUSER_EMAIL: str = os.getenv('FIRST_SUPERUSER_EMAIL', '<FIRST_SUPERUSER_EMAIL>')
    FIRST_SUPERUSER_PASSWORD: str = os.getenv('FIRST_SUPERUSER_PASSWORD', '<FIRST_SUPERUSER_PASSWORD>')
    DEFAULT_LIMIT_PRODUTOS_SEM_PLANO: int = int(os.getenv('DEFAULT_LIMIT_PRODUTOS_SEM_PLANO', 50))
    DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO: int = int(os.getenv('DEFAULT_LIMIT_ENRIQUECIMENTO_SEM_PLANO', 10))
    DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO: int = int(os.getenv('DEFAULT_LIMIT_GERACAO_IA_SEM_PLANO', 20))
    MAIL_USERNAME: Optional[str] = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD: Optional[str] = os.getenv('MAIL_PASSWORD')
    MAIL_FROM: Optional[str] = os.getenv('MAIL_FROM')
    MAIL_PORT: int = int(os.getenv('MAIL_PORT', 587))
    MAIL_SERVER: Optional[str] = os.getenv('MAIL_SERVER')
    MAIL_STARTTLS: bool = os.getenv('MAIL_STARTTLS', 'True').lower() in ('true', '1', 't')
    MAIL_SSL_TLS: bool = os.getenv('MAIL_SSL_TLS', 'False').lower() in ('true', '1', 't')
    USE_CREDENTIALS: bool = bool(os.getenv('MAIL_USERNAME') and os.getenv('MAIL_PASSWORD'))
    VALIDATE_CERTS: bool = True
    MAIL_FROM_NAME: Optional[str] = os.getenv('MAIL_FROM_NAME', 'CatalogAI Platform')
    RAISE_ON_MISSING_EMAIL_CONFIG: bool = os.getenv('RAISE_ON_MISSING_EMAIL_CONFIG', 'True').lower() in ('true', '1', 't', 'yes')
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI: Optional[str] = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:8000/api/v1/auth/google/callback')
    FACEBOOK_CLIENT_ID: Optional[str] = os.getenv('FACEBOOK_CLIENT_ID')
    FACEBOOK_CLIENT_SECRET: Optional[str] = os.getenv('FACEBOOK_CLIENT_SECRET')
    FACEBOOK_REDIRECT_URI: Optional[str] = os.getenv('FACEBOOK_REDIRECT_URI', 'http://localhost:8000/api/v1/auth/facebook/callback')
    FRONTEND_URL: str = os.getenv('FRONTEND_URL', 'http://localhost:5173')
    UPLOAD_DIRECTORY: str = os.getenv('UPLOAD_DIRECTORY', 'static/uploads')
    PREVIEW_DIRECTORY: str = os.getenv('PREVIEW_DIRECTORY', 'static/previews')
    POPPLER_PATH: Optional[str] = os.getenv('POPPLER_PATH')
    OPENAI_API_KEY: Optional[str] = os.getenv('OPENAI_API_KEY')
    AI_PROVIDER: str = os.getenv('AI_PROVIDER', 'openai')
    LM_STUDIO_BASE_URL: str = os.getenv('LM_STUDIO_BASE_URL', 'http://127.0.0.1:1234/v1')
    LM_STUDIO_MODEL: Optional[str] = os.getenv('LM_STUDIO_MODEL')
    LM_STUDIO_API_KEY: str = os.getenv('LM_STUDIO_API_KEY', 'lm-studio')
    GOOGLE_GEMINI_API_KEY: Optional[str] = os.getenv('GOOGLE_GEMINI_API_KEY')
    CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI: int = int(os.getenv('CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI', 1))
    GOOGLE_CSE_API_KEY: Optional[str] = os.getenv('GOOGLE_CSE_API_KEY')
    GOOGLE_CSE_ID: Optional[str] = os.getenv('GOOGLE_CSE_ID')
    PLAYWRIGHT_PROXY_POOL_JSON: Optional[str] = os.getenv('PLAYWRIGHT_PROXY_POOL_JSON')
    PLAYWRIGHT_GOTO_TIMEOUT_MS: int = int(os.getenv('PLAYWRIGHT_GOTO_TIMEOUT_MS', 30000))
    MAX_UPLOAD_BYTES: int = int(os.getenv('MAX_UPLOAD_BYTES', 25 * 1024 * 1024))
    ASYNC_DISPATCH_PROVIDER: str = os.getenv('ASYNC_DISPATCH_PROVIDER', 'background_tasks')
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CELERY_BROKER_URL: str = os.getenv('CELERY_BROKER_URL', os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    CELERY_RESULT_BACKEND: str = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')
    CELERY_TASK_ALWAYS_EAGER: bool = os.getenv('CELERY_TASK_ALWAYS_EAGER', 'False').lower() in ('true', '1', 't', 'yes')
    AUTO_CREATE_TABLES: bool = os.getenv('AUTO_CREATE_TABLES', 'False').lower() in ('true', '1', 't', 'yes')
    APP_MODE: str = os.getenv('APP_MODE', 'oop')
    PRODUCT_EXPERIENCE_DEFAULT: str = os.getenv('PRODUCT_EXPERIENCE_DEFAULT', 'basic')
    ALLOW_ADMIN_EXPERIENCE_PREVIEW: bool = os.getenv('ALLOW_ADMIN_EXPERIENCE_PREVIEW', 'True').lower() in ('true', '1', 't', 'yes')
    ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES: bool = Field(default=False, validation_alias='ALLOW_USERS_TO_EDIT_GLOBAL_PRODUCT_TYPES')
    ALLOW_USERS_TO_DELETE_GLOBAL_PRODUCT_TYPES: bool = Field(default=False, validation_alias='ALLOW_USERS_TO_DELETE_GLOBAL_PRODUCT_TYPES')
    model_config = SettingsConfigDict(case_sensitive=True, env_file='.env', env_file_encoding='utf-8', extra='ignore')

class ConfigWorkflow:

    """Represent Config Workflow and centralize its responsibilities inside this module."""
    def __init__(self, runtime: Optional['ConfigRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Config Workflow."""
        self._runtime = runtime or ConfigRuntime()

    def build_settings(self) -> Settings:
        """Build settings from current inputs and configuration."""
        return self._runtime.build_settings()

class ConfigRuntime:
    """Runtime OO para resolução e construção de settings."""

    def resolve_dotenv_path(self) -> Path:
        """Resolve dotenv path from injected repositories or runtime context."""
        return Path(__file__).resolve().parent.parent.parent / '.env'

    def load_dotenv(self, dotenv_path: Path) -> None:
        """Execute load dotenv as part of this module workflow."""
        if dotenv_path.exists():
            load_dotenv(dotenv_path=dotenv_path)
            return
        logger.warning('Arquivo .env nao encontrado em %s. Usando valores padrao ou variaveis de ambiente do sistema.', dotenv_path)

    def build_default_cors_origins(self) -> List[AnyHttpUrl]:
        """Build default cors origins from current inputs and configuration."""
        default_origins: List[AnyHttpUrl] = []
        default_list = ['http://localhost:5173', 'http://127.0.0.1:5173', 'http://localhost']
        for origin_url in default_list:
            try:
                default_origins.append(http_url_adapter.validate_python(origin_url))
            except ValidationError:
                continue
        return default_origins

    def parse_cors_origins(self, cors_origins_str: str) -> List[AnyHttpUrl]:
        """Parse cors origins into structured data used by downstream logic."""
        raw_origins = [origin.strip() for origin in cors_origins_str.split(',') if origin.strip()]
        valid_origins: List[AnyHttpUrl] = []
        for origin_str in raw_origins:
            try:
                valid_origins.append(http_url_adapter.validate_python(origin_str))
            except ValidationError:
                logger.warning("Origem CORS invalida '%s' em BACKEND_CORS_ORIGINS. Sera ignorada.", origin_str)
        return valid_origins

    def configure_database_url(self, settings_obj: Settings) -> None:
        """Execute configure database url as part of this module workflow."""
        if settings_obj.DATABASE_URL is not None:
            logger.info('DATABASE_URL carregada do .env: %s', settings_obj.DATABASE_URL)
            return
        backend_dir = Path(__file__).resolve().parent.parent
        sqlite_file_path = backend_dir / settings_obj.SQLITE_DB_FILE
        settings_obj.DATABASE_URL = f'sqlite:///{sqlite_file_path.resolve()}'
        logger.info('DATABASE_URL nao encontrada no .env. Usando SQLite em: %s', settings_obj.DATABASE_URL)

    def configure_cors_origins(self, settings_obj: Settings) -> None:
        """Execute configure cors origins as part of this module workflow."""
        if settings_obj.cors_origins_str:
            try:
                settings_obj.BACKEND_CORS_ORIGINS = self.parse_cors_origins(settings_obj.cors_origins_str)
            except Exception as exc:
                logger.error('Erro ao processar BACKEND_CORS_ORIGINS do .env: %s. Usando fallback.', exc)
                settings_obj.BACKEND_CORS_ORIGINS = []
        else:
            settings_obj.BACKEND_CORS_ORIGINS = self.build_default_cors_origins()
            logger.info('Usando CORS origins padrao: %s', [str(origin) for origin in settings_obj.BACKEND_CORS_ORIGINS])

    def build_settings(self) -> Settings:
        """Build settings from current inputs and configuration."""
        dotenv_path = self.resolve_dotenv_path()
        self.load_dotenv(dotenv_path)
        settings_obj = Settings()
        self.configure_database_url(settings_obj)
        self.configure_cors_origins(settings_obj)
        logger.info('Usando CORS origins de settings: %s', [str(origin) for origin in settings_obj.BACKEND_CORS_ORIGINS])
        logger.info('APP_MODE ativo: %s', settings_obj.APP_MODE)
        return settings_obj


settings = ConfigWorkflow().build_settings()
