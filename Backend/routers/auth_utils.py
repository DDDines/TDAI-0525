"""Camada de transporte HTTP para o dominio 'auth_utils'."""

from __future__ import annotations

import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core import config, security
from Backend.infrastructure.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.settings.API_V1_STR}/auth/token")


class AuthRequestService:
    """Servico OO para resolucao de usuario autenticado e validacoes de acesso."""

    def __init__(
        self,
        *,
        security_workflow: security.SecurityWorkflow | None = None,
        user_repository_cls: type[UserRepository] = UserRepository,
    ) -> None:
        self._security_workflow = security_workflow or security.SecurityWorkflow()
        self._user_repository_cls = user_repository_cls

    def _decode_token(self, token: str):
        return self._security_workflow.decode_token(token, config.settings.SECRET_KEY)

    def _get_user(self, session: Session, user_id: int):
        return self._user_repository_cls(session).get_user(user_id=user_id)

    async def get_current_user(
        self,
        *,
        request: Request,
        session: Session,
        token: str,
    ) -> models.User:
        _ = request
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        token_payload = self._decode_token(token)
        if token_payload is None or token_payload.user_id is None:
            logger.warning("Token invalido ou user_id ausente no payload. Token: %s...", token[:20])
            raise credentials_exception
        user = self._get_user(session, user_id=token_payload.user_id)
        if user is None:
            logger.warning("Usuario nao encontrado no DB para user_id: %s", token_payload.user_id)
            raise credentials_exception
        return user

    @staticmethod
    async def get_current_active_user(*, current_user: models.User) -> models.User:
        if not current_user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
        return current_user

    @staticmethod
    async def get_current_active_superuser(*, current_user: models.User) -> models.User:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="The user doesn't have enough privileges",
            )
        return current_user


class _AuthUtilsCurrentUserDependency:

    @staticmethod
    async def get_current_user(
        request: Request,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
        token: str = Depends(oauth2_scheme),
    ) -> models.User:
        service = AuthRequestService()
        return await service.get_current_user(request=request, session=session, token=token)


class _AuthUtilsActiveUserDependency:

    @staticmethod
    async def get_current_active_user(
        current_user: models.User = Depends(_AuthUtilsCurrentUserDependency.get_current_user),
    ) -> models.User:
        return await AuthRequestService.get_current_active_user(current_user=current_user)


class _AuthUtilsSuperUserDependency:

    @staticmethod
    async def get_current_active_superuser(
        current_user: models.User = Depends(_AuthUtilsActiveUserDependency.get_current_active_user),
    ) -> models.User:
        return await AuthRequestService.get_current_active_superuser(current_user=current_user)
