"""Camada de transporte HTTP para o dominio 'auth_utils'."""
# Backend/routers/auth_utils.py
from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.service_container import (
    build_request_scoped_dependency,
)
from Backend.core import config
from Backend.core import security
from Backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.settings.API_V1_STR}/auth/token")


class _AuthUtilsRuntime:
    """Runtime OO para operacoes de autenticacao do router."""

    def __init__(self) -> None:
        self._security_workflow = security.get_security_workflow()

    def decode_token(self, token: str, secret_key: str):
        return self._security_workflow.decode_token(token, secret_key)

    def get_user(self, db: Session, user_id: int):
        return UserRepository(db).get_user(user_id=user_id)


class _AuthUtilsWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'auth_utils'."""

    def __init__(self, runtime: _AuthUtilsRuntime | None = None) -> None:
        self._runtime = runtime or _AuthUtilsRuntime()

    async def get_current_user(
        self,
        request: Request,
        db: Session,
        token: str,
    ) -> models.User:
        _ = request
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

        token_payload = self._runtime.decode_token(token, config.settings.SECRET_KEY)
        if token_payload is None or token_payload.user_id is None:
            logger.warning("Token invalido ou user_id ausente no payload. Token: %s...", token[:20])
            raise credentials_exception

        user = self._runtime.get_user(db, user_id=token_payload.user_id)
        if user is None:
            logger.warning("Usuario nao encontrado no DB para user_id: %s", token_payload.user_id)
            raise credentials_exception
        return user

    async def get_current_active_user(self, current_user: models.User) -> models.User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return current_user

    async def get_current_active_superuser(self, current_user: models.User) -> models.User:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user


AuthUtilsWorkflow = _AuthUtilsWorkflow


get_auth_utils_workflow = lambda: AuthUtilsWorkflow(runtime=_AuthUtilsRuntime())


_build_auth_request_session = build_request_scoped_dependency(lambda session: session)


class _AuthUtilsCurrentUserDependency:
    @staticmethod
    async def get_current_user(
        request: Request,
        session: Session = Depends(_build_auth_request_session),
        token: str = Depends(oauth2_scheme),
    ) -> models.User:
        """Resolve usuario autenticado atual via workflow OO."""
        workflow = get_auth_utils_workflow()
        return await workflow.get_current_user(
            request=request,
            db=session,
            token=token,
        )


get_current_user = _AuthUtilsCurrentUserDependency.get_current_user


class _AuthUtilsActiveUserDependency:
    @staticmethod
    async def get_current_active_user(
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        """Valida usuario ativo via workflow OO."""
        workflow = get_auth_utils_workflow()
        return await workflow.get_current_active_user(current_user=current_user)


get_current_active_user = _AuthUtilsActiveUserDependency.get_current_active_user


class _AuthUtilsSuperUserDependency:
    @staticmethod
    async def get_current_active_superuser(
        current_user: models.User = Depends(get_current_active_user),
    ) -> models.User:
        """Valida privilegio de superusuario via workflow OO."""
        workflow = get_auth_utils_workflow()
        return await workflow.get_current_active_superuser(current_user=current_user)


get_current_active_superuser = _AuthUtilsSuperUserDependency.get_current_active_superuser
