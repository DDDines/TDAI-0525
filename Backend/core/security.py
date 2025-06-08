# Backend/core/security.py
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt, JWTError
from passlib.context import CryptContext
from pydantic import BaseModel, ValidationError # Adicionado ValidationError

from Backend.core.config import settings # Importa o objeto settings diretamente

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    user_id: Optional[int] = None
    # Adicionar outros campos que você possa ter no payload
    # exp: Optional[int] = None # exp é tratado pelo jose.jwt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    # Adiciona um campo 'type' ou similar para diferenciar do access token se necessário no payload
    to_encode.update({"exp": expire, "token_type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.REFRESH_SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str, secret_key: str) -> Optional[TokenPayload]:
    try:
        payload_dict = jwt.decode(token, secret_key, algorithms=[ALGORITHM])
        # O campo 'sub' é o email, user_id é customizado
        user_id_str = payload_dict.get("user_id")
        user_id = int(user_id_str) if user_id_str is not None else None
        
        return TokenPayload(sub=payload_dict.get("sub"), user_id=user_id)
    except JWTError: # Erro de decodificação (expirado, inválido, etc)
        return None
    except ValidationError: # Erro de validação do TokenPayload (raro se o token for bem formado)
        return None
    except ValueError: # Erro ao converter user_id para int
        return None
