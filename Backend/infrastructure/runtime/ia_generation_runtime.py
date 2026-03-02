"""Ia generation runtime.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.ia_generation_runtime_service import IAGenerationRuntimeService

class IAGenerationRuntimeProvider:

    """Encapsulates I a generation runtime provider."""
    @staticmethod
    def get_runtime_service() -> IAGenerationRuntimeService:
        """Return Runtime service."""
        return IAGenerationRuntimeService()
