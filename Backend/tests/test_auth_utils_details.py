"""Detailed coverage for auth utils guards and dependency delegates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.routers import auth_utils as auth_utils_module


@pytest.mark.asyncio
async def test_auth_utils_guard_methods_cover_success_and_error_paths():
    active_user = SimpleNamespace(is_active=True, is_superuser=True)
    assert (
        await auth_utils_module.AuthRequestService.get_current_active_user(current_user=active_user)
        is active_user
    )
    assert (
        await auth_utils_module.AuthRequestService.get_current_active_superuser(current_user=active_user)
        is active_user
    )

    with pytest.raises(HTTPException) as inactive_error:
        await auth_utils_module.AuthRequestService.get_current_active_user(
            current_user=SimpleNamespace(is_active=False, is_superuser=True)
        )
    assert inactive_error.value.status_code == 400

    with pytest.raises(HTTPException) as forbidden_error:
        await auth_utils_module.AuthRequestService.get_current_active_superuser(
            current_user=SimpleNamespace(is_active=True, is_superuser=False)
        )
    assert forbidden_error.value.status_code == 403


@pytest.mark.asyncio
async def test_auth_utils_dependency_builders_and_delegates(monkeypatch):
    class FakeSecurityWorkflow:
        pass

    class FakeUserRepository:
        def __init__(self, session):
            self.session = session

    monkeypatch.setattr(auth_utils_module.security, "SecurityWorkflow", FakeSecurityWorkflow)
    monkeypatch.setattr(auth_utils_module, "UserRepository", FakeUserRepository)

    service = auth_utils_module._AuthUtilsCurrentUserDependency.build_auth_request_service()
    assert isinstance(service._security_workflow, FakeSecurityWorkflow)
    assert isinstance(service._user_repository_factory("db"), FakeUserRepository)

    async def _fake_get_current_user(*, request, session, token):
        assert request is None
        assert session == "db"
        assert token == "jwt"
        return "user"

    monkeypatch.setattr(
        auth_utils_module._AuthUtilsCurrentUserDependency,
        "build_auth_request_service",
        staticmethod(lambda: SimpleNamespace(get_current_user=_fake_get_current_user)),
    )
    current_user = await auth_utils_module._AuthUtilsCurrentUserDependency.get_current_user(
        session="db",
        token="jwt",
    )
    assert current_user == "user"

    async def _fake_active(*, current_user):
        return ("active", current_user)

    async def _fake_super(*, current_user):
        return ("super", current_user)

    monkeypatch.setattr(auth_utils_module.AuthRequestService, "get_current_active_user", staticmethod(_fake_active))
    monkeypatch.setattr(auth_utils_module.AuthRequestService, "get_current_active_superuser", staticmethod(_fake_super))

    assert await auth_utils_module._AuthUtilsActiveUserDependency.get_current_active_user(
        current_user="user"
    ) == ("active", "user")
    assert await auth_utils_module._AuthUtilsSuperUserDependency.get_current_active_superuser(
        current_user="user"
    ) == ("super", "user")


@pytest.mark.asyncio
async def test_auth_utils_get_current_user_raises_when_user_missing():
    class FakeSecurityWorkflow:
        def decode_token(self, token, secret_key):
            _ = token, secret_key
            return SimpleNamespace(user_id=7)

    class FakeUserRepository:
        def get_user(self, *, user_id):
            _ = user_id
            return None

    service = auth_utils_module.AuthRequestService(
        security_workflow=FakeSecurityWorkflow(),
        user_repository_factory=lambda session: FakeUserRepository(),
    )

    with pytest.raises(HTTPException) as exc_info:
        await service.get_current_user(request=None, session="db", token="jwt")
    assert exc_info.value.status_code == 401
