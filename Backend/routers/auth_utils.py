# Backend/routers/auth_utils.py
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
# from passlib.context import CryptContext # Removido, agora em core.security
from sqlalchemy.orm import Session

from Backend import crud_users
from Backend import models
from Backend.core import config  # Mantido para settings que não são de segurança direta
from Backend.core import security  # <<< ADICIONADO: Importa o novo módulo de segurança
from Backend.database import get_db

# Configuração básica de logging
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.settings.API_V1_STR}/auth/token")

# pwd_context, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES foram movidos para core.security

# def verify_password(plain_password, hashed_password): # MOVIDO para core.security
# return security.pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password): # MOVIDO para core.security
# return security.pwd_context.hash(password)

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str: # MOVIDO para core.security
#     return security.create_access_token(data, expires_delta)


async def get_current_user(
    request: Request, # Adicionado para debug
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:
    # Debugging: Log headers and token
    # logger.debug(f"--- DEBUG: auth_utils.get_current_user ---")
    # logger.debug(f"Path da Requisição: {request.url.path}")
    # logger.debug(f"Headers Recebidos (raw): {dict(request.headers)}")
    # logger.debug(f"--- FIM DEBUG: auth_utils.get_current_user ---")


    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    token_payload = security.decode_token(token, config.settings.SECRET_KEY)
    if token_payload is None or token_payload.user_id is None: # Verifica se user_id está presente
        logger.warning(f"Token inválido ou user_id ausente no payload. Token: {token[:20]}...")
        raise credentials_exception
        
    user = crud_users.get_user(db, user_id=token_payload.user_id)
    if user is None:
        logger.warning(f"Usuário não encontrado no DB para user_id: {token_payload.user_id}")
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
    return current_user


async def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="The user doesn't have enough privileges"
        )
    return current_user

