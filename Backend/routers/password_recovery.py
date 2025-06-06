# Backend/routers/password_recovery.py

import secrets
from datetime import datetime, timedelta, timezone # Adicionado timezone
from fastapi import APIRouter, Depends, HTTPException, Request, status, Body # Adicionado Body
from sqlalchemy.orm import Session

import crud
import schemas # schemas é importado
import models # models é importado
from database import get_db # Corrigido para get_db
from core.config import settings # Para FRONTEND_URL
from core.email_utils import send_password_reset_email # Importa a função de envio de email

router = APIRouter(
    prefix="/api/v1/auth", # Mantendo o prefixo como no arquivo original, se for este
    tags=["password-recovery"],
)

@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def recover_password(email: str, request: Request, db: Session = Depends(get_db)):
    """
    Envia um email de recuperação de senha para o usuário.
    """
    user = crud.get_user_by_email(db, email=email)
    if not user:
        # Não revelar se o usuário existe ou não por motivos de segurança,
        # mas para depuração, um erro 404 seria mais claro.
        # Em produção, uma mensagem genérica é melhor.
        # raise HTTPException(
        # status_code=404,
        # detail="O email fornecido não foi encontrado em nosso sistema.",
        # )
        # No entanto, para evitar enumeração de usuários, retornamos sucesso mesmo se não encontrado.
        print(f"INFO: Solicitação de recuperação de senha para email não registrado: {email}")
        return {"msg": "Se um usuário com este email existir, um link de recuperação foi enviado."}


    # Gerar token de reset
    token = secrets.token_urlsafe(32)
    expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # Usar uma configuração específica para reset seria melhor
    expires_at = datetime.now(timezone.utc) + expires_delta # Usar timezone.utc
    
    # Salvar o token e a data de expiração no usuário
    crud.update_user_password_reset_token(db, user_id=user.id, token=token, expires_at=expires_at)

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
        print(f"ERRO: Falha ao enviar email de recuperação de senha para {user.email}: {e}")
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
    user = crud.get_user_by_reset_token(db, token=reset_data.token)
    
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reset inválido.")
    
    if not user.reset_password_token_expires_at or user.reset_password_token_expires_at < datetime.now(timezone.utc): # Usar timezone.utc
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token de reset expirado.")

    # Atualizar a senha do usuário
    hashed_password = crud.get_password_hash(reset_data.new_password)
    user_update_data = schemas.UserUpdate(password=reset_data.new_password) # Criar um schema de update
    
    # Para atualizar apenas a senha e limpar o token:
    db_user = crud.get_user(db, user_id=user.id) # Busca o usuário novamente para garantir que temos o objeto da sessão
    if db_user:
        db_user.hashed_password = hashed_password
        db_user.reset_password_token = None # Limpa o token após o uso
        db_user.reset_password_token_expires_at = None # Limpa a data de expiração
        db.commit()
    else:
        # Isso não deveria acontecer se get_user_by_reset_token retornou um usuário
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro ao atualizar senha.")

    return {"msg": "Senha atualizada com sucesso."}
