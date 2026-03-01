from __future__ import annotations

from Backend.infrastructure.runtime_services.validator_crew_runtime_service import (
    ValidatorCrewRuntimeService,
)


class _ValidatorCrewRuntimeProvider:
    @staticmethod
    def get_runtime_service() -> ValidatorCrewRuntimeService:
        return ValidatorCrewRuntimeService()


get_runtime_service = _ValidatorCrewRuntimeProvider.get_runtime_service
