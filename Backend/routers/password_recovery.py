"""Camada de transporte HTTP para o dominio 'password_recovery'."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.auth import AuthWorkflow
from Backend.core.config import settings
from Backend.core.email_utils import EmailWorkflow
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.user_repository import UserRepository


router = APIRouter(prefix="/auth", tags=["password-recovery"])
logger = get_logger(__name__)


class PasswordRecoveryRequestService:
    """Servico request-scoped para recuperacao e reset de senha."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        self._session = session
        self._auth_workflow = AuthWorkflow(session=session)
        self._email_workflow = EmailWorkflow()
        self._user_repository = UserRepository(session)

    async def recover_password(self, *, email: str, request: Request) -> schemas.Msg:
        _ = request
        user = self._user_repository.get_user_by_email(email=email)
        if not user:
            return schemas.Msg(
                msg="Se um usuario com este email existir, um link de recuperacao foi enviado."
            )

        token = self._auth_workflow.create_password_reset_token()
        token_hash = self._auth_workflow.hash_password_reset_token(token)
        expires_delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        expires_at = datetime.now(timezone.utc) + expires_delta
        self._user_repository.set_user_password_reset_token(
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        try:
            await self._email_workflow.send_password_reset_email(
                email_to=user.email,
                username=user.nome_completo or user.email,
                reset_link=reset_link,
            )
            return schemas.Msg(msg="Email de recuperacao de senha enviado com sucesso.")
        except Exception as exc:
            logger.error("Falha ao enviar email de recuperacao para %s: %s", user.email, exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=(
                    "Houve um erro ao enviar o email de recuperacao. "
                    "Tente novamente mais tarde."
                ),
            ) from exc

    def reset_password(self, *, reset_data: schemas.PasswordResetSchema) -> schemas.Msg:
        token_hash = self._auth_workflow.hash_password_reset_token(reset_data.token)
        user = self._user_repository.get_user_by_reset_token(token_hash=token_hash)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de reset invalido.",
            )
        if not user.reset_password_token_expires_at or user.reset_password_token_expires_at < datetime.now(
            timezone.utc
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token de reset expirado.",
            )

        db_user = self._user_repository.get_user(user_id=user.id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar senha.",
            )

        db_user.hashed_password = self._auth_workflow.get_password_hash(reset_data.new_password)
        db_user.reset_password_token = None
        db_user.reset_password_token_expires_at = None
        self._session.commit()
        return schemas.Msg(msg="Senha atualizada com sucesso.")


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def recover_password(
    email: str,
    request: Request,
    request_service: PasswordRecoveryRequestService = Depends(),
):
    return await request_service.recover_password(email=email, request=request)


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    *,
    reset_data: schemas.PasswordResetSchema = Body(...),
    request_service: PasswordRecoveryRequestService = Depends(),
):
    return request_service.reset_password(reset_data=reset_data)
