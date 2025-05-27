# tdai_project/Backend/core/email_utils.py
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType
from pydantic import EmailStr
from typing import List, Dict, Any, Optional
from pathlib import Path

# CORREÇÃO: '.' indica o diretório atual ('core') para encontrar config.py
from .config import settings #

# CORREÇÃO: '..' sobe um nível para 'Backend/' para encontrar auth.py
# Precisamos importar 'auth' para tentar obter a constante,
# ou usar um valor de settings/default se não encontrada.
try:
    from .. import auth #
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS_EMAIL = auth.PASSWORD_RESET_TOKEN_EXPIRE_HOURS
except (ImportError, AttributeError):
    # Fallback se auth não puder ser importado ainda ou não tiver a constante
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS_EMAIL = getattr(settings, 'PASSWORD_RESET_TOKEN_EXPIRE_HOURS', 1)


# Inicializar fm como None. Ele só será configurado se as settings estiverem presentes.
fm: Optional[FastMail] = None
email_configured_properly: bool = False

# Verifica se as configurações mínimas de email estão presentes para inicializar FastMail
if settings.MAIL_USERNAME and \
   settings.MAIL_PASSWORD and \
   settings.MAIL_FROM and \
   settings.MAIL_SERVER:
    try:
        conf = ConnectionConfig(
            MAIL_USERNAME=str(settings.MAIL_USERNAME),
            MAIL_PASSWORD=str(settings.MAIL_PASSWORD),
            MAIL_FROM=EmailStr(str(settings.MAIL_FROM)),
            MAIL_PORT=settings.MAIL_PORT,
            MAIL_SERVER=str(settings.MAIL_SERVER),
            MAIL_FROM_NAME=settings.MAIL_FROM_NAME or "Equipe TDAI", # Default se None
            MAIL_STARTTLS=settings.MAIL_STARTTLS,
            MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
            USE_CREDENTIALS=settings.USE_CREDENTIALS,
            VALIDATE_CERTS=settings.VALIDATE_CERTS,
            TEMPLATE_FOLDER=Path(__file__).parent.parent / 'templates' # Aponta para Backend/templates
        )
        fm = FastMail(conf)
        email_configured_properly = True
        print("INFO:     Configuração de Email (FastMail) inicializada com sucesso.")
    except Exception as e:
        print(f"ERRO ao inicializar ConnectionConfig para FastMail: {e}")
        print("AVISO:   Configurações de Email parecem presentes mas são inválidas. Funcionalidade de envio de email desabilitada.")
        fm = None
        email_configured_properly = False
else:
    print("AVISO:   Configurações de Email (MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER) incompletas no .env. Funcionalidade de envio de email desabilitada.")


async def send_reset_password_email(
    email_to: EmailStr,
    username: str,
    token: str
):
    """
    Envia o email de reset de senha.
    """
    if not email_configured_properly or not fm:
        print(f"AVISO: Envio de email desabilitado (configuração incompleta ou falhou na inicialização). Email de reset para {email_to} não enviado.")
        print(f"Token de reset (para desenvolvimento/teste manual): {token}")
        return

    reset_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    
    template_body: Dict[str, Any] = {
        "username": username or email_to,
        "reset_url": reset_url,
        "expiration_hours": PASSWORD_RESET_TOKEN_EXPIRE_HOURS_EMAIL
    }

    message = MessageSchema(
        subject="TDAI - Redefinição de Senha Solicitada",
        recipients=[email_to],
        template_body=template_body,
        subtype=MessageType.html
    )

    try:
        # O template_folder já foi definido na ConnectionConfig
        await fm.send_message(message, template_name="password_reset_email.html") #
        print(f"INFO: Email de reset de senha enviado para: {email_to} (URL: {reset_url})")
    except Exception as e:
        print(f"ERRO ao enviar email de reset de senha para {email_to}: {e}")