"""Module ia generation runtime.

Contains backend logic related to ia generation runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.ia_generation_runtime_service import IAGenerationRuntimeService

class IAGenerationRuntimeProvider:

    """Represent i a generation runtime provider and centralize responsibilities for this module."""
    @staticmethod
    def get_runtime_service() -> IAGenerationRuntimeService:
        """Return runtime service for this workflow."""
        return IAGenerationRuntimeService()
