# Backend/core/email_utils.py
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from .config import settings
from .logging_config import get_logger

TEMPLATE_FOLDER = Path(__file__).parent.parent / "templates"
logger = get_logger(__name__)


class _EmailWorkflow:
    def __init__(self, runtime: Optional["_EmailRuntime"] = None):
        self._runtime = runtime or _EmailRuntime()
        self._conf = self._runtime.build_connection_config()

    @property
    def conf(self):
        return self._conf

    def _build_connection_config(self) -> Optional[ConnectionConfig]:
        return self._runtime.build_connection_config()

    async def send_email(
        self,
        *,
        email_to: EmailStr,
        subject: str,
        html_content: str,
        template_body: Optional[Dict[str, Any]] = None,
        template_name: Optional[str] = None,
        raise_if_unconfigured: Optional[bool] = None,
    ) -> None:
        if raise_if_unconfigured is None:
            raise_if_unconfigured = self._runtime.get_raise_on_missing_email_config()

        if not self._conf:
            logger.warning(
                "Tentativa de enviar email para %s com assunto '%s', mas a configuracao de email esta desabilitada.",
                email_to,
                subject,
            )
            if raise_if_unconfigured:
                raise RuntimeError("Configuracao de email ausente")
            return

        message_data = {
            "subject": subject,
            "recipients": [email_to],
        }
        fm = self._runtime.create_fastmail(self._conf)

        try:
            if template_name:
                message = self._runtime.create_message_schema(**message_data)
                await fm.send_message(
                    message,
                    template_name=template_name,
                    template_body=template_body or {},
                )
                logger.info("Email com template '%s' enviado para %s.", template_name, email_to)
                return

            if html_content:
                message = self._runtime.create_message_schema(
                    **message_data,
                    body=html_content,
                    subtype=MessageType.html,
                )
                await fm.send_message(message)
                logger.info("Email HTML enviado para %s.", email_to)
                return

            logger.warning(
                "Tentativa de enviar email para %s sem template_name ou html_content.",
                email_to,
            )
        except Exception as exc:
            logger.error("Falha ao enviar email para %s. Erro: %s", email_to, exc)
            if raise_if_unconfigured:
                raise RuntimeError(f"Falha ao enviar email: {exc}")

    async def send_password_reset_email(
        self,
        *,
        email_to: EmailStr,
        username: str,
        reset_link: str,
        raise_if_unconfigured: Optional[bool] = None,
    ) -> None:
        if raise_if_unconfigured is None:
            raise_if_unconfigured = self._runtime.get_raise_on_missing_email_config()

        if not self._conf:
            logger.warning(
                "Tentativa de enviar email de reset de senha para %s, mas a configuracao de email esta desabilitada.",
                email_to,
            )
            if raise_if_unconfigured:
                raise RuntimeError("Configuracao de email ausente")
            return

        subject = "Redefinicao de Senha - CatalogAI"
        template_name = "password_reset_email.html"
        template_body = {
            "username": username,
            "reset_url": reset_link,
            "expiration_hours": settings.ACCESS_TOKEN_EXPIRE_MINUTES // 60,
            "current_year": self._runtime.current_year(),
        }

        message = self._runtime.create_message_schema(
            subject=subject,
            recipients=[email_to],
            subtype=MessageType.html,
        )

        fm = self._runtime.create_fastmail(self._conf)
        try:
            await fm.send_message(
                message,
                template_name=template_name,
                template_body=template_body,
            )
            logger.info("Email de reset de senha enviado para %s", email_to)
        except Exception as exc:
            logger.error("Falha ao enviar email de reset de senha para %s. Erro: %s", email_to, exc)
            raise RuntimeError(f"Falha ao enviar email de reset de senha: {exc}")


class _EmailRuntime:
    """Runtime OO para configuração e envio de email."""

    def build_connection_config(self) -> Optional[ConnectionConfig]:
        if (
            settings.MAIL_USERNAME
            and settings.MAIL_PASSWORD
            and settings.MAIL_FROM
            and settings.MAIL_SERVER
        ):
            return ConnectionConfig(
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
                TEMPLATE_FOLDER=TEMPLATE_FOLDER,
            )

        logger.warning(
            "Configuracoes de Email (MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_SERVER) incompletas no .env. Funcionalidade de envio de email desabilitada."
        )
        return None

    def get_raise_on_missing_email_config(self) -> bool:
        return settings.RAISE_ON_MISSING_EMAIL_CONFIG

    def create_fastmail(self, conf: ConnectionConfig) -> FastMail:
        return FastMail(conf)

    def create_message_schema(self, **kwargs) -> MessageSchema:
        return MessageSchema(**kwargs)

    def current_year(self) -> int:
        return datetime.now().year

EmailWorkflow = _EmailWorkflow


def get_email_workflow() -> EmailWorkflow:
    return EmailWorkflow()




