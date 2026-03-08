"""Targeted coverage for auth bootstrap, workflow wrappers and HTTP delegates."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys

import pytest
from fastapi import HTTPException

from Backend import auth as auth_module
from Backend import schemas


class _FakeLogger:
    def __init__(self) -> None:
        self.warning_calls = []
        self.error_calls = []
        self.info_calls = []
        self.exception_calls = []

    def warning(self, *args, **kwargs):
        self.warning_calls.append((args, kwargs))

    def error(self, *args, **kwargs):
        self.error_calls.append((args, kwargs))

    def info(self, *args, **kwargs):
        self.info_calls.append((args, kwargs))

    def exception(self, *args, **kwargs):
        self.exception_calls.append((args, kwargs))


def _load_auth_probe_module(monkeypatch, *, settings):
    import authlib.integrations.starlette_client as starlette_client
    import Backend.core.config as config_module
    import Backend.core.logging_config as logging_config

    logger = _FakeLogger()
    oauth_instances = []

    class FakeOAuth:
        def __init__(self, config=None):
            self.config = config
            self._clients = {}
            self.register_calls = []
            oauth_instances.append(self)

        def register(self, **kwargs):
            self.register_calls.append(kwargs)

    monkeypatch.setattr(config_module, "settings", settings)
    monkeypatch.setattr(logging_config, "get_logger", lambda _name: logger)
    monkeypatch.setattr(starlette_client, "OAuth", FakeOAuth)

    module_name = "Backend.tests._auth_probe_runtime"
    sys.modules.pop(module_name, None)
    spec = importlib.util.spec_from_file_location(module_name, Path("Backend/auth.py"))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module, logger, oauth_instances


def test_auth_bootstrap_registers_oauth_clients_from_settings(monkeypatch):
    settings = SimpleNamespace(
        GOOGLE_CLIENT_ID="google-id",
        GOOGLE_CLIENT_SECRET="google-secret",
        FACEBOOK_CLIENT_ID="facebook-id",
        FACEBOOK_CLIENT_SECRET="facebook-secret",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        SECRET_KEY="secret",
        REFRESH_SECRET_KEY="refresh",
        ALGORITHM="HS256",
    )

    module, logger, oauth_instances = _load_auth_probe_module(monkeypatch, settings=settings)

    assert module.auth_config_dict_env == {
        "GOOGLE_CLIENT_ID": "google-id",
        "GOOGLE_CLIENT_SECRET": "google-secret",
        "FACEBOOK_CLIENT_ID": "facebook-id",
        "FACEBOOK_CLIENT_SECRET": "facebook-secret",
    }
    assert {call["name"] for call in oauth_instances[0].register_calls} == {"google", "facebook"}
    assert logger.warning_calls == []


def test_auth_bootstrap_logs_warnings_when_oauth_credentials_are_missing(monkeypatch):
    settings = SimpleNamespace(
        GOOGLE_CLIENT_ID=None,
        GOOGLE_CLIENT_SECRET=None,
        FACEBOOK_CLIENT_ID="",
        FACEBOOK_CLIENT_SECRET="",
        ACCESS_TOKEN_EXPIRE_MINUTES=15,
        REFRESH_TOKEN_EXPIRE_DAYS=7,
        SECRET_KEY="secret",
        REFRESH_SECRET_KEY="refresh",
        ALGORITHM="HS256",
    )

    module, logger, oauth_instances = _load_auth_probe_module(monkeypatch, settings=settings)

    assert module.auth_config_dict_env == {}
    assert oauth_instances[0].register_calls == []
    assert len(logger.warning_calls) == 2


def test_auth_runtime_password_and_token_helpers_cover_direct_branches(monkeypatch):
    runtime = auth_module.AuthRuntime()
    encoded_calls = []

    monkeypatch.setattr(
        auth_module.pwd_context,
        "verify",
        lambda plain_password, hashed_password: (plain_password, hashed_password) == ("senha", "hash"),
    )
    monkeypatch.setattr(auth_module.pwd_context, "hash", lambda password: f"hashed:{password}")
    monkeypatch.setattr(auth_module.secrets, "token_urlsafe", lambda _size: "reset-token")
    monkeypatch.setattr(
        auth_module.jwt,
        "encode",
        lambda payload, secret, algorithm: encoded_calls.append((payload, secret, algorithm)) or "jwt-token",
    )

    assert runtime.verify_password("senha", "hash") is True
    assert runtime.get_password_hash("nova") == "hashed:nova"
    assert runtime.create_password_reset_token() == "reset-token"
    assert runtime.hash_password_reset_token("abc") == runtime.hash_password_reset_token("abc")
    assert runtime.verify_password_reset_token("abc", runtime.hash_password_reset_token("abc")) is True

    access = runtime.create_access_token({"sub": "user@test.com"}, expires_delta=timedelta(minutes=5))
    refresh = runtime.create_refresh_token({"sub": "user@test.com"}, expires_delta=timedelta(days=2))

    assert access == "jwt-token"
    assert refresh == "jwt-token"
    assert encoded_calls[0][1] == auth_module.settings.SECRET_KEY
    assert encoded_calls[1][1] == auth_module.settings.REFRESH_SECRET_KEY
    assert encoded_calls[0][0]["sub"] == "user@test.com"
    assert encoded_calls[1][0]["sub"] == "user@test.com"
    assert "exp" in encoded_calls[0][0]
    assert "iat" in encoded_calls[1][0]


@pytest.mark.asyncio
async def test_auth_runtime_refresh_access_token_rejects_incomplete_payload(monkeypatch):
    repo = SimpleNamespace(get_user=lambda **_kwargs: None)
    runtime = auth_module.AuthRuntime(user_repository=repo)

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: {"sub": "user@test.com", "user_id": None},
    )

    with pytest.raises(HTTPException) as exc_info:
        await runtime.refresh_access_token(
            refresh_token_data=SimpleNamespace(refresh_token="refresh-token")
        )

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_auth_runtime_get_or_create_social_user_without_updates_or_default_plan():
    session = SimpleNamespace(add=lambda *_a, **_k: None, commit=lambda: None, refresh=lambda *_a, **_k: None)
    existing_user = SimpleNamespace(
        id=4,
        email="social@test.com",
        is_active=True,
        nome_completo="Nome Completo",
        provider="Google",
        provider_user_id="google-1",
    )
    created_calls = []

    class FakeUserRepo:
        def get_user_by_email(self, *, email):
            return existing_user if email == existing_user.email else None

        def get_plano_by_name(self, *, nome):
            assert nome == "Gratuito"
            return None

        def create_user_oauth(self, *, user_oauth, plano_id_default=None):
            created_calls.append((user_oauth, plano_id_default))
            return SimpleNamespace(id=9, email=user_oauth.email)

    runtime = auth_module.AuthRuntime(session=session, user_repository=FakeUserRepo())

    same_user = await runtime._get_or_create_social_user(
        email="social@test.com",
        nome="Nome Completo",
        provider="Google",
        provider_user_id="google-1",
    )
    created_user = await runtime._get_or_create_social_user(
        email="novo@test.com",
        nome=None,
        provider="Facebook",
        provider_user_id="facebook-1",
    )

    assert same_user is existing_user
    assert created_user.email == "novo@test.com"
    assert created_calls[0][1] is None
    assert created_calls[0][0].nome_completo == "novo"


@pytest.mark.asyncio
async def test_auth_workflow_and_request_scope_delegate_to_runtime_and_workflow(monkeypatch):
    called = []

    class FakeRuntime:
        def verify_password(self, **kwargs):
            called.append(("verify_password", kwargs))
            return True

        def get_password_hash(self, **kwargs):
            called.append(("get_password_hash", kwargs))
            return "hash"

        def create_access_token(self, **kwargs):
            called.append(("create_access_token", kwargs))
            return "access"

        def create_refresh_token(self, **kwargs):
            called.append(("create_refresh_token", kwargs))
            return "refresh"

        def create_password_reset_token(self):
            called.append(("create_password_reset_token", {}))
            return "reset"

        def hash_password_reset_token(self, **kwargs):
            called.append(("hash_password_reset_token", kwargs))
            return "token-hash"

        def verify_password_reset_token(self, **kwargs):
            called.append(("verify_password_reset_token", kwargs))
            return True

        def authenticate_user(self, **kwargs):
            called.append(("authenticate_user", kwargs))
            return "user"

        async def get_current_user(self, **kwargs):
            called.append(("get_current_user", kwargs))
            return "current-user"

        async def login_for_access_token(self, **kwargs):
            called.append(("login_for_access_token", kwargs))
            return {"access_token": "a"}

        async def refresh_access_token(self, **kwargs):
            called.append(("refresh_access_token", kwargs))
            return {"access_token": "b"}

        async def update_users_me(self, **kwargs):
            called.append(("update_users_me", kwargs))
            return "updated"

        async def change_password_me(self, **kwargs):
            called.append(("change_password_me", kwargs))
            return {"message": "ok"}

        async def process_google_login(self, **kwargs):
            called.append(("process_google_login", kwargs))
            return "google-user"

        async def process_facebook_login(self, **kwargs):
            called.append(("process_facebook_login", kwargs))
            return "facebook-user"

    workflow = auth_module.AuthWorkflow(runtime=FakeRuntime())

    assert workflow.verify_password("senha", "hash") is True
    assert workflow.get_password_hash("nova") == "hash"
    assert workflow.create_access_token({"sub": "x"}) == "access"
    assert workflow.create_refresh_token({"sub": "x"}) == "refresh"
    assert workflow.create_password_reset_token() == "reset"
    assert workflow.hash_password_reset_token("abc") == "token-hash"
    assert workflow.verify_password_reset_token("abc", "hash") is True
    assert workflow.authenticate_user("u@test.com", "senha") == "user"
    assert await workflow.get_current_user("jwt") == "current-user"
    assert await workflow.login_for_access_token(form_data="form") == {"access_token": "a"}
    assert await workflow.refresh_access_token(refresh_token_data="refresh") == {"access_token": "b"}
    assert await workflow.update_users_me(user_update="update", current_user="user") == "updated"
    assert await workflow.change_password_me(payload="payload", current_user="user") == {"message": "ok"}
    assert await workflow.process_google_login({"email": "g@test.com"}) == "google-user"
    assert await workflow.process_facebook_login({"email": "f@test.com"}) == "facebook-user"

    scope_called = []

    class FakeWorkflow:
        def __init__(self, *, session):
            scope_called.append(("init", session))

        async def get_current_user(self, **kwargs):
            scope_called.append(("get_current_user", kwargs))
            return "scope-user"

        async def login_for_access_token(self, **kwargs):
            scope_called.append(("login_for_access_token", kwargs))
            return {"ok": 1}

        async def refresh_access_token(self, **kwargs):
            scope_called.append(("refresh_access_token", kwargs))
            return {"ok": 2}

        async def update_users_me(self, **kwargs):
            scope_called.append(("update_users_me", kwargs))
            return "scope-update"

        async def change_password_me(self, **kwargs):
            scope_called.append(("change_password_me", kwargs))
            return {"message": "changed"}

    monkeypatch.setattr(auth_module, "AuthWorkflow", FakeWorkflow)
    request_scope = auth_module._AuthRequestScope(session="db")

    assert await request_scope.get_current_user(token="jwt") == "scope-user"
    assert await request_scope.login_for_access_token(form_data="form") == {"ok": 1}
    assert await request_scope.refresh_access_token(refresh_token_data="refresh") == {"ok": 2}
    assert await request_scope.update_users_me(user_update="update", current_user="user") == "scope-update"
    assert await request_scope.change_password_me(payload="payload", current_user="user") == {"message": "changed"}
    assert scope_called[0] == ("init", "db")


@pytest.mark.asyncio
async def test_auth_dependencies_and_endpoint_handlers_delegate(monkeypatch):
    current_user = SimpleNamespace(id=7, is_active=True)
    dependency_calls = []

    class FakeRequestScope:
        async def get_current_user(self, **kwargs):
            dependency_calls.append(("get_current_user", kwargs))
            return current_user

        async def login_for_access_token(self, **kwargs):
            dependency_calls.append(("login_for_access_token", kwargs))
            return {"access_token": "a", "refresh_token": "b", "token_type": "bearer"}

        async def refresh_access_token(self, **kwargs):
            dependency_calls.append(("refresh_access_token", kwargs))
            return {"access_token": "c", "refresh_token": "d", "token_type": "bearer"}

        async def update_users_me(self, **kwargs):
            dependency_calls.append(("update_users_me", kwargs))
            return {"updated": True}

        async def change_password_me(self, **kwargs):
            dependency_calls.append(("change_password_me", kwargs))
            return {"message": "changed"}

    monkeypatch.setattr(auth_module.AuthWorkflow, "get_current_active_user", staticmethod(lambda current_user: ("active", current_user)))

    scope = FakeRequestScope()
    assert await auth_module._AuthDependencies.get_current_user(token="jwt", request_scope=scope) is current_user
    assert await auth_module._AuthActiveUserDependency.get_current_active_user(current_user=current_user) == ("active", current_user)

    form_data = SimpleNamespace(username="user@test.com", password="senha")
    refresh_data = schemas.RefreshTokenRequest(refresh_token="refresh")
    user_update = schemas.UserUpdate(nome_completo="Atualizado")
    password_payload = schemas.UserChangePassword(current_password="Atual1!", new_password="NovaSenha123!")

    assert await auth_module._EndpointHandlers.login_for_access_token(form_data=form_data, request_scope=scope) == {
        "access_token": "a",
        "refresh_token": "b",
        "token_type": "bearer",
    }
    assert await auth_module._EndpointHandlers.refresh_access_token(refresh_token_data=refresh_data, request_scope=scope) == {
        "access_token": "c",
        "refresh_token": "d",
        "token_type": "bearer",
    }
    assert await auth_module._EndpointHandlers.read_users_me(current_user=current_user) is current_user
    assert await auth_module._EndpointHandlers.update_users_me(
        user_update=user_update,
        current_user=current_user,
        request_scope=scope,
    ) == {"updated": True}
    assert await auth_module._EndpointHandlers.change_password_me(
        payload=password_payload,
        current_user=current_user,
        request_scope=scope,
    ) == {"message": "changed"}
