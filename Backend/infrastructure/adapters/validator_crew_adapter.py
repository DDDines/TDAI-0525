"""Document validator crew adapter module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.validator_crew_module import (
    ValidationCrewWorkflow,
)


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, runtime: ValidationCrewWorkflow | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for Validator Crew Service Adapter."""
        self._runtime = runtime or ValidationCrewWorkflow()

    def run_validation_crew(self, raw_data: Any):
        """Execute run validation crew as part of this module workflow."""
        return self._runtime.run_validation_crew(raw_data)
