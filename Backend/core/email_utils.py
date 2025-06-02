# Backend/core/email_utils.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List, Dict, Any, Optional # Adicionado Optional
from pathlib import Path

from .config import settings # Importa as configurações (settings)
# Removido import desnecessário de auth que estava no arquivo do usuário
# import auth # Cuidado com import circular se auth importar email_utils

# Define o diretório de templates de email
# Se email_utils.py está em Backend/core/ e templates está em Backend/templates/
TEMPLATE_FOLDER = Path(__file__).parent.parent / 'templates'
# print(f"DEBUG: Email Template folder: {TEMPLATE_FOLDER.resolve()}") # Para depuração

conf = None
if settings.MAIL_USERNAME and settings.MAIL_PASSWORD and settings.MAIL_FROM and settings.MAIL_SERVER:
    conf = ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=settings.USE_CREDENTIALS,
        VALIDATE_CERTS=settings.VALIDATE_CERTS,
        TEMPLATE_FOLDER=TEMPLATE_FOLDER # Adiciona o diretório de templates à configuração
    )
else:
    print("AVISO: Configurações de Email (MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER) incompletas no .env. Funcionalidade de envio de email desabilitada.")


async def send_email(
    email_to: EmailStr,
    subject: str,
    html_content: str, # Alterado de body para html_content para clareza
    # attachments: Optional[List[UploadFile]] = None, # Se precisar enviar anexos
    template_body: Optional[Dict[str, Any]] = None, # Para usar com templates
    template_name: Optional[str] = None
):
    if not conf:
        print(f"AVISO: Tentativa de enviar email para {email_to} com assunto '{subject}', mas a configuração de email está desabilitada.")
        return

    message_data = {
        "subject": subject,
        "recipients": [email_to],
        # "attachments": attachments or []
    }

    if template_name:
        message_data["template_body"] = template_body or {}
        message = MessageSchema(**message_data) # type: ignore
        # print(f"DEBUG: Enviando email com template '{template_name}' para {email_to}")
        # print(f"DEBUG: Template body: {template_body}")
        # print(f"DEBUG: MessageSchema data: {message.model_dump()}")
        
        fm = FastMail(conf)
        try:
            await fm.send_message(message, template_name=template_name)
            print(f"INFO: Email com template '{template_name}' enviado para {email_to}.")
        except Exception as e:
            print(f"ERRO: Falha ao enviar email com template para {email_to}. Erro: {e}")
            # Considerar levantar uma exceção aqui ou retornar um status de falha
            # raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {e}")
            pass # Evita quebrar a aplicação se o email falhar, mas loga o erro
    elif html_content: # Se não for template, usa html_content
        message_data["body"] = html_content
        message_data["message_type"] = MessageType.html # Define o tipo como HTML
        message = MessageSchema(**message_data) # type: ignore
        # print(f"DEBUG: Enviando email HTML para {email_to}")
        fm = FastMail(conf)
        try:
            await fm.send_message(message)
            print(f"INFO: Email HTML enviado para {email_to}.")
        except Exception as e:
            print(f"ERRO: Falha ao enviar email HTML para {email_to}. Erro: {e}")
            pass
    else:
        print(f"AVISO: Tentativa de enviar email para {email_to} sem template_name ou html_content.")


# NOVA FUNÇÃO ADICIONADA
async def send_password_reset_email(email_to: EmailStr, username: str, reset_link: str):
    """
    Envia um email de redefinição de senha para o usuário.
    """
    if not conf:
        print(f"AVISO: Tentativa de enviar email de reset de senha para {email_to}, mas a configuração de email está desabilitada.")
        # Em um cenário real, você pode querer levantar uma exceção aqui
        # ou retornar um status que indique que o email não pôde ser enviado.
        # Por enquanto, apenas logamos e não enviamos.
        # Se esta função for chamada de um endpoint, o endpoint deve lidar com a falha.
        # raise HTTPException(status_code=500, detail="Serviço de email não configurado.")
        return 

    subject = "Redefinição de Senha - TDAI"
    template_name = "password_reset_email.html" # Nome do arquivo de template em Backend/templates/
    
    template_body = {
        "username": username,
        "reset_link": reset_link,
        "project_name": settings.PROJECT_NAME, # Passa o nome do projeto para o template
        "valid_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES # Passa o tempo de validade do token
    }

    # Construindo MessageSchema
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=template_body, # Para uso com template_name
        subtype=MessageType.html # Garante que o email seja enviado como HTML
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message, template_name=template_name)
        print(f"INFO: Email de reset de senha enviado para {email_to}")
    except Exception as e:
        print(f"ERRO: Falha ao enviar email de reset de senha para {email_to}. Erro: {e}")
        # Considerar levantar uma exceção aqui para que o chamador possa tratar
        raise RuntimeError(f"Falha ao enviar email de reset de senha: {e}")


async def send_new_account_email(email_to: EmailStr, username: str, login_link: str):
    """
    Envia um email de boas-vindas para um novo usuário. (Exemplo, não usado ainda)
    """
    if not conf:
        print(f"AVISO: Tentativa de enviar email de boas-vindas para {email_to}, mas a configuração de email está desabilitada.")
        return

    subject = f"Bem-vindo ao {settings.PROJECT_NAME}!"
    # Você precisaria de um template new_account_email.html
    template_name = "new_account_email.html" # Supondo que você crie este template
    
    template_body = {
        "username": username,
        "login_link": login_link,
        "project_name": settings.PROJECT_NAME
    }
    
    message = MessageSchema(
        subject=subject,
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html
    )

    fm = FastMail(conf)
    try:
        await fm.send_message(message, template_name=template_name)
        print(f"INFO: Email de boas-vindas enviado para {email_to}")
    except Exception as e:
        print(f"ERRO: Falha ao enviar email de boas-vindas para {email_to}. Erro: {e}")
        raise RuntimeError(f"Falha ao enviar email de boas-vindas: {e}")