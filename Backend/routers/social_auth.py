from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend.core.deprecation import deprecated_legacy_service_proxy
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


class _SocialAuthRouterRuntime:
    """Runtime OO para integrações de autenticação social."""

    def has_client(self, provider: str) -> bool:
        return provider in oauth._clients

    async def authorize_redirect(self, provider: str, request: Request, redirect_uri: str):
        return await getattr(oauth, provider).authorize_redirect(request, redirect_uri)

    async def authorize_access_token(self, provider: str, request: Request):
        return await getattr(oauth, provider).authorize_access_token(request)

    async def parse_google_id_token(self, request: Request, token):
        return await oauth.google.parse_id_token(request, token)

    async def get_userinfo(self, provider: str, token):
        resp = await getattr(oauth, provider).get("userinfo", token=token)
        return resp.json()

    async def process_google_login(self, db: Session, userinfo):
        return await process_google_login(db, userinfo)

    async def process_facebook_login(self, db: Session, userinfo):
        return await process_facebook_login(db, userinfo)

    def create_access_token(self, payload):
        return create_access_token(payload)

    def create_refresh_token(self, payload):
        return create_refresh_token(payload)


class _SocialAuthRouterWorkflow:
    def __init__(self, runtime: _SocialAuthRouterRuntime | None = None) -> None:
        self._runtime = runtime or _SocialAuthRouterRuntime()

    def social_login_config(self) -> schemas.SocialLoginConfig:
        return schemas.SocialLoginConfig(
            google_enabled=self._runtime.has_client("google"),
            facebook_enabled=self._runtime.has_client("facebook"),
        )

    async def google_login(self, request: Request):
        if not self._runtime.has_client("google"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )
        redirect_uri = settings.GOOGLE_REDIRECT_URI
        return await self._runtime.authorize_redirect("google", request, redirect_uri)

    async def google_callback(self, request: Request, db: Session) -> schemas.Token:
        if not self._runtime.has_client("google"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )

        try:
            token = await self._runtime.authorize_access_token("google", request)
        except OAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Google.",
            )

        try:
            userinfo = await self._runtime.parse_google_id_token(request, token)
        except Exception:
            userinfo = await self._runtime.get_userinfo("google", token)

        user = await self._runtime.process_google_login(db, userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Google.",
            )

        access = self._runtime.create_access_token({"sub": user.email, "user_id": user.id})
        refresh = self._runtime.create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")

    async def facebook_login(self, request: Request):
        if not self._runtime.has_client("facebook"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )
        redirect_uri = settings.FACEBOOK_REDIRECT_URI
        return await self._runtime.authorize_redirect("facebook", request, redirect_uri)

    async def facebook_callback(self, request: Request, db: Session) -> schemas.Token:
        if not self._runtime.has_client("facebook"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )

        try:
            token = await self._runtime.authorize_access_token("facebook", request)
        except OAuthError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Facebook.",
            )

        userinfo = await self._runtime.get_userinfo("facebook", token)

        user = await self._runtime.process_facebook_login(db, userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Facebook.",
            )

        access = self._runtime.create_access_token({"sub": user.email, "user_id": user.id})
        refresh = self._runtime.create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")


social_auth_router_runtime = _SocialAuthRouterRuntime()
social_auth_router_workflow = _SocialAuthRouterWorkflow(runtime=social_auth_router_runtime)


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


social_auth_router_legacy_service = deprecated_legacy_service_proxy(
    SocialAuthRouterLegacyService(),
    qualified_name="Backend.routers.social_auth.social_auth_router_legacy_service",
)
