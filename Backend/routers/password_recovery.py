from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from Backend import crud_users, schemas
from Backend.auth import create_password_reset_token, hash_password_reset_token
from Backend.core import security
from Backend.core.config import settings
from Backend.core.email_utils import send_password_reset_email
from Backend.core.logging_config import get_logger
from Backend.database import get_db

router = APIRouter(prefix="/auth", tags=["password-recovery"])
logger = get_logger(__name__)


class _PasswordRecoveryWorkflow:
    async def recover_password(
        self,
        db: Session,
        email: str,
        request: Request,
    ) -> schemas.Msg:
        _ = request
        user = crud_users.get_user_by_email(db, email=email)
        if not user:
            return schemas.Msg(
                msg=(
                    "Se um usuario com este email existir, um link de "
                    "recuperacao foi enviado."
                )
            )

        token = create_password_reset_token()
        token_hash = hash_password_reset_token(token)
        expires_delta = timedelta(hours=settings.PASSWORD_RESET_TOKEN_EXPIRE_HOURS)
        expires_at = datetime.now(timezone.utc) + expires_delta

        crud_users.set_user_password_reset_token(
            db,
            user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        try:
            await send_password_reset_email(
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
        token_hash = hash_password_reset_token(reset_data.token)
        user = crud_users.get_user_by_reset_token(db, token_hash=token_hash)
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

        db_user = crud_users.get_user(db, user_id=user.id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao atualizar senha.",
            )

        db_user.hashed_password = security.get_password_hash(reset_data.new_password)
        db_user.reset_password_token = None
        db_user.reset_password_token_expires_at = None
        db.commit()
        return schemas.Msg(msg="Senha atualizada com sucesso.")


_password_recovery_workflow = _PasswordRecoveryWorkflow()


@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def recover_password(email: str, request: Request, db: Session = Depends(get_db)):
    return await _password_recovery_workflow.recover_password(
        db=db,
        email=email,
        request=request,
    )


@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    *,
    db: Session = Depends(get_db),
    reset_data: schemas.PasswordResetSchema = Body(...),
):
    return _password_recovery_workflow.reset_password(db=db, reset_data=reset_data)


class PasswordRecoveryRouterLegacyService:
    """Camada de compatibilidade para chamadas legadas do router."""

    async def recover_password(self, *args, **kwargs):
        return await _password_recovery_workflow.recover_password(*args, **kwargs)

    def reset_password(self, *args, **kwargs):
        return _password_recovery_workflow.reset_password(*args, **kwargs)


password_recovery_router_legacy_service = PasswordRecoveryRouterLegacyService()
