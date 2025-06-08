from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend.auth import (
    oauth,
    OAuthError,
    process_google_login,
    process_facebook_login,
    create_access_token,
    create_refresh_token,
)
from Backend.database import get_db
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend import schemas

router = APIRouter()
logger = get_logger(__name__)


@router.get("/google/login")
async def google_login(request: Request):
    """Redirects the user to Google's OAuth consent page."""
    if "google" not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth não configurado.",
        )
    redirect_uri = settings.GOOGLE_REDIRECT_URI
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/google/callback", response_model=schemas.Token)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    """Handles Google OAuth callback and returns API tokens."""
    if "google" not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth não configurado.",
        )
    try:
        token = await oauth.google.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao autorizar com Google.")

    try:
        userinfo = await oauth.google.parse_id_token(request, token)
    except Exception:
        resp = await oauth.google.get("userinfo", token=token)
        userinfo = resp.json()

    user = await process_google_login(db, userinfo)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível autenticar o usuário Google.")

    access = create_access_token({"sub": user.email, "user_id": user.id})
    refresh = create_refresh_token({"sub": user.email, "user_id": user.id})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.get("/facebook/login")
async def facebook_login(request: Request):
    """Redirects the user to Facebook's OAuth consent page."""
    if "facebook" not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook OAuth não configurado.",
        )
    redirect_uri = settings.FACEBOOK_REDIRECT_URI
    return await oauth.facebook.authorize_redirect(request, redirect_uri)


@router.get("/facebook/callback", response_model=schemas.Token)
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    """Handles Facebook OAuth callback and returns API tokens."""
    if "facebook" not in oauth._clients:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Facebook OAuth não configurado.",
        )

    try:
        token = await oauth.facebook.authorize_access_token(request)
    except OAuthError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Erro ao autorizar com Facebook.")

    resp = await oauth.facebook.get("userinfo", token=token)
    userinfo = resp.json()

    user = await process_facebook_login(db, userinfo)
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível autenticar o usuário Facebook.")

    access = create_access_token({"sub": user.email, "user_id": user.id})
    refresh = create_refresh_token({"sub": user.email, "user_id": user.id})
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}
