# tdai_project/app/core/config.py
import os
from dotenv import load_dotenv
from passlib.context import CryptContext
from typing import Optional, List # Adicionado List para compatibilidade futura, se necessário
from pydantic import EmailStr # Necessário para validação de MAIL_FROM

# Carrega variáveis de ambiente do arquivo .env (se existir na raiz do projeto)
# Garanta que a pasta 'tdai_project' seja o diretório de trabalho atual
# ou ajuste o path para o .env se necessário.
# Exemplo: load_dotenv(dotenv_path=os.path.join(os.path.dirname(PROJECT_ROOT_CONFIG_ASSUMES_APP_DIR), '.env'))
# Se este config.py está em app/core/ e .env está em tdai_project/, o seguinte deve funcionar
# ao rodar a partir da raiz do projeto.
project_root_for_dotenv = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
dotenv_path = os.path.join(project_root_for_dotenv, '.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)
else:
    print(f"AVISO: Arquivo .env não encontrado em {dotenv_path}. Usando valores default ou variáveis de ambiente existentes.")


# Configurações do Banco de Dados
# Tenta pegar a URL completa primeiro, depois monta com as partes individuais
DATABASE_URL_ENV = os.getenv("DATABASE_URL")
POSTGRES_USER_ENV = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD_ENV = os.getenv("POSTGRES_PASSWORD", "password") # Mude isso no seu .env!
POSTGRES_SERVER_ENV = os.getenv("POSTGRES_SERVER", "localhost")
POSTGRES_PORT_ENV = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB_ENV = os.getenv("POSTGRES_DB", "tdai_db")

if DATABASE_URL_ENV:
    FINAL_DATABASE_URL = DATABASE_URL_ENV
else:
    FINAL_DATABASE_URL = f"postgresql://{POSTGRES_USER_ENV}:{POSTGRES_PASSWORD_ENV}@{POSTGRES_SERVER_ENV}:{POSTGRES_PORT_ENV}/{POSTGRES_DB_ENV}"


# Configurações JWT
SECRET_KEY = os.getenv("SECRET_KEY", "uma_chave_secreta_muito_forte_e_aleatoria_para_desenvolvimento_apenas") # MUDE EM PRODUÇÃO!
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 60)) # Ex: 1 hora

# Configurações OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") # Pode ser None se não configurado

# Configurações Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback") # Ajuste se necessário

# Configurações Facebook OAuth
FACEBOOK_CLIENT_ID = os.getenv("FACEBOOK_CLIENT_ID")
FACEBOOK_CLIENT_SECRET = os.getenv("FACEBOOK_CLIENT_SECRET")
FACEBOOK_REDIRECT_URI = os.getenv("FACEBOOK_REDIRECT_URI", "http://localhost:8000/auth/facebook/callback") # Ajuste se necessário

# Configurações Google Search API (Programmable Search Engine)
GOOGLE_CSE_API_KEY = os.getenv("GOOGLE_CSE_API_KEY")
GOOGLE_CSE_ID = os.getenv("GOOGLE_CSE_ID")

# Configurações de Email com FastAPI-Mail
MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM") # Ex: seu_email@example.com
MAIL_PORT = int(os.getenv("MAIL_PORT", 587)) # Porta TLS padrão
MAIL_SERVER = os.getenv("MAIL_SERVER") # Ex: smtp.gmail.com
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "Equipe TDAI")
# Converte string para boolean de forma mais robusta
MAIL_STARTTLS_STR = os.getenv("MAIL_STARTTLS", "True").lower()
MAIL_STARTTLS = MAIL_STARTTLS_STR in ('true', '1', 't', 'yes')

MAIL_SSL_TLS_STR = os.getenv("MAIL_SSL_TLS", "False").lower()
MAIL_SSL_TLS = MAIL_SSL_TLS_STR in ('true', '1', 't', 'yes')

USE_CREDENTIALS_STR = os.getenv("USE_CREDENTIALS", "True").lower()
USE_CREDENTIALS = USE_CREDENTIALS_STR in ('true', '1', 't', 'yes')

VALIDATE_CERTS_STR = os.getenv("VALIDATE_CERTS", "True").lower()
VALIDATE_CERTS = VALIDATE_CERTS_STR in ('true', '1', 't', 'yes')

# URL base do seu frontend para construir o link de reset (IMPORTANTE)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000") # Ajuste para a URL do seu frontend React

# Passlib Context para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class Settings:
    PROJECT_NAME: str = "TDAI - Sistema Inteligente de Geração de Títulos e Descrições"
    PROJECT_VERSION: str = "0.1.0"

    DATABASE_URL: str = FINAL_DATABASE_URL

    SECRET_KEY: str = SECRET_KEY
    ALGORITHM: str = ALGORITHM
    ACCESS_TOKEN_EXPIRE_MINUTES: int = ACCESS_TOKEN_EXPIRE_MINUTES
    
    OPENAI_API_KEY: Optional[str] = OPENAI_API_KEY

    GOOGLE_CLIENT_ID: Optional[str] = GOOGLE_CLIENT_ID
    GOOGLE_CLIENT_SECRET: Optional[str] = GOOGLE_CLIENT_SECRET
    GOOGLE_REDIRECT_URI: Optional[str] = GOOGLE_REDIRECT_URI 

    FACEBOOK_CLIENT_ID: Optional[str] = FACEBOOK_CLIENT_ID
    FACEBOOK_CLIENT_SECRET: Optional[str] = FACEBOOK_CLIENT_SECRET
    FACEBOOK_REDIRECT_URI: Optional[str] = FACEBOOK_REDIRECT_URI 
    
    GOOGLE_CSE_API_KEY: Optional[str] = GOOGLE_CSE_API_KEY
    GOOGLE_CSE_ID: Optional[str] = GOOGLE_CSE_ID

    MAIL_USERNAME: Optional[str] = MAIL_USERNAME
    MAIL_PASSWORD: Optional[str] = MAIL_PASSWORD
    MAIL_FROM: Optional[EmailStr] = MAIL_FROM 
    MAIL_PORT: int = MAIL_PORT
    MAIL_SERVER: Optional[str] = MAIL_SERVER
    MAIL_FROM_NAME: Optional[str] = MAIL_FROM_NAME
    MAIL_STARTTLS: bool = MAIL_STARTTLS
    MAIL_SSL_TLS: bool = MAIL_SSL_TLS
    USE_CREDENTIALS: bool = USE_CREDENTIALS
    VALIDATE_CERTS: bool = VALIDATE_CERTS
    
    FRONTEND_URL: str = FRONTEND_URL

settings = Settings()