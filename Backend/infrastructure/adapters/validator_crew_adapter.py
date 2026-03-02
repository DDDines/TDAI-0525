"""Validator crew adapter.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.validator_crew_module import (
    ValidationCrewWorkflow,
)


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, runtime: ValidationCrewWorkflow | None = None) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._runtime = runtime or ValidationCrewWorkflow()

    def run_validation_crew(self, raw_data: Any):
        """Run validation crew."""
        return self._runtime.run_validation_crew(raw_data)
