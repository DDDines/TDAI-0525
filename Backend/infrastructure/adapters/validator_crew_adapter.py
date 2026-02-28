from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.validator_crew_runtime import (
    get_runtime_module,
)


def _default_validator_module() -> Any:
    return get_runtime_module()


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, module: Any | None = None) -> None:
        self._module = module or _default_validator_module()

    def run_validation_crew(self, raw_data: Any):
        return self._module.run_validation_crew(raw_data)
