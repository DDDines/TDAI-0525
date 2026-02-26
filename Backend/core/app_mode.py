from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict

from Backend.core.config import settings
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


class AppMode(str, Enum):
    LEGACY = "legacy"
    OOP = "oop"
    SHADOW = "shadow"


def _normalize_for_compare_impl(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {
            str(key): _normalize_for_compare_impl(val)
            for key, val in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple, set)):
        return [_normalize_for_compare_impl(item) for item in value]
    if hasattr(value, "__name__"):
        return f"<callable:{getattr(value, '__name__', type(value).__name__)}>"
    return repr(value)


def _get_app_mode_impl() -> AppMode:
    raw_mode = str(getattr(settings, "APP_MODE", AppMode.LEGACY.value) or "").strip().lower()
    if raw_mode in {mode.value for mode in AppMode}:
        return AppMode(raw_mode)
    logger.warning("APP_MODE invalido '%s'. Usando modo legacy.", raw_mode)
    return AppMode.LEGACY


def _compare_shadow_payloads_impl(
    context: str,
    legacy_payload: Dict[str, Any],
    oop_payload: Dict[str, Any],
) -> bool:
    normalized_legacy = _normalize_for_compare_impl(legacy_payload)
    normalized_oop = _normalize_for_compare_impl(oop_payload)
    is_equal = normalized_legacy == normalized_oop
    if is_equal:
        logger.info("SHADOW compare OK (%s)", context)
        return True

    logger.warning(
        "SHADOW compare DIFF (%s)\nlegacy=%s\noop=%s",
        context,
        json.dumps(normalized_legacy, ensure_ascii=False, sort_keys=True),
        json.dumps(normalized_oop, ensure_ascii=False, sort_keys=True),
    )
    return False


class _AppModeWorkflow:
    def get_app_mode(self) -> AppMode:
        return _get_app_mode_impl()

    def is_legacy_mode(self) -> bool:
        return self.get_app_mode() == AppMode.LEGACY

    def is_oop_mode(self) -> bool:
        return self.get_app_mode() == AppMode.OOP

    def is_shadow_mode(self) -> bool:
        return self.get_app_mode() == AppMode.SHADOW

    def normalize_for_compare(self, value: Any) -> Any:
        return _normalize_for_compare_impl(value)

    def compare_shadow_payloads(
        self,
        context: str,
        legacy_payload: Dict[str, Any],
        oop_payload: Dict[str, Any],
    ) -> bool:
        return _compare_shadow_payloads_impl(
            context=context,
            legacy_payload=legacy_payload,
            oop_payload=oop_payload,
        )


_app_mode_workflow = _AppModeWorkflow()


def get_app_mode() -> AppMode:
    return _app_mode_workflow.get_app_mode()


def is_legacy_mode() -> bool:
    return _app_mode_workflow.is_legacy_mode()


def is_oop_mode() -> bool:
    return _app_mode_workflow.is_oop_mode()


def is_shadow_mode() -> bool:
    return _app_mode_workflow.is_shadow_mode()


def _normalize_for_compare(value: Any) -> Any:
    return _app_mode_workflow.normalize_for_compare(value=value)


def compare_shadow_payloads(
    context: str,
    legacy_payload: Dict[str, Any],
    oop_payload: Dict[str, Any],
) -> bool:
    return _app_mode_workflow.compare_shadow_payloads(
        context=context,
        legacy_payload=legacy_payload,
        oop_payload=oop_payload,
    )


class AppModeLegacyService:
    def get_app_mode(self, *args, **kwargs):
        return get_app_mode(*args, **kwargs)

    def is_legacy_mode(self, *args, **kwargs):
        return is_legacy_mode(*args, **kwargs)

    def is_oop_mode(self, *args, **kwargs):
        return is_oop_mode(*args, **kwargs)

    def is_shadow_mode(self, *args, **kwargs):
        return is_shadow_mode(*args, **kwargs)

    def normalize_for_compare(self, *args, **kwargs):
        return _normalize_for_compare(*args, **kwargs)

    def compare_shadow_payloads(self, *args, **kwargs):
        return compare_shadow_payloads(*args, **kwargs)


app_mode_legacy_service = AppModeLegacyService()
