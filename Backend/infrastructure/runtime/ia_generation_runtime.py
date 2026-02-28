from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.services import ia_generation_service

    return ia_generation_service
