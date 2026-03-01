from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.validator_crew_module import (
    ValidationCrewWorkflow,
)


class ValidatorCrewRuntimeService:
    """Explicit runtime service surface for validation crew flow."""

    def __init__(self) -> None:
        self._workflow = ValidationCrewWorkflow()

    def run_validation_crew(self, raw_data: Any):
        return self._workflow.run_validation_crew(raw_data)
