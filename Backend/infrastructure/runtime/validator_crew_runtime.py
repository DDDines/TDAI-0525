from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.services import validator_crew

    return validator_crew
