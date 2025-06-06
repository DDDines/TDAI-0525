# Backend/routers/social_auth.py

"""Endpoints para autenticação social (Google e Facebook)"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from auth import (
    oauth,
    process_google_login,
    process_facebook_login,
    create_access_token,
    create_refresh_token,
)
from database import get_db
from core.config import settings
from core.logging_config import get_logger
import schemas

router = APIRouter()
logger = get_logger(__name__)


@router.get("/google/login")
async def google_login(request: Request):
    """Redireciona o usuário para o fluxo de autenticação do Google."""
    if not (settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Google OAuth não configurado")
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=schemas.Token)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Processa o retorno do Google OAuth e emite tokens da aplicação."""
    try:
        token = await oauth.google.authorize_access_token(request)
    except Exception as e:
        logger.error("Erro ao autorizar login do Google: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro de autenticação com Google")

    userinfo = token.get("userinfo")
    if not userinfo:
        try:
            userinfo = await oauth.google.parse_id_token(request, token)
        except Exception:
            resp = await oauth.google.get("userinfo", token=token)
            userinfo = resp.json()

    user = await process_google_login(db, userinfo)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível autenticar via Google")

    access_token = create_access_token({"sub": user.email, "user_id": user.id})
    refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}


@router.get("/facebook/login")
async def facebook_login(request: Request):
    """Redireciona o usuário para o fluxo de autenticação do Facebook."""
    if not (settings.FACEBOOK_CLIENT_ID and settings.FACEBOOK_CLIENT_SECRET):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Facebook OAuth não configurado")
    redirect_uri = settings.FACEBOOK_REDIRECT_URI
    return await oauth.facebook.authorize_redirect(request, redirect_uri)


@router.get("/facebook/callback", response_model=schemas.Token)
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    """Processa o retorno do Facebook OAuth e emite tokens da aplicação."""
    try:
        token = await oauth.facebook.authorize_access_token(request)
    except Exception as e:
        logger.error("Erro ao autorizar login do Facebook: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro de autenticação com Facebook")

    resp = await oauth.facebook.get("me?fields=id,name,email", token=token)
    userinfo = resp.json()

    user = await process_facebook_login(db, userinfo)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível autenticar via Facebook")

    access_token = create_access_token({"sub": user.email, "user_id": user.id})
    refresh_token = create_refresh_token({"sub": user.email, "user_id": user.id})
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}
