# Backend/auth.py
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any 
from jose import JWTError, jwt
from passlib.context import CryptContext 
from authlib.integrations.starlette_client import OAuth, OAuthError
from starlette.config import Config as AuthlibConfig 
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status # Adicionado status se não estiver já em uso global
from fastapi.security import OAuth2PasswordBearer # <--- ADICIONADO ESTA IMPORTAÇÃO

import crud 
import models
import schemas
from core.config import settings, pwd_context 
from database import get_db 

PASSWORD_RESET_TOKEN_EXPIRE_HOURS = 1 

auth_config_dict_env = {}
if settings.GOOGLE_CLIENT_ID:
    auth_config_dict_env["GOOGLE_CLIENT_ID"] = settings.GOOGLE_CLIENT_ID
if settings.GOOGLE_CLIENT_SECRET:
    auth_config_dict_env["GOOGLE_CLIENT_SECRET"] = settings.GOOGLE_CLIENT_SECRET

facebook_client_id_from_settings = getattr(settings, 'FACEBOOK_CLIENT_ID', None)
facebook_client_secret_from_settings = getattr(settings, 'FACEBOOK_CLIENT_SECRET', None)

if facebook_client_id_from_settings:
    auth_config_dict_env["FACEBOOK_CLIENT_ID"] = facebook_client_id_from_settings
if facebook_client_secret_from_settings:
    auth_config_dict_env["FACEBOOK_CLIENT_SECRET"] = facebook_client_secret_from_settings

oauth = OAuth(config=AuthlibConfig(environ=auth_config_dict_env))

if settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET:
    try:
        if 'google' not in oauth._clients: 
            oauth.register(
                name='google',
                server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                client_kwargs={'scope': 'openid email profile'}
            )
    except Exception as e:
        print(f"AVISO: Falha ao registrar cliente Google OAuth: {e}")
else:
    print("AVISO: Credenciais do Google OAuth (CLIENT_ID ou CLIENT_SECRET) não configuradas. Login com Google desabilitado.")

if facebook_client_id_from_settings and facebook_client_secret_from_settings:
    try:
        if 'facebook' not in oauth._clients: 
            oauth.register(
                name='facebook',
                client_id=facebook_client_id_from_settings,
                client_secret=facebook_client_secret_from_settings,
                authorize_url='https://www.facebook.com/v19.0/dialog/oauth', 
                access_token_url='https://graph.facebook.com/v19.0/oauth/access_token',
                userinfo_endpoint='https://graph.facebook.com/me?fields=id,name,email,first_name,last_name,picture',
                client_kwargs={'scope': 'email public_profile'}
            )
    except Exception as e:
        print(f"AVISO: Falha ao registrar cliente Facebook OAuth: {e}")
else:
    if not (facebook_client_id_from_settings and facebook_client_secret_from_settings):
        print("AVISO: Credenciais do Facebook OAuth (FACEBOOK_CLIENT_ID e/ou FACEBOOK_CLIENT_SECRET) não configuradas. Login com Facebook desabilitado.")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/token") 

google_oauth_client = oauth.google if 'google' in oauth._clients else None
facebook_oauth_client = oauth.facebook if 'facebook' in oauth._clients else None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = crud.get_user_by_email(db, email=email)
    if not user:
        return None
    if not user.is_active: 
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_password_reset_token(email: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(hours=PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "exp": expire,
        "nbf": datetime.now(timezone.utc),
        "sub": email,
        "type": "password_reset" 
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "password_reset": 
            return None
        
        email: Optional[str] = payload.get("sub")
        if email is None:
            return None
        return email
    except JWTError:
        return None

async def get_current_user( 
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = crud.get_user_by_email(db, email=email) 
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user

async def get_current_active_superuser(current_user: models.User = Depends(get_current_active_user)) -> models.User:
    if not hasattr(current_user, 'is_superuser') or not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user

async def _get_or_create_social_user(
    db: Session,
    email: str,
    nome: Optional[str],
    provider: str,
    ) -> Optional[models.User]:
    db_user = crud.get_user_by_email(db, email=email)
    if db_user:
        if not db_user.is_active:
            print(f"Usuário existente {email} (via {provider}) está inativo.")
            return None
        
        if not db_user.nome and nome: 
            db_user.nome = nome
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
        return db_user
    else:
        default_role = crud.get_role_by_name(db, "free_user")
        if not default_role: 
            default_role = crud.create_role(db, schemas.RoleCreate(name="free_user", description="Usuário com acesso básico"))
        
        default_plano = crud.get_plano_by_name(db, "Gratuito")
        if not default_plano: 
            default_plano = crud.create_plano(db, schemas.PlanoCreate(name="Gratuito", max_descricoes_mes=100, max_titulos_mes=500))

        placeholder_password = f"!{provider.lower()}_login_disabled_{datetime.now().timestamp()}" 
        
        user_in_create = schemas.UserCreate(
            email=email,
            password=placeholder_password, 
            nome=(nome or email.split('@')[0]), 
            idioma_preferido=getattr(settings, 'IDIOMA_PADRAO_USUARIO', 'pt') 
        )
        
        created_user = crud.create_user(
            db=db,
            user=user_in_create
        )
        
        if created_user:
            if default_plano: created_user.plano_id = default_plano.id
            if default_role: created_user.role_id = default_role.id
            created_user.is_active = True 
            db.add(created_user)
            db.commit()
            db.refresh(created_user)
            print(f"Novo usuário criado via {provider}: {email}")
        return created_user

async def process_google_login(db: Session, google_userinfo: Dict[str, Any]) -> Optional[models.User]:
    email = google_userinfo.get('email')
    if not email:
        print("Email do Google não encontrado nas informações do usuário.")
        return None
    if not google_userinfo.get('email_verified', False):
        print(f"Email {email} do Google não está verificado.")
        # Considere se quer bloquear aqui ou apenas avisar.
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email do Google não verificado.")

    nome_completo = google_userinfo.get('name')
    if not nome_completo: 
        primeiro_nome = google_userinfo.get('given_name', '')
        ultimo_nome = google_userinfo.get('family_name', '')
        nome_completo = f"{primeiro_nome} {ultimo_nome}".strip()
        
    return await _get_or_create_social_user(db, email, nome_completo, "Google")

async def process_facebook_login(db: Session, facebook_userinfo: Dict[str, Any]) -> Optional[models.User]:
    email = facebook_userinfo.get('email')
    if not email:
        print("Email do Facebook não fornecido. Não é possível prosseguir com login/registro baseado em email.")
        return None 
        
    nome_completo = facebook_userinfo.get('name', '')
    return await _get_or_create_social_user(db, email, nome_completo, "Facebook")