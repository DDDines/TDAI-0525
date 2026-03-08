from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "smoke_release.py"
)


def _load_smoke_module():
    spec = importlib.util.spec_from_file_location("smoke_release", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_run_smoke_without_credentials_checks_public_endpoints(monkeypatch):
    smoke = _load_smoke_module()
    calls = []

    monkeypatch.setattr(
        smoke,
        "_check_health",
        lambda base_url, timeout: calls.append(("health", base_url, timeout)),
    )
    monkeypatch.setattr(
        smoke,
        "_check_root",
        lambda base_url, timeout: calls.append(("root", base_url, timeout)),
    )

    smoke.run_smoke(
        base_url="http://localhost:8000/",
        api_prefix="/api/v1",
        timeout=12.5,
        email=None,
        password=None,
    )

    assert calls == [
        ("health", "http://localhost:8000", 12.5),
        ("root", "http://localhost:8000", 12.5),
    ]


def test_run_smoke_with_credentials_checks_authenticated_endpoints(monkeypatch):
    smoke = _load_smoke_module()
    calls = []

    monkeypatch.setattr(
        smoke,
        "_check_health",
        lambda base_url, timeout: calls.append(("health", base_url, timeout)),
    )
    monkeypatch.setattr(
        smoke,
        "_check_root",
        lambda base_url, timeout: calls.append(("root", base_url, timeout)),
    )
    monkeypatch.setattr(
        smoke,
        "_fetch_access_token",
        lambda base_url, api_prefix, email, password, timeout: (
            calls.append(("token", base_url, api_prefix, email, password, timeout))
            or "abc123"
        ),
    )
    monkeypatch.setattr(
        smoke,
        "_check_authenticated_endpoints",
        lambda base_url, api_prefix, token, timeout: calls.append(
            ("authed", base_url, api_prefix, token, timeout)
        ),
    )

    smoke.run_smoke(
        base_url="http://localhost:8000/",
        api_prefix="api/v1/",
        timeout=10.0,
        email="admin@example.com",
        password="password",
    )

    assert calls == [
        ("health", "http://localhost:8000", 10.0),
        ("root", "http://localhost:8000", 10.0),
        (
            "token",
            "http://localhost:8000",
            "/api/v1",
            "admin@example.com",
            "password",
            10.0,
        ),
        ("authed", "http://localhost:8000", "/api/v1", "abc123", 10.0),
    ]


def test_fetch_access_token_requires_access_token(monkeypatch):
    smoke = _load_smoke_module()
    monkeypatch.setattr(smoke, "_read_json", lambda *args, **kwargs: {})

    with pytest.raises(smoke.SmokeFailure, match="access_token"):
        smoke._fetch_access_token(
            "http://localhost:8000",
            "/api/v1",
            email="admin@example.com",
            password="password",
            timeout=5.0,
        )


def test_authenticated_endpoint_validation_rejects_unexpected_payload(monkeypatch):
    smoke = _load_smoke_module()
    payloads = iter([[], {"not": "a list"}])

    monkeypatch.setattr(smoke, "_read_json", lambda *args, **kwargs: next(payloads))

    with pytest.raises(smoke.SmokeFailure, match="Produtos endpoint"):
        smoke._check_authenticated_endpoints(
            "http://localhost:8000",
            "/api/v1",
            token="token",
            timeout=5.0,
        )


def test_main_returns_one_on_smoke_failure(monkeypatch, capsys):
    smoke = _load_smoke_module()
    parser = smoke.build_parser()
    args = parser.parse_args(["--base-url", "http://localhost:8000"])

    monkeypatch.setattr(parser, "parse_args", lambda: args)
    monkeypatch.setattr(smoke, "build_parser", lambda: parser)
    monkeypatch.setattr(
        smoke,
        "run_smoke",
        lambda **kwargs: (_ for _ in ()).throw(smoke.SmokeFailure("boom")),
    )

    exit_code = smoke.main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Smoke check failed: boom" in captured.err
