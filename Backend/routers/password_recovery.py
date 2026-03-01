from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.application.services.service_container import (
    DependencyContainer,
    SessionDep,
)
from Backend.auth import create_password_reset_token, hash_password_reset_token
from Backend.core import security
from Backend.core.config import settings
from Backend.core.email_utils import send_password_reset_email
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.user_repository import UserRepository
router = APIRouter(prefix="/auth", tags=["password-recovery"])
logger = get_logger(__name__)


class _PasswordRecoveryRuntime:
    """Runtime OO para operaÃ§Ãµes de recuperaÃ§Ã£o de senha."""

    def get_user_by_email(self, db: Session, email: str):
        return UserRepository(db).get_user_by_email(email=email)

    def create_password_reset_token(self) -> str:
        return create_password_reset_token()

    def hash_password_reset_token(self, token: str) -> str:
        return hash_password_reset_token(token)

    def set_user_password_reset_token(
        self,
        db: Session,
        user,
        *,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        UserRepository(db).set_user_password_reset_token(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    async def send_password_reset_email(
        self,
        *,
        email_to: str,
        username: str,
        reset_link: str,
    ) -> None:
        await send_password_reset_email(
            email_to=email_to,
            username=username,
            reset_link=reset_link,
        )

    def get_user_by_reset_token(self, db: Session, token_hash: str):
        return UserRepository(db).get_user_by_reset_token(
            token_hash=token_hash,
        )

    def get_user(self, db: Session, user_id: int):
        return UserRepository(db).get_user(user_id=user_id)

    def get_password_hash(self, raw_password: str) -> str:
        return security.get_password_hash(raw_password)


class _PasswordRecoveryWorkflow:
    def __init__(self, runtime: _PasswordRecoveryRuntime | None = None) -> None:
        self._runtime = runtime or _PasswordRecoveryRuntime()

    async def recover_password(
        self,
        db: Session,
        email: str,
        request: Request,
    ) -> schemas.Msg:
        _ = request
        user = self._runtime.get_user_by_email(db, email=email)
        if not user:
            return schemas.Msg(
                msg=(
                    "Se um usuario com este email existir, um link de "
                    "recuperacao foi enviado."
                )
            )

        token = self._runtime.create_password_reset_token()
        token_hash = self._runtime.hash_password_reset_token(token)
        expires_delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        expires_at = datetime.now(timezone.utc) + expires_delta

        self._runtime.set_user_password_reset_token(
            db,
            user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        try:
            await self._runtime.send_password_reset_email(
                email_to=user.email,
                username=user.nome_completo or user.email,
                reset_link=reset_link,
            )
            return schemas.Msg(msg="Email de recuperacao de senha enviado com sucesso.")
        except Exception as exc:
            logger.error(
                "Falha ao enviar email de recuperacao para %s: %s",
                user.email,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Houve um erro ao enviar o email de recuperacao. "
                    "Tente novamente mais tarde."
                ),
            ) from exc

    def reset_password(
        self,
        db: Session,
        reset_data: schemas.PasswordResetSchema,
    ) -> schemas.Msg:
        token_hash = self._runtime.hash_password_reset_token(reset_data.token)
        user = self._runtime.get_user_by_reset_token(db, token_hash=token_hash)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de reset invalido.",
            )

        if (
            not user.reset_password_token_expires_at
            or user.reset_password_token_expires_at < datetime.now(timezone.utc)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de reset expirado.",
            )

        db_user = self._runtime.get_user(db, user_id=user.id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar senha.",
            )

        db_user.hashed_password = self._runtime.get_password_hash(reset_data.new_password)
        db_user.reset_password_token = None
        db_user.reset_password_token_expires_at = None
        db.commit()
        return schemas.Msg(msg="Senha atualizada com sucesso.")


PasswordRecoveryWorkflow = _PasswordRecoveryWorkflow


def get_password_recovery_workflow() -> PasswordRecoveryWorkflow:
    return PasswordRecoveryWorkflow(runtime=_PasswordRecoveryRuntime())


class _PasswordRecoveryRequestContext:
    def __init__(self, db: Session) -> None:
        self.db=db


def _build_password_recovery_request_context(
    db: SessionDep,
) -> _PasswordRecoveryRequestContext:
    return _PasswordRecoveryRequestContext(db=db)


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def recover_password(
    email: str,
    request: Request,
    request_context: _PasswordRecoveryRequestContext = Depends(
        _build_password_recovery_request_context
    ),
):
    workflow = get_password_recovery_workflow()
    return await workflow.recover_password(
        db=request_context.db,
        email=email,
        request=request,
    )


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    *,
    reset_data: schemas.PasswordResetSchema = Body(...),
    request_context: _PasswordRecoveryRequestContext = Depends(
        _build_password_recovery_request_context
    ),
):
    workflow = get_password_recovery_workflow()
    return workflow.reset_password(
        db=request_context.db,
        reset_data=reset_data,
    )





