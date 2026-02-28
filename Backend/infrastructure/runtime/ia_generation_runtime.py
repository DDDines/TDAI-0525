from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.infrastructure.runtime_modules import ia_generation_module

    return ia_generation_module
