"""Module limit runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.limit_runtime_service import LimitRuntimeService

class LimitRuntimeProvider:

    """Class LimitRuntimeProvider.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_runtime_service() -> LimitRuntimeService:
        """Execute get_runtime_service.

        This callable is documented to make behavior explicit for readers.
        """
        return LimitRuntimeService()
