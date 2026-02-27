from __future__ import annotations

import os

_TRUTHY_VALUES = {"1", "true", "yes", "on"}


def is_strict_oop_no_legacy_enabled() -> bool:
    raw = str(os.getenv("STRICT_OOP_NO_LEGACY", "") or "").strip().lower()
    if raw not in _TRUTHY_VALUES:
        return False
    from Backend.core.config import settings

    app_mode = str(getattr(settings, "APP_MODE", "legacy") or "").strip().lower()
    return app_mode == "oop"


def assert_legacy_usage_allowed(source: str) -> None:
    if is_strict_oop_no_legacy_enabled():
        raise RuntimeError(
            f"Legacy access blocked in APP_MODE=oop (STRICT_OOP_NO_LEGACY=1): {source}"
        )
