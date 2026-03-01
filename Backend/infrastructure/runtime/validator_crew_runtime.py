from __future__ import annotations

from Backend.infrastructure.runtime_services.validator_crew_runtime_service import (
    ValidatorCrewRuntimeService,
)


def get_runtime_service() -> ValidatorCrewRuntimeService:
    return ValidatorCrewRuntimeService()
