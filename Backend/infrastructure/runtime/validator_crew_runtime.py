"""Module validator crew runtime.

Contains backend logic related to validator crew runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.validator_crew_runtime_service import ValidatorCrewRuntimeService

class ValidatorCrewRuntimeProvider:

    """Represent validator crew runtime provider and centralize responsibilities for this module."""
    @staticmethod
    def get_runtime_service() -> ValidatorCrewRuntimeService:
        """Return runtime service for this workflow."""
        return ValidatorCrewRuntimeService()
