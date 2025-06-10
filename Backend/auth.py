# Backend/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status # Imports do FastAPI
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm # Para o formulário de login

from jose import JWTError, jwt
from authlib.integrations.starlette_client import OAuth, OAuthError  # type: ignore
from starlette.config import Config as AuthlibConfig
from sqlalchemy.orm import Session
from Backend.core.config import settings
from Backend.core.security import pwd_context
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)

from Backend import schemas
from Backend import models
from Backend import crud
from Backend import crud_users
from Backend.database import get_db  # Para Depends(get_db)

# Constante para expiração do token de reset de senha
PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1 

# --- Definição do Router para este módulo ---
router = APIRouter() # <--- DEFINIÇÃO DO ROUTER ADICIONADA AQUI

# --- Esquema OAuth2 ---
# O tokenUrl DEVE corresponder ao endpoint de login/token que este router define.
# Se este router (auth.router) for montado em /api/v1/auth em main.py, 
# e o endpoint de token neste arquivo for "/token",
# então o tokenUrl completo para o cliente é "/api/v1/auth/token".
# O FastAPI usa este tokenUrl internamente e para a documentação Swagger.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token") # Relativo ao prefixo do router


# --- Configuração Authlib OAuth (para login social) ---
auth_config_dict_env = {}
if settings.GOOGLE_CLIENT_ID:
    auth_config_dict_env["GOOGLE_CLIENT_ID"] = settings.GOOGLE_CLIENT_ID
if settings.GOOGLE_CLIENT_SECRET:
    auth_config_dict_env["GOOGLE_CLIENT_SECRET"] = settings.GOOGLE_CLIENT_SECRET
if settings.FACEBOOK_CLIENT_ID:
    auth_config_dict_env["FACEBOOK_CLIENT_ID"] = settings.FACEBOOK_CLIENT_ID
if settings.FACEBOOK_CLIENT_SECRET:
    auth_config_dict_env["FACEBOOK_CLIENT_SECRET"] = settings.FACEBOOK_CLIENT_SECRET

oauth = OAuth(config=AuthlibConfig(environ=auth_config_dict_env))

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    if 'google' not in oauth._clients:
        oauth.register(
            name='google',
            server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            client_kwargs={'scope': 'openid email profile'}
        )
else:
    logger.warning(
        "Credenciais do Google OAuth (CLIENT_ID ou CLIENT_SECRET) não configuradas no .env. Login com Google desabilitado."
    )

if settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET:
    if 'facebook' not in oauth._clients:
        oauth.register(
            name='facebook',
            client_id=settings.FACEBOOK_CLIENT_ID,
            client_secret=settings.FACEBOOK_CLIENT_SECRET,
            authorize_url='https://www.facebook.com/v19.0/dialog/oauth',
            access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',
            userinfo_endpoint='https://graph.facebook.com/me?fields=id,name,email,first_name,last_name,picture',
            client_kwargs={'scope': 'email public_profile'}
        )
else:
    logger.warning(
        "Credenciais do Facebook OAuth (CLIENT_ID ou CLIENT_SECRET) não configuradas no .env. Login com Facebook desabilitado."
    )


# --- Funções de Senha e Token ---
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_password_reset_token() -> str:
    """Generate a random password reset token."""
    return secrets.token_urlsafe(32)


def hash_password_reset_token(token: str) -> str:
    """Return a deterministic hash of the reset token."""
    return hashlib.sha256(token.encode()).hexdigest()


def verify_password_reset_token(token: str, token_hash: str) -> bool:
    """Compare a provided token against the stored hash."""
    return hash_password_reset_token(token) == token_hash

# --- Funções de Autenticação de Usuário ---
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = crud_users.get_user_by_email(db, email=email)
    if not user:
        return None
    if not user.is_active:
        return None 
    if not user.hashed_password or not verify_password(password, user.hashed_password): 
        return None
    return user

# --- DEPENDÊNCIAS DE AUTENTICAÇÃO ---
async def get_current_user(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Não foi possível validar as credenciais",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("user_id") 
        if email is None or user_id is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email, user_id=user_id)
    except JWTError:
        raise credentials_exception
    
    user = crud_users.get_user(db, user_id=token_data.user_id) 
    if user is None or user.email != token_data.email : 
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Usuário inativo")
    return current_user

# --- ENDPOINTS DE AUTENTICAÇÃO ---
@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, email=form_data.username, password=form_data.password) 
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active: 
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conta inativa.")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(data={"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.post("/token/refresh/", response_model=schemas.Token)
async def refresh_access_token(
    refresh_token_data: schemas.RefreshTokenRequest, 
    db: Session = Depends(get_db)
):
    token = refresh_token_data.refresh_token
    credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = jwt.decode(token, settings.REFRESH_SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        user_id: Optional[int] = payload.get("user_id")
        if email is None or user_id is None:
            raise credentials_exception
        
        user = crud_users.get_user(db, user_id=user_id)
        if not user or user.email != email or not user.is_active:
            raise credentials_exception

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        new_access_token = create_access_token(
            data={"sub": user.email, "user_id": user.id}, expires_delta=access_token_expires
        )
        return {"access_token": new_access_token, "refresh_token": token, "token_type": "bearer"}

    except JWTError:
        raise credentials_exception


@router.get("/users/me", response_model=schemas.UserResponse)
async def read_users_me(
    current_user: models.User = Depends(get_current_active_user) 
):
    return current_user

# --- Funções de Processamento de Login Social (UTILITÁRIAS, chamadas por routers/social_auth.py) ---
async def _get_or_create_social_user( 
    db: Session,
    email: str,
    nome: Optional[str], 
    provider: str,
    provider_user_id: str 
    ) -> Optional[models.User]:
    db_user = crud_users.get_user_by_email(db, email=email)
    if db_user:
        if not db_user.is_active:
            logger.warning("Usuário existente %s (via %s) está inativo.", email, provider)
            return None
        
        updated = False
        if not db_user.nome_completo and nome: 
            db_user.nome_completo = nome
            updated = True
        if not db_user.provider: 
            db_user.provider = provider
            updated = True
        if not db_user.provider_user_id: # Salva o provider_user_id se não existir
            db_user.provider_user_id = provider_user_id
            updated = True
        
        if updated:
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        return db_user
    else:
        # Utiliza a função correta do CRUD para buscar o plano pelo nome
        # (get_plano_by_name). A versão 'get_plano_by_nome' não existe e
        # geraria AttributeError em tempo de execução.
        default_plano = crud_users.get_plano_by_name(db, "Gratuito")
        
        user_in_create = schemas.UserCreateOAuth( 
            email=email,
            nome_completo=(nome or email.split('@')[0]), 
            provider=provider,
            provider_user_id=provider_user_id 
        )
        
        created_user = crud_users.create_user_oauth(
            db=db,
            user_oauth=user_in_create,
            plano_id_default=default_plano.id if default_plano else None,
        )
        logger.info("Novo usuário criado via %s: %s", provider, email)
        return created_user

async def process_google_login(db: Session, google_userinfo: Dict[str, Any]) -> Optional[models.User]:
    email = google_userinfo.get("email")
    if not email:
        logger.error("Email do Google não encontrado nas informações do usuário.")
        return None

    if not google_userinfo.get("email_verified", False):
        logger.warning("Email %s do Google não está verificado.", email)
        return None

    nome_completo = google_userinfo.get("name")
    if not nome_completo:
        primeiro_nome = google_userinfo.get("given_name", "")
        ultimo_nome = google_userinfo.get("family_name", "")
        nome_completo = f"{primeiro_nome} {ultimo_nome}".strip()

    google_user_id = google_userinfo.get("sub")
    if not google_user_id:
        logger.error("ID de usuário do Google (sub) não encontrado.")
        return None

    return await _get_or_create_social_user(db, email, nome_completo, "Google", google_user_id)

async def process_facebook_login(db: Session, facebook_userinfo: Dict[str, Any]) -> Optional[models.User]:
    email = facebook_userinfo.get("email")
    if not email:
        logger.error(
            "Email do Facebook não fornecido. Não é possível prosseguir com login/registro baseado em email."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email não fornecido pelo Facebook. Verifique suas permissões.",
        )

    nome_completo = facebook_userinfo.get("name", "")
    facebook_user_id = facebook_userinfo.get("id")
    if not facebook_user_id:
        logger.error("ID de usuário do Facebook não encontrado.")
        return None

    return await _get_or_create_social_user(db, email, nome_completo, "Facebook", facebook_user_id)
