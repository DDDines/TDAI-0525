from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import validator_crew_module


class ValidatorCrewRuntimeService:
    """Explicit runtime service surface for validation crew flow."""

    def run_validation_crew(self, raw_data: Any):
        return validator_crew_module.run_validation_crew(raw_data)


validator_crew_runtime_service = ValidatorCrewRuntimeService()

