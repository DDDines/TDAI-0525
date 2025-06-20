# Backend/core/email_utils.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List, Dict, Any, Optional # Adicionado Optional
from pathlib import Path
from datetime import datetime
from .config import settings  # Importa as configurações (settings)
from .logging_config import get_logger

# Removido import desnecessário de auth que estava no arquivo do usuário
# import auth # Cuidado com import circular se auth importar email_utils

# Define o diretório de templates de email
# Se email_utils.py está em Backend/core/ e templates está em Backend/templates/
TEMPLATE_FOLDER = Path(__file__).parent.parent / 'templates'
# print(f"DEBUG: Email Template folder: {TEMPLATE_FOLDER.resolve()}") # Para depuração

logger = get_logger(__name__)

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
    logger.warning(
        "Configurações de Email (MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER) incompletas no .env. Funcionalidade de envio de email desabilitada."
    )


async def send_email(
    email_to: EmailStr,
    subject: str,
    html_content: str,  # Alterado de body para html_content para clareza
    # attachments: Optional[List[UploadFile]] = None, # Se precisar enviar anexos
    template_body: Optional[Dict[str, Any]] = None,  # Para usar com templates
    template_name: Optional[str] = None,
    *,
    raise_if_unconfigured: Optional[bool] = None,
):
    if raise_if_unconfigured is None:
        raise_if_unconfigured = settings.RAISE_ON_MISSING_EMAIL_CONFIG

    if not conf:
        logger.warning(
            "Tentativa de enviar email para %s com assunto '%s', mas a configuração de email está desabilitada.",
            email_to,
            subject,
        )
        if raise_if_unconfigured:
            raise RuntimeError("Configuração de email ausente")
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
            logger.info("Email com template '%s' enviado para %s.", template_name, email_to)
        except Exception as e:
            logger.error("Falha ao enviar email com template para %s. Erro: %s", email_to, e)
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
            logger.info("Email HTML enviado para %s.", email_to)
        except Exception as e:
            logger.error("Falha ao enviar email HTML para %s. Erro: %s", email_to, e)
            pass
    else:
        logger.warning("Tentativa de enviar email para %s sem template_name ou html_content.", email_to)

        logger.warning(
            "Tentativa de enviar email para %s sem template_name ou html_content.",
            email_to,
        )


# NOVA FUNÇÃO ADICIONADA
async def send_password_reset_email(
    email_to: EmailStr,
    username: str,
    reset_link: str,
    *,
    raise_if_unconfigured: Optional[bool] = None,
):
    """Envia um email de redefinição de senha para o usuário."""

    if raise_if_unconfigured is None:
        raise_if_unconfigured = settings.RAISE_ON_MISSING_EMAIL_CONFIG

    if not conf:
        logger.warning(
            "Tentativa de enviar email de reset de senha para %s, mas a configuração de email está desabilitada.",
            email_to,
        )
        if raise_if_unconfigured:
            raise RuntimeError("Configuração de email ausente")
        return

    subject = "Redefinição de Senha - CatalogAI"
    template_name = "password_reset_email.html" # Nome do arquivo de template em Backend/templates/
    
    template_body = {
        "username": username,
        "reset_url": reset_link,
        "expiration_hours": settings.ACCESS_TOKEN_EXPIRE_MINUTES // 60,
        "current_year": datetime.now().year,
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
        logger.info("Email de reset de senha enviado para %s", email_to)
    except Exception as e:
        logger.error("Falha ao enviar email de reset de senha para %s. Erro: %s", email_to, e)
        # Considerar levantar uma exceção aqui para que o chamador possa tratar
        raise RuntimeError(f"Falha ao enviar email de reset de senha: {e}")


