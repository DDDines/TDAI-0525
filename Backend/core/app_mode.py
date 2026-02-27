from __future__ import annotations

import json
from enum import Enum
from typing import Any, Dict, Optional

from Backend.core.config import settings
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


class AppMode(str, Enum):
    LEGACY = "legacy"
    OOP = "oop"
    SHADOW = "shadow"

class _AppModeWorkflow:
    def __init__(self, runtime: Optional["_AppModeRuntime"] = None) -> None:
        self._runtime = runtime or _AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        return self._runtime.get_app_mode()

    def is_legacy_mode(self) -> bool:
        return self.get_app_mode() == AppMode.LEGACY

    def is_oop_mode(self) -> bool:
        return self.get_app_mode() == AppMode.OOP

    def is_shadow_mode(self) -> bool:
        return self.get_app_mode() == AppMode.SHADOW

    def normalize_for_compare(self, value: Any) -> Any:
        return self._runtime.normalize_for_compare(value=value)

    def compare_shadow_payloads(
        self,
        context: str,
        legacy_payload: Dict[str, Any],
        oop_payload: Dict[str, Any],
    ) -> bool:
        return self._runtime.compare_shadow_payloads(
            context=context,
            legacy_payload=legacy_payload,
            oop_payload=oop_payload,
        )


class _AppModeRuntime:
    """Runtime OO para resolução de modo de execução e comparação shadow."""

    def get_app_mode(self) -> AppMode:
        raw_mode = str(getattr(settings, "APP_MODE", AppMode.LEGACY.value) or "").strip().lower()
        if raw_mode in {mode.value for mode in AppMode}:
            return AppMode(raw_mode)
        logger.warning("APP_MODE invalido '%s'. Usando modo legacy.", raw_mode)
        return AppMode.LEGACY

    def normalize_for_compare(self, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {
                str(key): self.normalize_for_compare(val)
                for key, val in sorted(value.items(), key=lambda item: str(item[0]))
            }
        if isinstance(value, (list, tuple, set)):
            return [self.normalize_for_compare(item) for item in value]
        if hasattr(value, "__name__"):
            return f"<callable:{getattr(value, '__name__', type(value).__name__)}>"
        return repr(value)

    def compare_shadow_payloads(
        self,
        *,
        context: str,
        legacy_payload: Dict[str, Any],
        oop_payload: Dict[str, Any],
    ) -> bool:
        normalized_legacy = self.normalize_for_compare(legacy_payload)
        normalized_oop = self.normalize_for_compare(oop_payload)
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


app_mode_runtime = _AppModeRuntime()
_app_mode_workflow = _AppModeWorkflow(runtime=app_mode_runtime)


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
