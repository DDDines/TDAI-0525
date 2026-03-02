"""Module validator crew adapter.

Contains backend logic related to validator crew adapter and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.validator_crew_module import (
    ValidationCrewWorkflow,
)


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, runtime: ValidationCrewWorkflow | None = None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._runtime = runtime or ValidationCrewWorkflow()

    def run_validation_crew(self, raw_data: Any):
        """Run validation crew for this workflow."""
        return self._runtime.run_validation_crew(raw_data)
