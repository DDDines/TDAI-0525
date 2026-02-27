from __future__ import annotations

import pytest

from Backend.core.config import settings
from Backend.core.deprecation import deprecated_legacy_service_proxy


def test_deprecation_proxy_warns_once_and_delegates(recwarn):
    class _Service:
        def ping(self):
            return "pong"

    proxy = deprecated_legacy_service_proxy(
        _Service(),
        qualified_name="Backend.services.demo.demo_legacy_service",
        removal_date="2026-04-30",
    )

    assert proxy.ping() == "pong"
    assert proxy.ping() == "pong"

    warnings = [w for w in recwarn if issubclass(w.category, DeprecationWarning)]
    assert len(warnings) == 1
    assert "demo_legacy_service" in str(warnings[0].message)


def test_deprecation_proxy_blocks_in_strict_oop(monkeypatch):
    class _Service:
        def ping(self):
            return "pong"

    original_mode = settings.APP_MODE
    try:
        settings.APP_MODE = "oop"
        monkeypatch.setenv("STRICT_OOP_NO_LEGACY", "1")

        proxy = deprecated_legacy_service_proxy(
            _Service(),
            qualified_name="Backend.services.demo.demo_legacy_service",
            removal_date="2026-04-30",
        )

        with pytest.raises(RuntimeError):
            _ = proxy.ping()
    finally:
        settings.APP_MODE = original_mode
