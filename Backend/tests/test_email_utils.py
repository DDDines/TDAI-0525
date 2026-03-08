"""Focused tests for email workflow and runtime helpers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.core import email_utils
from Backend.core.email_utils import EmailRuntime, EmailWorkflow


class _FakeMailClient:
    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls: list[dict[str, object]] = []

    async def send_message(self, message, template_name=None, template_body=None):
        self.calls.append(
            {
                "message": message,
                "template_name": template_name,
                "template_body": template_body,
            }
        )
        if self.error:
            raise self.error


class _FakeRuntime:
    def __init__(self, *, conf="conf", raise_on_missing=False, mail_client=None):
        self._conf = conf
        self._raise_on_missing = raise_on_missing
        self._mail_client = mail_client or _FakeMailClient()
        self.created_messages: list[dict[str, object]] = []

    def build_connection_config(self):
        return self._conf

    def get_raise_on_missing_email_config(self):
        return self._raise_on_missing

    def create_fastmail(self, conf):
        assert conf == self._conf
        return self._mail_client

    def create_message_schema(self, **kwargs):
        self.created_messages.append(kwargs)
        return kwargs

    def current_year(self):
        return 2035


@pytest.mark.asyncio
async def test_email_workflow_send_email_template_html_and_empty_paths():
    runtime = _FakeRuntime()
    workflow = EmailWorkflow(runtime=runtime)

    assert workflow.conf == "conf"
    assert workflow._build_connection_config() == "conf"

    await workflow.send_email(
        email_to="dest@example.com",
        subject="Template",
        html_content="",
        template_name="email.html",
        template_body={"nome": "Julio"},
    )
    await workflow.send_email(
        email_to="dest@example.com",
        subject="HTML",
        html_content="<b>ok</b>",
    )
    await workflow.send_email(
        email_to="dest@example.com",
        subject="Vazio",
        html_content="",
    )

    assert len(runtime._mail_client.calls) == 2
    assert runtime._mail_client.calls[0]["template_name"] == "email.html"
    assert runtime._mail_client.calls[0]["template_body"] == {"nome": "Julio"}
    assert runtime._mail_client.calls[1]["template_name"] is None
    assert runtime.created_messages[1]["subtype"] == email_utils.MessageType.html


@pytest.mark.asyncio
async def test_email_workflow_send_email_handles_missing_config_and_send_errors():
    missing_runtime = _FakeRuntime(conf=None, raise_on_missing=False)
    workflow = EmailWorkflow(runtime=missing_runtime)
    await workflow.send_email(
        email_to="dest@example.com",
        subject="Sem Config",
        html_content="<b>ok</b>",
    )

    with pytest.raises(RuntimeError, match="Configuracao de email ausente"):
        await EmailWorkflow(runtime=_FakeRuntime(conf=None, raise_on_missing=True)).send_email(
            email_to="dest@example.com",
            subject="Sem Config",
            html_content="<b>ok</b>",
        )

    with pytest.raises(RuntimeError, match="Falha ao enviar email"):
        await EmailWorkflow(
            runtime=_FakeRuntime(
                conf="conf",
                raise_on_missing=True,
                mail_client=_FakeMailClient(error=RuntimeError("smtp indisponivel")),
            )
        ).send_email(
            email_to="dest@example.com",
            subject="Erro",
            html_content="<b>ok</b>",
        )

    await EmailWorkflow(runtime=_FakeRuntime(conf="conf")).send_email(
        email_to="dest@example.com",
        subject="Sem raise automatico",
        html_content="",
        raise_if_unconfigured=False,
    )

    await EmailWorkflow(
        runtime=_FakeRuntime(
            conf="conf",
            raise_on_missing=False,
            mail_client=_FakeMailClient(error=RuntimeError("smtp instavel")),
        )
    ).send_email(
        email_to="dest@example.com",
        subject="Erro tolerado",
        html_content="<b>ok</b>",
        raise_if_unconfigured=False,
    )


@pytest.mark.asyncio
async def test_email_workflow_password_reset_success_and_failure_paths():
    runtime = _FakeRuntime()
    workflow = EmailWorkflow(runtime=runtime)
    await workflow.send_password_reset_email(
        email_to="dest@example.com",
        username="Julio",
        reset_link="https://catalog/reset",
    )
    assert runtime._mail_client.calls[0]["template_name"] == "password_reset_email.html"
    assert runtime._mail_client.calls[0]["template_body"]["current_year"] == 2035

    with pytest.raises(RuntimeError, match="Configuracao de email ausente"):
        await EmailWorkflow(runtime=_FakeRuntime(conf=None, raise_on_missing=True)).send_password_reset_email(
            email_to="dest@example.com",
            username="Julio",
            reset_link="https://catalog/reset",
        )

    await EmailWorkflow(runtime=_FakeRuntime(conf=None, raise_on_missing=False)).send_password_reset_email(
        email_to="dest@example.com",
        username="Julio",
        reset_link="https://catalog/reset",
    )

    with pytest.raises(RuntimeError, match="Falha ao enviar email de reset de senha"):
        await EmailWorkflow(
            runtime=_FakeRuntime(conf="conf", mail_client=_FakeMailClient(error=RuntimeError("smtp down")))
        ).send_password_reset_email(
            email_to="dest@example.com",
            username="Julio",
            reset_link="https://catalog/reset",
        )

    await EmailWorkflow(runtime=_FakeRuntime(conf=None, raise_on_missing=True)).send_password_reset_email(
        email_to="dest@example.com",
        username="Julio",
        reset_link="https://catalog/reset",
        raise_if_unconfigured=False,
    )


def test_email_runtime_builds_config_and_exposes_helpers(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "MAIL_USERNAME", "user", raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_PASSWORD", "pass", raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_FROM", "from@example.com", raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_SERVER", "smtp.example.com", raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_PORT", 587, raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_FROM_NAME", "Catalog", raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_STARTTLS", True, raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_SSL_TLS", False, raising=False)
    monkeypatch.setattr(email_utils.settings, "USE_CREDENTIALS", True, raising=False)
    monkeypatch.setattr(email_utils.settings, "VALIDATE_CERTS", True, raising=False)
    monkeypatch.setattr(email_utils.settings, "RAISE_ON_MISSING_EMAIL_CONFIG", True, raising=False)

    runtime = EmailRuntime()
    conf = runtime.build_connection_config()
    assert conf is not None
    assert runtime.get_raise_on_missing_email_config() is True

    created_message = runtime.create_message_schema(
        subject="Assunto",
        recipients=["dest@example.com"],
        body="Corpo",
        subtype=email_utils.MessageType.html,
    )
    assert created_message.subject == "Assunto"
    assert created_message.body == "Corpo"
    assert runtime.current_year() >= 2026

    class _FastMailStub:
        def __init__(self, conf_obj):
            self.conf_obj = conf_obj

    monkeypatch.setattr(email_utils, "FastMail", _FastMailStub)
    client = runtime.create_fastmail(conf)
    assert client.conf_obj == conf


def test_email_runtime_returns_none_when_config_incomplete(monkeypatch):
    monkeypatch.setattr(email_utils.settings, "MAIL_USERNAME", None, raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_PASSWORD", None, raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_FROM", None, raising=False)
    monkeypatch.setattr(email_utils.settings, "MAIL_SERVER", None, raising=False)

    assert EmailRuntime().build_connection_config() is None
