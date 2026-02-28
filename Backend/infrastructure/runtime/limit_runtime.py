from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.services import limit_service

    return limit_service
