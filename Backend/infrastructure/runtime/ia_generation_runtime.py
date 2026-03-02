"""Module ia generation runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.ia_generation_runtime_service import IAGenerationRuntimeService

class IAGenerationRuntimeProvider:

    """Class IAGenerationRuntimeProvider.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_runtime_service() -> IAGenerationRuntimeService:
        """Execute get_runtime_service.

        This callable is documented to make behavior explicit for readers.
        """
        return IAGenerationRuntimeService()
