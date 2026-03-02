"""Camada de transporte HTTP para o dominio 'social_auth'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.auth import AuthWorkflow, OAuthError, oauth
from Backend.core.config import settings
from Backend.core.logging_config import get_logger


router = APIRouter()
logger = get_logger(__name__)


class SocialAuthRequestService:
    """Servico request-scoped para login social (Google/Facebook)."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize dependencies for SocialAuthRequestService."""
        self._session = session
        self._auth_workflow = AuthWorkflow(session=session)

    @staticmethod
    def _has_client(provider: str) -> bool:
        """Has client."""
        return provider in oauth._clients

    @staticmethod
    async def _authorize_redirect(provider: str, request: Request, redirect_uri: str):
        """Authorize redirect."""
        return await getattr(oauth, provider).authorize_redirect(request, redirect_uri)

    @staticmethod
    async def _authorize_access_token(provider: str, request: Request):
        """Authorize access token."""
        return await getattr(oauth, provider).authorize_access_token(request)

    @staticmethod
    async def _parse_google_id_token(request: Request, token):
        """Parse google id token."""
        return await oauth.google.parse_id_token(request, token)

    @staticmethod
    async def _get_userinfo(provider: str, token):
        """Get userinfo."""
        resp = await getattr(oauth, provider).get("userinfo", token=token)
        return resp.json()

    def social_login_config(self) -> schemas.SocialLoginConfig:
        """Social login config."""
        return schemas.SocialLoginConfig(
            google_enabled=self._has_client("google"),
            facebook_enabled=self._has_client("facebook"),
        )

    async def google_login(self, request: Request):
        """Google login."""
        if not self._has_client("google"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )
        return await self._authorize_redirect("google", request, settings.GOOGLE_REDIRECT_URI)

    async def google_callback(self, request: Request) -> schemas.Token:
        """Google callback."""
        if not self._has_client("google"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )
        try:
            token = await self._authorize_access_token("google", request)
        except OAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Google.",
            ) from exc

        try:
            userinfo = await self._parse_google_id_token(request, token)
        except Exception:
            userinfo = await self._get_userinfo("google", token)

        user = await self._auth_workflow.process_google_login(google_userinfo=userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Google.",
            )

        access = self._auth_workflow.create_access_token({"sub": user.email, "user_id": user.id})
        refresh = self._auth_workflow.create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")

    async def facebook_login(self, request: Request):
        """Facebook login."""
        if not self._has_client("facebook"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )
        return await self._authorize_redirect(
            "facebook",
            request,
            settings.FACEBOOK_REDIRECT_URI,
        )

    async def facebook_callback(self, request: Request) -> schemas.Token:
        """Facebook callback."""
        if not self._has_client("facebook"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Facebook OAuth nao configurado.",
            )
        try:
            token = await self._authorize_access_token("facebook", request)
        except OAuthError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Erro ao autorizar com Facebook.",
            ) from exc

        userinfo = await self._get_userinfo("facebook", token)
        user = await self._auth_workflow.process_facebook_login(facebook_userinfo=userinfo)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nao foi possivel autenticar o usuario Facebook.",
            )

        access = self._auth_workflow.create_access_token({"sub": user.email, "user_id": user.id})
        refresh = self._auth_workflow.create_refresh_token({"sub": user.email, "user_id": user.id})
        return schemas.Token(access_token=access, refresh_token=refresh, token_type="bearer")


@router.get("/social/config", response_model=schemas.SocialLoginConfig)
async def social_login_config(request_service: SocialAuthRequestService = Depends()):
    """Social login config."""
    return request_service.social_login_config()


@router.get("/google/login")
async def google_login(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Google login."""
    return await request_service.google_login(request)


@router.get("/google/callback", response_model=schemas.Token)
async def google_callback(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Google callback."""
    return await request_service.google_callback(request)


@router.get("/facebook/login")
async def facebook_login(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Facebook login."""
    return await request_service.facebook_login(request)


@router.get("/facebook/callback", response_model=schemas.Token)
async def facebook_callback(
    request: Request,
    request_service: SocialAuthRequestService = Depends(),
):
    """Facebook callback."""
    return await request_service.facebook_callback(request)
