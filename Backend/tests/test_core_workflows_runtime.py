"""Module test core workflows runtime.

Contains backend logic related to test core workflows runtime and documents its role in the OOP architecture.
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

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_app_mode_workflow_runtime_injection():
        """Run test app mode workflow runtime injection in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def get_app_mode(self):
                """Return app mode for this workflow."""
                return AppMode.OOP
    
        workflow = AppModeWorkflow(runtime=FakeRuntime())
    
        assert workflow.get_app_mode() == AppMode.OOP

    def test_config_workflow_runtime_injection():
        """Run test config workflow runtime injection in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def build_settings(self):
                """Build settings for this workflow."""
                return SimpleNamespace(APP_MODE="test")
    
        workflow = ConfigWorkflow(runtime=FakeRuntime())
        settings_obj = workflow.build_settings()
    
        assert settings_obj.APP_MODE == "test"

    def test_logging_workflow_runtime_injection():
        """Run test logging workflow runtime injection in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def get_logger(self, **kwargs):
                """Return logger for this workflow."""
                return f"logger:{kwargs['name']}"
    
        workflow = LoggingWorkflow(runtime=FakeRuntime())
        assert workflow.get_logger("core.test") == "logger:core.test"

    def test_security_workflow_runtime_injection():
        """Run test security workflow runtime injection in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def verify_password(self, **kwargs):
                """Run verify password in this workflow."""
                return kwargs["plain_password"] == "ok"
    
            def get_password_hash(self, **kwargs):
                """Return password hash for this workflow."""
                return f"hash:{kwargs['password']}"
    
            def create_access_token(self, **kwargs):
                """Create access token for this workflow."""
                return f"access:{kwargs['data']['sub']}"
    
            def create_refresh_token(self, **kwargs):
                """Create refresh token for this workflow."""
                return f"refresh:{kwargs['data']['sub']}"
    
            def decode_token(self, **kwargs):
                """Run decode token in this workflow."""
                return TokenPayload(sub="decoded", user_id=7)
    
        workflow = SecurityWorkflow(runtime=FakeRuntime())
    
        assert workflow.verify_password("ok", "ignored") is True
        assert workflow.get_password_hash("senha") == "hash:senha"
        assert workflow.create_access_token({"sub": "u1"}) == "access:u1"
        assert workflow.create_refresh_token({"sub": "u1"}) == "refresh:u1"
        assert workflow.decode_token("token", "secret").user_id == 7

    @pytest.mark.asyncio
    async def test_email_workflow_runtime_injection_sem_config():
        """Run test email workflow runtime injection sem config in this workflow."""
        class FakeRuntime:
            """Represent fake runtime and centralize responsibilities for this module."""
            def build_connection_config(self):
                """Build connection config for this workflow."""
                return None
    
            def get_raise_on_missing_email_config(self):
                """Return raise on missing email config for this workflow."""
                return False
    
            def create_fastmail(self, conf):
                """Create fastmail for this workflow."""
                raise AssertionError("Nao deveria tentar enviar sem configuracao de email")
    
            def create_message_schema(self, **kwargs):
                """Create message schema for this workflow."""
                return kwargs
    
            def current_year(self):
                """Run current year in this workflow."""
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








