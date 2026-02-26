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


class _SocialAuthRouterWorkflow:
    def social_login_config(self) -> schemas.SocialLoginConfig:
        return schemas.SocialLoginConfig(
            google_enabled="google" in oauth._clients,
            facebook_enabled="facebook" in oauth._clients,
        )

    async def google_login(self, request: Request):
        if "google" not in oauth._clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        return await oauth.google.authorize_redirect(request, redirect_uri)

    async def google_callback(self, request: Request, db: Session) -> schemas.Token:
        if "google" not in oauth._clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )

        try:
            token = await oauth.google.authorize_access_token(request)
        except OAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Google.",
            )

        try:
            userinfo = await oauth.google.parse_id_token(request, token)
        except Exception:
            resp = await oauth.google.get("userinfo", token=token)
            userinfo = resp.json()

        user = await process_google_login(db, userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Google.",
            )

        access = create_access_token({"sub": user.email, "user_id": user.id})
        refresh = create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")

    async def facebook_login(self, request: Request):
        if "facebook" not in oauth._clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )
        redirect_uri = settings.FACEBOOK_REDIRECT_URI
        return await oauth.facebook.authorize_redirect(request, redirect_uri)

    async def facebook_callback(self, request: Request, db: Session) -> schemas.Token:
        if "facebook" not in oauth._clients:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )

        try:
            token = await oauth.facebook.authorize_access_token(request)
        except OAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Facebook.",
            )

        resp = await oauth.facebook.get("userinfo", token=token)
        userinfo = resp.json()

        user = await process_facebook_login(db, userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Facebook.",
            )

        access = create_access_token({"sub": user.email, "user_id": user.id})
        refresh = create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")


social_auth_router_workflow = _SocialAuthRouterWorkflow()


@router.get("/social/config", response_model=schemas.SocialLoginConfig)
async def social_login_config():
    return social_auth_router_workflow.social_login_config()


@router.get("/google/login")
async def google_login(request: Request):
    return await social_auth_router_workflow.google_login(request)


@router.get("/google/callback", response_model=schemas.Token)
async def google_callback(request: Request, db: Session = Depends(get_db)):
    return await social_auth_router_workflow.google_callback(request=request, db=db)


@router.get("/facebook/login")
async def facebook_login(request: Request):
    return await social_auth_router_workflow.facebook_login(request)


@router.get("/facebook/callback", response_model=schemas.Token)
async def facebook_callback(request: Request, db: Session = Depends(get_db)):
    return await social_auth_router_workflow.facebook_callback(request=request, db=db)


class SocialAuthRouterLegacyService:
    def social_login_config(self):
        return social_auth_router_workflow.social_login_config()

    async def google_login(self, *args, **kwargs):
        return await social_auth_router_workflow.google_login(*args, **kwargs)

    async def google_callback(self, *args, **kwargs):
        return await social_auth_router_workflow.google_callback(*args, **kwargs)

    async def facebook_login(self, *args, **kwargs):
        return await social_auth_router_workflow.facebook_login(*args, **kwargs)

    async def facebook_callback(self, *args, **kwargs):
        return await social_auth_router_workflow.facebook_callback(*args, **kwargs)


social_auth_router_legacy_service = SocialAuthRouterLegacyService()
