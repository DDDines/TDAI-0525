# tdai_project/Backend/routers/password_recovery.py
from fastapi import APIRouter, Depends, HTTPException, status, Body, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timezone # Adicionado timezone para user.updated_at

# CORREÇÕES DOS IMPORTS:
# '..' sobe um nível (de 'routers' para 'Backend')
import crud #
import models #
import schemas #
import auth #
from database import get_db #
from core.config import pwd_context #
from core.email_utils import send_reset_password_email #

router = APIRouter(
    prefix="/auth", 
    tags=["Password Recovery"],
)

@router.post("/password-recovery/{email}", response_model=schemas.Msg)
async def request_password_recovery(
    email: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_email(db, email=email)
    
    if user and user.is_active:
        password_reset_token = auth.create_password_reset_token(email=email)
        
        background_tasks.add_task(
            send_reset_password_email,
            email_to=user.email,
            username=user.nome or user.email,
            token=password_reset_token
        )
        print(f"INFO: Solicitação de reset de senha para {email}. Token (dev only): {password_reset_token}")

    return {"message": "Se um usuário com este email estiver cadastrado e ativo em nosso sistema, um link para redefinir a senha foi enviado."}


@router.post("/reset-password/", response_model=schemas.Msg)
async def reset_password_with_token(
    reset_data: schemas.PasswordResetRequest = Body(...),
    db: Session = Depends(get_db)
):
    email = auth.verify_password_reset_token(token=reset_data.token)
    
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de reset de senha inválido ou expirado.",
        )
    
    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário associado ao token não encontrado.",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuário está inativo e não pode resetar a senha."
        )

    hashed_password = pwd_context.hash(reset_data.new_password)
    user.hashed_password = hashed_password
    user.updated_at = datetime.now(timezone.utc) # Garante que updated_at seja atualizado
    db.add(user)
    db.commit()
    
    return {"message": "Senha atualizada com sucesso."}