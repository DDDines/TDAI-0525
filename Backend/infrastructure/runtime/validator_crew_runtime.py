"""Validator crew runtime.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.validator_crew_runtime_service import ValidatorCrewRuntimeService

class ValidatorCrewRuntimeProvider:

    """Encapsulates Validator crew runtime provider."""
    @staticmethod
    def get_runtime_service() -> ValidatorCrewRuntimeService:
        """Return Runtime service."""
        return ValidatorCrewRuntimeService()
