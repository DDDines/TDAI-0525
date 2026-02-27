from __future__ import annotations

import pytest

from Backend.core.config import settings
from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.infrastructure.legacy.validator_crew_bridge import (
    LegacyValidatorCrewBridge,
)


@pytest.fixture
def _restore_app_mode():
    original_mode = settings.APP_MODE
    try:
        yield
    finally:
        settings.APP_MODE = original_mode


def test_legacy_guard_allows_when_not_oop(monkeypatch, _restore_app_mode):
    settings.APP_MODE = "legacy"
    monkeypatch.setenv("STRICT_OOP_NO_LEGACY", "1")

    assert_legacy_usage_allowed("x")


def test_legacy_guard_allows_when_not_strict(monkeypatch, _restore_app_mode):
    settings.APP_MODE = "oop"
    monkeypatch.delenv("STRICT_OOP_NO_LEGACY", raising=False)

    assert_legacy_usage_allowed("x")


def test_legacy_guard_blocks_when_oop_and_strict(monkeypatch, _restore_app_mode):
    settings.APP_MODE = "oop"
    monkeypatch.setenv("STRICT_OOP_NO_LEGACY", "1")

    with pytest.raises(RuntimeError):
        assert_legacy_usage_allowed("x")


def test_validator_bridge_obeys_legacy_guard(monkeypatch, _restore_app_mode):
    class _Module:
        @staticmethod
        def run_validation_crew(raw_data):
            return {"ok": raw_data}

    bridge = LegacyValidatorCrewBridge(module=_Module())
    settings.APP_MODE = "oop"
    monkeypatch.setenv("STRICT_OOP_NO_LEGACY", "1")

    with pytest.raises(RuntimeError):
        bridge.run_validation_crew({"a": 1})
