"""Detailed coverage for password recovery request service and route delegates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend import schemas
from Backend.routers import password_recovery as password_module


@pytest.mark.asyncio
async def test_password_recovery_request_service_handles_missing_user_and_email_failure():
    service = password_module.PasswordRecoveryRequestService(session="db")

    class MissingUserRepo:
        def get_user_by_email(self, *, email):
            _ = email
            return None

    service._user_repository = MissingUserRepo()
    response = await service.recover_password(email="user@test.com", request=object())
    assert "Se um usuario" in response.msg

    class UserRepo:
        def get_user_by_email(self, *, email):
            return SimpleNamespace(email=email, nome_completo=None)

        def set_user_password_reset_token(self, **kwargs):
            self.kwargs = kwargs

    class AuthWorkflowStub:
        def create_password_reset_token(self):
            return "token"

        def hash_password_reset_token(self, token):
            assert token == "token"
            return "hash"

    class EmailWorkflowStub:
        async def send_password_reset_email(self, **kwargs):
            _ = kwargs
            raise RuntimeError("smtp offline")

    service._user_repository = UserRepo()
    service._auth_workflow = AuthWorkflowStub()
    service._email_workflow = EmailWorkflowStub()

    with pytest.raises(HTTPException) as exc_info:
        await service.recover_password(email="user@test.com", request=object())
    assert exc_info.value.status_code == 500


def test_password_recovery_request_service_reset_error_paths():
    service = password_module.PasswordRecoveryRequestService(session=SimpleNamespace(commit=lambda: None))

    class AuthWorkflowStub:
        def hash_password_reset_token(self, token):
            return f"hash:{token}"

        def get_password_hash(self, raw_password):
            return f"hashed:{raw_password}"

    class UserRepoInvalid:
        def get_user_by_reset_token(self, *, token_hash):
            _ = token_hash
            return None

    service._auth_workflow = AuthWorkflowStub()
    service._user_repository = UserRepoInvalid()
    reset_data = schemas.PasswordResetSchema(token="abc", new_password="NovaSenha123!")

    with pytest.raises(HTTPException) as invalid_token:
        service.reset_password(reset_data=reset_data)
    assert invalid_token.value.status_code == 400

    class UserRepoExpired:
        def get_user_by_reset_token(self, *, token_hash):
            _ = token_hash
            return SimpleNamespace(
                id=1,
                reset_password_token_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )

    service._user_repository = UserRepoExpired()
    with pytest.raises(HTTPException) as expired_token:
        service.reset_password(reset_data=reset_data)
    assert expired_token.value.status_code == 400

    class UserRepoMissingDbUser:
        def get_user_by_reset_token(self, *, token_hash):
            _ = token_hash
            return SimpleNamespace(
                id=1,
                reset_password_token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            )

        def get_user(self, *, user_id):
            _ = user_id
            return None

    service._user_repository = UserRepoMissingDbUser()
    with pytest.raises(HTTPException) as missing_db_user:
        service.reset_password(reset_data=reset_data)
    assert missing_db_user.value.status_code == 500


@pytest.mark.asyncio
async def test_password_recovery_route_wrappers_delegate():
    called = []

    class FakeRequestService:
        async def recover_password(self, *, email, request):
            called.append(("recover", email, request))
            return schemas.Msg(msg="recover")

        def reset_password(self, *, reset_data):
            called.append(("reset", reset_data))
            return schemas.Msg(msg="reset")

    recover_response = await password_module.recover_password(
        email="user@test.com",
        request="request",
        request_service=FakeRequestService(),
    )
    reset_response = password_module.reset_password(
        reset_data=schemas.PasswordResetSchema(token="abc", new_password="NovaSenha123!"),
        request_service=FakeRequestService(),
    )

    assert recover_response.msg == "recover"
    assert reset_response.msg == "reset"
    assert called[0] == ("recover", "user@test.com", "request")
    assert called[1][0] == "reset"
