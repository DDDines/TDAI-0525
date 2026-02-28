# Backend/routers/auth_utils.py
import logging

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from Backend import crud_users
from Backend import models
from Backend.core import config
from Backend.core import security
from Backend.database import get_db

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{config.settings.API_V1_STR}/auth/token")


class _AuthUtilsRuntime:
    """Runtime OO para operações de autenticação do router."""

    def decode_token(self, token: str, secret_key: str):
        return security.decode_token(token, secret_key)

    def get_user(self, db: Session, user_id: int):
        return crud_users.get_user(db, user_id=user_id)


class _AuthUtilsWorkflow:
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


auth_utils_runtime = _AuthUtilsRuntime()
auth_utils_workflow = _AuthUtilsWorkflow(runtime=auth_utils_runtime)


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> models.User:
    return await auth_utils_workflow.get_current_user(
        request=request,
        db=db,
        token=token,
    )


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user),
) -> models.User:
    return await auth_utils_workflow.get_current_active_user(current_user=current_user)


async def get_current_active_superuser(
    current_user: models.User = Depends(get_current_active_user),
) -> models.User:
    return await auth_utils_workflow.get_current_active_superuser(current_user=current_user)


class AuthUtilsLegacyService:
    async def get_current_user(self, *args, **kwargs):
        return await auth_utils_workflow.get_current_user(*args, **kwargs)

    async def get_current_active_user(self, *args, **kwargs):
        return await auth_utils_workflow.get_current_active_user(*args, **kwargs)

    async def get_current_active_superuser(self, *args, **kwargs):
        return await auth_utils_workflow.get_current_active_superuser(*args, **kwargs)


