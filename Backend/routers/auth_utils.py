# Backend/routers/auth_utils.py
from fastapi import Depends, HTTPException, status, Request # Adicionar Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

import crud
import models
import schemas # Necessário para schemas.TokenData
from core.config import settings
import database # Para database.get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token") # Corrigido para o path completo do token

async def get_current_user(
    request: Request, # Adicionar Request para acessar headers
    db: Session = Depends(database.get_db), 
    token: str = Depends(oauth2_scheme)
) -> models.User:
    
    # DEBUG LOG: Imprimir cabeçalhos da requisição
    print(f"auth_utils: get_current_user chamado para o path: {request.url.path}")
    print(f"auth_utils: Headers recebidos: {request.headers}")
    # Fim do DEBUG LOG

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id") # Adicionado para pegar user_id
        if email is None or user_id is None:
            print("auth_utils: Email ou user_id ausente no payload do token.") # DEBUG
            raise credentials_exception
        # token_data = schemas.TokenData(email=email, user_id=user_id) # Correção do nome da classe
        token_data = schemas.TokenData(email=email, user_id=user_id)


    except JWTError as e:
        print(f"auth_utils: Erro de JWTError: {e}") # DEBUG
        raise credentials_exception
    
    # user = crud.get_user_by_email(db, email=token_data.email)
    user = crud.get_user(db, user_id=token_data.user_id) # Buscar por ID é mais robusto se o email puder mudar

    if user is None:
        print(f"auth_utils: Usuário não encontrado no banco de dados com ID: {token_data.user_id} ou email: {token_data.email}") # DEBUG
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    if not current_user.is_active:
        # print(f"auth_utils: Usuário {current_user.email} está inativo.") # DEBUG (opcional)
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user)
) -> models.User:
    if not current_user.is_superuser:
        # print(f"auth_utils: Usuário {current_user.email} não é superuser.") # DEBUG (opcional)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user