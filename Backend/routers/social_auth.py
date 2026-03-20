"""Camada de transporte HTTP para o dominio 'social_auth'."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
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
        """Initialize injected dependencies and runtime configuration for Social Auth Request Service."""
        self._session = session
        self._auth_workflow = AuthWorkflow(session=session)

    @staticmethod
    def _has_client(provider: str) -> bool:
        """Execute has client as part of this module workflow."""
        return provider in oauth._clients

    @staticmethod
    def _resolve_product_experience_default() -> str:
        """Normaliza o modo de experiencia publico para valores suportados."""
        configured = str(getattr(settings, "PRODUCT_EXPERIENCE_DEFAULT", "basic") or "basic").strip().lower()
        return configured if configured in {"basic", "complete"} else "basic"

    @staticmethod
    async def _authorize_redirect(provider: str, request: Request, redirect_uri: str):
        """Execute authorize redirect as part of this module workflow."""
        return await getattr(oauth, provider).authorize_redirect(request, redirect_uri)

    @staticmethod
    async def _authorize_access_token(provider: str, request: Request):
        """Execute authorize access token as part of this module workflow."""
        return await getattr(oauth, provider).authorize_access_token(request)

    @staticmethod
    async def _parse_google_id_token(request: Request, token):
        """Parse google id token into structured data used by downstream logic."""
        return await oauth.google.parse_id_token(request, token)

    @staticmethod
    async def _get_userinfo(provider: str, token):
        """Retrieve userinfo using the current service dependencies."""
        resp = await getattr(oauth, provider).get("userinfo", token=token)
        return resp.json()

    def social_login_config(self) -> schemas.SocialLoginConfig:
        """Execute social login config as part of this module workflow."""
        return schemas.SocialLoginConfig(
            google_enabled=self._has_client("google"),
            facebook_enabled=self._has_client("facebook"),
            product_experience_default=self._resolve_product_experience_default(),
            allow_admin_experience_preview=bool(
                getattr(settings, "ALLOW_ADMIN_EXPERIENCE_PREVIEW", True)
            ),
        )

    async def google_login(self, request: Request):
        """Execute google login as part of this module workflow."""
        if not self._has_client("google"):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Google OAuth nao configurado.",
            )
        return await self._authorize_redirect("google", request, settings.GOOGLE_REDIRECT_URI)

    async def google_callback(self, request: Request) -> RedirectResponse:
        """Execute google callback as part of this module workflow."""
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        if not self._has_client("google"):
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_not_configured")
        try:
            token = await self._authorize_access_token("google", request)
        except OAuthError as exc:
            logger.warning("Google OAuth error: %s", exc)
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed")

        try:
            userinfo = await self._parse_google_id_token(request, token)
        except Exception:
            userinfo = await self._get_userinfo("google", token)

        user = await self._auth_workflow.process_google_login(google_userinfo=userinfo)
        if not user:
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_user_failed")

        access = self._auth_workflow.create_access_token({"sub": user.email, "user_id": user.id})
        return RedirectResponse(url=f"{frontend_url}/auth/oauth-callback?access_token={access}")

    async def facebook_login(self, request: Request):
        """Execute facebook login as part of this module workflow."""
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

    async def facebook_callback(self, request: Request) -> RedirectResponse:
        """Execute facebook callback as part of this module workflow."""
        frontend_url = settings.FRONTEND_URL.rstrip("/")
        if not self._has_client("facebook"):
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_not_configured")
        try:
            token = await self._authorize_access_token("facebook", request)
        except OAuthError as exc:
            logger.warning("Facebook OAuth error: %s", exc)
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_failed")

        userinfo = await self._get_userinfo("facebook", token)
        user = await self._auth_workflow.process_facebook_login(facebook_userinfo=userinfo)
        if not user:
            return RedirectResponse(url=f"{frontend_url}/login?error=oauth_user_failed")

        access = self._auth_workflow.create_access_token({"sub": user.email, "user_id": user.id})
        return RedirectResponse(url=f"{frontend_url}/auth/oauth-callback?access_token={access}")


@router.get("/social/config", response_model=schemas.SocialLoginConfig)
async def social_login_config(request_service: SocialAuthRequestService = Depends()):
    """Execute social login config as part of this module workflow."""
    return request_service.social_login_config()


@router.get("/google/login")
async def google_login(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Execute google login as part of this module workflow."""
    return await request_service.google_login(request)


@router.get("/google/callback")
async def google_callback(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Execute google callback as part of this module workflow."""
    return await request_service.google_callback(request)


@router.get("/facebook/login")
async def facebook_login(request: Request, request_service: SocialAuthRequestService = Depends()):
    """Execute facebook login as part of this module workflow."""
    return await request_service.facebook_login(request)


@router.get("/facebook/callback")
async def facebook_callback(
    request: Request,
    request_service: SocialAuthRequestService = Depends(),
):
    """Execute facebook callback as part of this module workflow."""
    return await request_service.facebook_callback(request)
