"""Detailed runtime coverage for security helpers."""

from __future__ import annotations

from datetime import timedelta

from jose import JWTError

from Backend.core import security as security_module


def test_security_runtime_hash_and_token_generation(monkeypatch):
    runtime = security_module.SecurityRuntime()
    encoded_calls = []

    monkeypatch.setattr(
        security_module.pwd_context,
        "verify",
        lambda plain_password, hashed_password: (plain_password, hashed_password) == ("senha", "hash"),
    )
    monkeypatch.setattr(
        security_module.pwd_context,
        "hash",
        lambda password: f"hashed:{password}",
    )
    monkeypatch.setattr(
        security_module.jwt,
        "encode",
        lambda payload, secret, algorithm: encoded_calls.append((payload, secret, algorithm)) or "jwt-token",
    )

    assert runtime.verify_password(plain_password="senha", hashed_password="hash") is True
    assert runtime.get_password_hash(password="nova") == "hashed:nova"
    assert runtime.create_access_token(data={"sub": "user@test.com"}) == "jwt-token"
    assert runtime.create_refresh_token(data={"sub": "user@test.com"}) == "jwt-token"
    assert encoded_calls[0][1] == security_module.settings.SECRET_KEY
    assert encoded_calls[1][1] == security_module.settings.REFRESH_SECRET_KEY
    assert encoded_calls[1][0]["token_type"] == "refresh"

    encoded_calls.clear()
    runtime.create_access_token(data={"sub": "user@test.com"}, expires_delta=timedelta(minutes=5))
    runtime.create_refresh_token(data={"sub": "user@test.com"}, expires_delta=timedelta(days=2))
    assert len(encoded_calls) == 2


def test_security_runtime_decode_token_success_and_failures(monkeypatch):
    runtime = security_module.SecurityRuntime()

    monkeypatch.setattr(
        security_module.jwt,
        "decode",
        lambda token, secret_key, algorithms: {"sub": "user@test.com", "user_id": "7"},
    )
    payload = runtime.decode_token(token="token", secret_key="secret")
    assert payload.sub == "user@test.com"
    assert payload.user_id == 7

    monkeypatch.setattr(
        security_module.jwt,
        "decode",
        lambda token, secret_key, algorithms: {"sub": "user@test.com", "user_id": "abc"},
    )
    assert runtime.decode_token(token="token", secret_key="secret") is None

    monkeypatch.setattr(
        security_module.jwt,
        "decode",
        lambda token, secret_key, algorithms: {"sub": ["bad"], "user_id": "7"},
    )
    assert runtime.decode_token(token="token", secret_key="secret") is None

    def _raise_jwt_error(token, secret_key, algorithms):
        _ = token, secret_key, algorithms
        raise JWTError("invalid")

    monkeypatch.setattr(security_module.jwt, "decode", _raise_jwt_error)
    assert runtime.decode_token(token="token", secret_key="secret") is None
