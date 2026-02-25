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


def get_app_mode() -> AppMode:
    raw = str(getattr(settings, "APP_MODE", AppMode.LEGACY.value) or "").strip().lower()
    if raw in {mode.value for mode in AppMode}:
        return AppMode(raw)
    logger.warning("APP_MODE invalido '%s'. Usando modo legacy.", raw)
    return AppMode.LEGACY


def is_legacy_mode() -> bool:
    return get_app_mode() == AppMode.LEGACY


def is_oop_mode() -> bool:
    return get_app_mode() == AppMode.OOP


def is_shadow_mode() -> bool:
    return get_app_mode() == AppMode.SHADOW


def _normalize_for_compare(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _normalize_for_compare(v) for k, v in sorted(value.items(), key=lambda i: str(i[0]))}
    if isinstance(value, (list, tuple, set)):
        return [_normalize_for_compare(item) for item in value]
    if hasattr(value, "__name__"):
        return f"<callable:{getattr(value, '__name__', type(value).__name__)}>"
    return repr(value)


def compare_shadow_payloads(context: str, legacy_payload: Dict[str, Any], oop_payload: Dict[str, Any]) -> bool:
    normalized_legacy = _normalize_for_compare(legacy_payload)
    normalized_oop = _normalize_for_compare(oop_payload)
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
