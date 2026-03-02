"""Module validator crew runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.validator_crew_runtime_service import ValidatorCrewRuntimeService

class ValidatorCrewRuntimeProvider:

    """Class ValidatorCrewRuntimeProvider.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_runtime_service() -> ValidatorCrewRuntimeService:
        """Execute get_runtime_service.

        This callable is documented to make behavior explicit for readers.
        """
        return ValidatorCrewRuntimeService()
