from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.core.app_mode import AppMode, _AppModeWorkflow
from Backend.core.config import _ConfigWorkflow
from Backend.core.email_utils import _EmailWorkflow
from Backend.core.logging_config import _LoggingWorkflow
from Backend.core.security import TokenPayload, _SecurityWorkflow


def test_app_mode_workflow_runtime_injection():
    class FakeRuntime:
        def get_app_mode(self):
            return AppMode.OOP

        def normalize_for_compare(self, value):
            return {"normalized": value}

        def compare_shadow_payloads(self, **kwargs):
            return kwargs["context"] == "ok"

    workflow = _AppModeWorkflow(runtime=FakeRuntime())

    assert workflow.get_app_mode() == AppMode.OOP
    assert workflow.normalize_for_compare(value=1) == {"normalized": 1}
    assert workflow.compare_shadow_payloads("ok", {"a": 1}, {"a": 1}) is True


def test_config_workflow_runtime_injection():
    class FakeRuntime:
        def build_settings(self):
            return SimpleNamespace(APP_MODE="test")

    workflow = _ConfigWorkflow(runtime=FakeRuntime())
    settings_obj = workflow.build_settings()

    assert settings_obj.APP_MODE == "test"


def test_logging_workflow_runtime_injection():
    class FakeRuntime:
        def get_logger(self, **kwargs):
            return f"logger:{kwargs['name']}"

    workflow = _LoggingWorkflow(runtime=FakeRuntime())
    assert workflow.get_logger("core.test") == "logger:core.test"


def test_security_workflow_runtime_injection():
    class FakeRuntime:
        def verify_password(self, **kwargs):
            return kwargs["plain_password"] == "ok"

        def get_password_hash(self, **kwargs):
            return f"hash:{kwargs['password']}"

        def create_access_token(self, **kwargs):
            return f"access:{kwargs['data']['sub']}"

        def create_refresh_token(self, **kwargs):
            return f"refresh:{kwargs['data']['sub']}"

        def decode_token(self, **kwargs):
            return TokenPayload(sub="decoded", user_id=7)

    workflow = _SecurityWorkflow(runtime=FakeRuntime())

    assert workflow.verify_password("ok", "ignored") is True
    assert workflow.get_password_hash("senha") == "hash:senha"
    assert workflow.create_access_token({"sub": "u1"}) == "access:u1"
    assert workflow.create_refresh_token({"sub": "u1"}) == "refresh:u1"
    assert workflow.decode_token("token", "secret").user_id == 7


@pytest.mark.asyncio
async def test_email_workflow_runtime_injection_sem_config():
    class FakeRuntime:
        def build_connection_config(self):
            return None

        def get_raise_on_missing_email_config(self):
            return False

        def create_fastmail(self, conf):
            raise AssertionError("Nao deveria tentar enviar sem configuracao de email")

        def create_message_schema(self, **kwargs):
            return kwargs

        def current_year(self):
            return 2030

    workflow = _EmailWorkflow(runtime=FakeRuntime())

    await workflow.send_email(
        email_to="teste@example.com",
        subject="Teste",
        html_content="<b>ok</b>",
    )

    assert workflow.conf is None
