# Backend/routers/auth_utils.py
from fastapi import Depends, HTTPException, status, Request # Adicionado Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
import json # Para pretty print dos headers

import crud # models e schemas são usados via crud ou diretamente se necessário
import models
import schemas
from core.config import settings
import database

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

async def get_current_user(
    request: Request, # Adicionado Request para acessar headers
    db: Session = Depends(database.get_db),
    token: str = Depends(oauth2_scheme)
) -> models.User:

    # DEBUG LOG: Imprimir cabeçalhos da requisição
    print(f"\n--- DEBUG: auth_utils.get_current_user ---")
    print(f"Path da Requisição: {request.url.path}")
    try:
        # Pretty print headers if possible
        headers_dict = dict(request.headers)
        print(f"Headers Recebidos (raw): {headers_dict}")
        # Especificamente procurar por 'authorization'
        auth_header = headers_dict.get('authorization')
        if auth_header:
            print(f"Cabeçalho 'authorization' encontrado: {auth_header[:30]}...") # Snippet do token
        else:
            print("Cabeçalho 'authorization' NÃO encontrado.")
    except Exception as e:
        print(f"Erro ao tentar logar headers: {e}")
    print(f"--- FIM DEBUG: auth_utils.get_current_user ---\n")
    # Fim do DEBUG LOG

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials", # Esta é a mensagem que o frontend está recebendo como "Not authenticated"
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        if email is None or user_id is None:
            print(f"auth_utils: Email ({email}) ou user_id ({user_id}) ausente/inválido no payload do token.")
            raise credentials_exception
        token_data = schemas.TokenData(email=email, user_id=user_id)

    except JWTError as e:
        print(f"auth_utils: Erro de JWTError ao decodificar token: {e}. Token problemático (snippet): {token[:30]}...")
        raise credentials_exception

    user = crud.get_user(db, user_id=token_data.user_id)

    if user is None:
        print(f"auth_utils: Usuário não encontrado no DB com ID: {token_data.user_id} (do token com email: {token_data.email})")
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user