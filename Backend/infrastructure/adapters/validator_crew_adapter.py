from __future__ import annotations

from typing import Any


def _default_validator_module() -> Any:
    from Backend.services import validator_crew

    return validator_crew


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, module: Any | None = None) -> None:
        self._module = module or _default_validator_module()

    def run_validation_crew(self, raw_data: Any):
        return self._module.run_validation_crew(raw_data)
