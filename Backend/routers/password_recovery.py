# Backend/routers/password_recovery.py

from datetime import datetime, timedelta, timezone  # Adicionado timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body # Adicionado Body
from sqlalchemy.orm import Session

from Backend import crud_users
from Backend import schemas  # schemas é importado
from Backend import models  # models é importado
from Backend.database import get_db  # Corrigido para get_db
from Backend.core.config import settings  # Para FRONTEND_URL
from Backend.core.email_utils import send_password_reset_email  # Importa a função de envio de email
from Backend.core import security
from Backend.core.logging_config import get_logger
from Backend.auth import create_password_reset_token, hash_password_reset_token

router = APIRouter(
    prefix="/auth",  # Prefixo reduzido; '/api/v1' será adicionado em main.py
    tags=["password-recovery"],
)

logger = get_logger(__name__)

@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def recover_password(email: str, request: Request, db: Session = Depends(get_db)):
    """
    Envia um email de recuperação de senha para o usuário.
    """
    user = crud_users.get_user_by_email(db, email=email)
    if not user:
        # Não revelar se o usuário existe ou não por motivos de segurança,
        # mas para depuração, um erro 404 seria mais claro.
        # Em produção, uma mensagem genérica é melhor.
        # raise HTTPException(
        # status_code=404,
        # detail="O email fornecido não foi encontrado em nosso sistema.",
        # )
        # No entanto, para evitar enumeração de usuários, retornamos sucesso mesmo se não encontrado.
        return {"msg": "Se um usuário com este email existir, um link de recuperação foi enviado."}


    # Gerar token de reset
    token = create_password_reset_token()
    token_hash = hash_password_reset_token(token)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # Usar uma configuração específica para reset seria melhor
    expires_at = datetime.now(timezone.utc) + expires_delta # Usar timezone.utc
    
    # Salvar o hash do token e a data de expiração no usuário
    crud_users.set_user_password_reset_token(db, user, token_hash=token_hash, expires_at=expires_at)

    # Enviar email
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    try:
        await send_password_reset_email(
            email_to=user.email,
            username=user.nome_completo or user.email, # Usa nome_completo se disponível
            reset_link=reset_link
        )
        return {"msg": "Email de recuperação de senha enviado com sucesso."}
    except Exception as e:
        # Logar o erro 'e' aqui seria importante
        logger.error("Falha ao enviar email de recuperação de senha para %s: %s", user.email, e)

        logger.error(
            "Falha ao enviar email de recuperação de senha para %s: %s",
            user.email,
            e,
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Houve um erro ao enviar o email de recuperação. Tente novamente mais tarde."
        )

@router.post("/reset-password/", response_model=schemas.Msg)
def reset_password(
    *, # Força os parâmetros seguintes a serem keyword-only
    db: Session = Depends(get_db),
    # CORRIGIDO AQUI:
    reset_data: schemas.PasswordResetSchema = Body(...), # Usa PasswordResetSchema
):
    """
    Define uma nova senha usando o token de reset.
    """
    token_hash = hash_password_reset_token(reset_data.token)
    user = crud_users.get_user_by_reset_token(db, token_hash=token_hash)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reset inválido.")
    
    if not user.reset_password_token_expires_at or user.reset_password_token_expires_at < datetime.now(timezone.utc): # Usar timezone.utc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reset expirado.")

    # Atualizar a senha do usuário
    hashed_password = security.get_password_hash(reset_data.new_password)
    user_update_data = schemas.UserUpdate(password=reset_data.new_password) # Criar um schema de update
    
    # Para atualizar apenas a senha e limpar o token:
    db_user = crud_users.get_user(db, user_id=user.id) # Busca o usuário novamente para garantir que temos o objeto da sessão
    if db_user:
        db_user.hashed_password = hashed_password
        db_user.reset_password_token = None # Limpa o token após o uso
        db_user.reset_password_token_expires_at = None # Limpa a data de expiração
        db.commit()
    else:
        # Isso não deveria acontecer se get_user_by_reset_token retornou um usuário
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar senha.")

    return {"msg": "Senha atualizada com sucesso."}
