from __future__ import annotations

from Backend.infrastructure.runtime_services.validator_crew_runtime_service import (
    ValidatorCrewRuntimeService,
    validator_crew_runtime_service,
)


def get_runtime_service() -> ValidatorCrewRuntimeService:
    return validator_crew_runtime_service
