"""Module validator crew runtime service.

Contains backend logic related to validator crew runtime service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.validator_crew_module import (
    ValidationCrewWorkflow,
)


class ValidatorCrewRuntimeService:
    """Explicit runtime service surface for validation crew flow."""

    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._workflow = ValidationCrewWorkflow()

    def run_validation_crew(self, raw_data: Any):
        """Run validation crew for this workflow."""
        return self._workflow.run_validation_crew(raw_data)
