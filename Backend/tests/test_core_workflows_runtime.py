"""Module test core workflows runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.core.app_mode import AppMode, AppModeWorkflow
from Backend.core.config import ConfigWorkflow
from Backend.core.email_utils import EmailWorkflow
from Backend.core.logging_config import LoggingWorkflow
from Backend.core.security import TokenPayload, SecurityWorkflow


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_app_mode_workflow_runtime_injection():
        """Execute test_app_mode_workflow_runtime_injection.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def get_app_mode(self):
                """Execute get_app_mode.

                This callable is documented to make behavior explicit for readers.
                """
                return AppMode.OOP
    
        workflow = AppModeWorkflow(runtime=FakeRuntime())
    
        assert workflow.get_app_mode() == AppMode.OOP

    def test_config_workflow_runtime_injection():
        """Execute test_config_workflow_runtime_injection.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def build_settings(self):
                """Execute build_settings.

                This callable is documented to make behavior explicit for readers.
                """
                return SimpleNamespace(APP_MODE="test")
    
        workflow = ConfigWorkflow(runtime=FakeRuntime())
        settings_obj = workflow.build_settings()
    
        assert settings_obj.APP_MODE == "test"

    def test_logging_workflow_runtime_injection():
        """Execute test_logging_workflow_runtime_injection.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def get_logger(self, **kwargs):
                """Execute get_logger.

                This callable is documented to make behavior explicit for readers.
                """
                return f"logger:{kwargs['name']}"
    
        workflow = LoggingWorkflow(runtime=FakeRuntime())
        assert workflow.get_logger("core.test") == "logger:core.test"

    def test_security_workflow_runtime_injection():
        """Execute test_security_workflow_runtime_injection.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def verify_password(self, **kwargs):
                """Execute verify_password.

                This callable is documented to make behavior explicit for readers.
                """
                return kwargs["plain_password"] == "ok"
    
            def get_password_hash(self, **kwargs):
                """Execute get_password_hash.

                This callable is documented to make behavior explicit for readers.
                """
                return f"hash:{kwargs['password']}"
    
            def create_access_token(self, **kwargs):
                """Execute create_access_token.

                This callable is documented to make behavior explicit for readers.
                """
                return f"access:{kwargs['data']['sub']}"
    
            def create_refresh_token(self, **kwargs):
                """Execute create_refresh_token.

                This callable is documented to make behavior explicit for readers.
                """
                return f"refresh:{kwargs['data']['sub']}"
    
            def decode_token(self, **kwargs):
                """Execute decode_token.

                This callable is documented to make behavior explicit for readers.
                """
                return TokenPayload(sub="decoded", user_id=7)
    
        workflow = SecurityWorkflow(runtime=FakeRuntime())
    
        assert workflow.verify_password("ok", "ignored") is True
        assert workflow.get_password_hash("senha") == "hash:senha"
        assert workflow.create_access_token({"sub": "u1"}) == "access:u1"
        assert workflow.create_refresh_token({"sub": "u1"}) == "refresh:u1"
        assert workflow.decode_token("token", "secret").user_id == 7

    @pytest.mark.asyncio
    async def test_email_workflow_runtime_injection_sem_config():
        """Execute test_email_workflow_runtime_injection_sem_config.

        This callable is documented to make behavior explicit for readers.
        """
        class FakeRuntime:
            """Class FakeRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            def build_connection_config(self):
                """Execute build_connection_config.

                This callable is documented to make behavior explicit for readers.
                """
                return None
    
            def get_raise_on_missing_email_config(self):
                """Execute get_raise_on_missing_email_config.

                This callable is documented to make behavior explicit for readers.
                """
                return False
    
            def create_fastmail(self, conf):
                """Execute create_fastmail.

                This callable is documented to make behavior explicit for readers.
                """
                raise AssertionError("Nao deveria tentar enviar sem configuracao de email")
    
            def create_message_schema(self, **kwargs):
                """Execute create_message_schema.

                This callable is documented to make behavior explicit for readers.
                """
                return kwargs
    
            def current_year(self):
                """Execute current_year.

                This callable is documented to make behavior explicit for readers.
                """
                return 2030
    
        workflow = EmailWorkflow(runtime=FakeRuntime())
    
        await workflow.send_email(
            email_to="teste@example.com",
            subject="Teste",
            html_content="<b>ok</b>",
        )
    
        assert workflow.conf is None

test_app_mode_workflow_runtime_injection = _TopLevelFunctionSurface.test_app_mode_workflow_runtime_injection
test_config_workflow_runtime_injection = _TopLevelFunctionSurface.test_config_workflow_runtime_injection
test_logging_workflow_runtime_injection = _TopLevelFunctionSurface.test_logging_workflow_runtime_injection
test_security_workflow_runtime_injection = _TopLevelFunctionSurface.test_security_workflow_runtime_injection
test_email_workflow_runtime_injection_sem_config = _TopLevelFunctionSurface.test_email_workflow_runtime_injection_sem_config








