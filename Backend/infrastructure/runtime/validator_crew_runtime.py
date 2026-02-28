from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.infrastructure.runtime_modules import validator_crew_module

    return validator_crew_module
