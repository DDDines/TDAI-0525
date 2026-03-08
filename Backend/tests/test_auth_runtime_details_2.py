from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from jose import JWTError

from Backend import auth as auth_module


@pytest.mark.asyncio
async def test_auth_runtime_covers_user_mismatch_and_refresh_jwt_error(monkeypatch):
    repo = SimpleNamespace(
        get_user=lambda *, user_id: SimpleNamespace(id=user_id, email="other@test.com", is_active=True),
        get_user_by_email=lambda **kwargs: None,
    )
    runtime = auth_module.AuthRuntime(user_repository=repo)

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: {"sub": "expected@test.com", "user_id": 7},
    )
    with pytest.raises(HTTPException) as mismatch_error:
        await runtime.get_current_user(token="jwt")
    assert mismatch_error.value.status_code == 401

    monkeypatch.setattr(
        auth_module.jwt,
        "decode",
        lambda token, secret, algorithms: (_ for _ in ()).throw(JWTError("bad refresh")),
    )
    with pytest.raises(HTTPException) as refresh_error:
        await runtime.refresh_access_token(
            refresh_token_data=SimpleNamespace(refresh_token="refresh-token")
        )
    assert refresh_error.value.status_code == 401


def test_auth_workflow_static_active_user_wrapper_delegates():
    active_user = SimpleNamespace(is_active=True)
    assert auth_module.AuthWorkflow.get_current_active_user(active_user) is active_user
