# Backend/routers/auth_utils.py
import logging
from datetime import datetime, timedelta, timezone # Mantido para uso potencial
from typing import Optional

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt # JWTError pode ser útil para tratamento específico de erros de token
# from passlib.context import CryptContext # Removido, agora em core.security
from sqlalchemy.orm import Session

import crud
import models
import schemas
from core import config # Mantido para settings que não são de segurança direta
from core import security # <<< ADICIONADO: Importa o novo módulo de segurança
from database import get_db

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
    auth_header = request.headers.get('authorization')
    if auth_header:
        # logger.debug(f"Cabeçalho 'authorization' encontrado: {auth_header[:30]}...") # Log apenas uma parte do token
        pass
    else:
        # logger.debug("Cabeçalho 'authorization' NÃO encontrado.")
        pass
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
        
    user = crud.get_user(db, user_id=token_payload.user_id)
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

# Função para decodificar refresh token (exemplo, pode ser mais robusta)
async def get_user_from_refresh_token(
    db: Session,
    refresh_token: str,
) -> Optional[models.User]:
    try:
        payload = jwt.decode(
            refresh_token, config.settings.REFRESH_SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        token_type = payload.get("token_type")
        if token_type != "refresh":
            return None # Não é um refresh token

        user_id = payload.get("user_id")
        if user_id is None:
            return None
        
        user = crud.get_user(db, user_id=int(user_id))
        return user
    except JWTError:
        return None
    except ValueError: # Erro na conversão de user_id para int
        return None