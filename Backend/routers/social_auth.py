"""Camada de transporte HTTP para o dominio 'social_auth'."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.application.services.service_container import (
    build_request_scoped_dependency,
)
from Backend.auth import OAuthError, get_auth_workflow, oauth
from Backend.core.config import settings
from Backend.core.logging_config import get_logger

router = APIRouter()
logger = get_logger(__name__)


class _SocialAuthRouterRuntime:
    """Runtime OO para integracoes de autenticacao social."""

    def __init__(self) -> None:
        self._auth_workflow = get_auth_workflow()

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
        return await self._auth_workflow.process_google_login(
            db=db,
            google_userinfo=userinfo,
        )

    async def process_facebook_login(self, db: Session, userinfo):
        return await self._auth_workflow.process_facebook_login(
            db=db,
            facebook_userinfo=userinfo,
        )

    def create_access_token(self, payload):
        return self._auth_workflow.create_access_token(payload)

    def create_refresh_token(self, payload):
        return self._auth_workflow.create_refresh_token(payload)


class _SocialAuthRouterWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'social_auth'."""

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


SocialAuthRouterWorkflow = _SocialAuthRouterWorkflow


def get_social_auth_router_workflow() -> SocialAuthRouterWorkflow:
    """Factory de workflow OO para o modulo atual (get_social_auth_router_workflow)."""
    return SocialAuthRouterWorkflow(runtime=_SocialAuthRouterRuntime())


class _SocialAuthRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'social_auth'."""

    def __init__(self, db: Session, workflow: SocialAuthRouterWorkflow | None = None) -> None:
        self._db = db
        self._workflow = workflow or get_social_auth_router_workflow()

    async def google_callback(self, request: Request) -> schemas.Token:
        return await self._workflow.google_callback(
            request=request,
            db=self._db,
        )

    async def facebook_callback(self, request: Request) -> schemas.Token:
        return await self._workflow.facebook_callback(
            request=request,
            db=self._db,
        )


_build_social_auth_request_workflow = build_request_scoped_dependency(
    lambda session: _SocialAuthRequestScope(db=session),
)


@router.get("/social/config", response_model=schemas.SocialLoginConfig)
async def social_login_config():
    """Endpoint HTTP que delega a execucao para workflow/servico OO (social_login_config)."""
    workflow = get_social_auth_router_workflow()
    return workflow.social_login_config()


@router.get("/google/login")
async def google_login(request: Request):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (google_login)."""
    workflow = get_social_auth_router_workflow()
    return await workflow.google_login(request)


@router.get("/google/callback", response_model=schemas.Token)
async def google_callback(
    request: Request,
    request_workflow: _SocialAuthRequestScope = Depends(_build_social_auth_request_workflow),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (google_callback)."""
    return await request_workflow.google_callback(request=request)


@router.get("/facebook/login")
async def facebook_login(request: Request):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (facebook_login)."""
    workflow = get_social_auth_router_workflow()
    return await workflow.facebook_login(request)


@router.get("/facebook/callback", response_model=schemas.Token)
async def facebook_callback(
    request: Request,
    request_workflow: _SocialAuthRequestScope = Depends(_build_social_auth_request_workflow),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (facebook_callback)."""
    return await request_workflow.facebook_callback(request=request)
