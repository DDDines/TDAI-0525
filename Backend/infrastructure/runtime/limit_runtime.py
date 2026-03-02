"""Limit runtime.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.limit_runtime_service import LimitRuntimeService

class LimitRuntimeProvider:

    """Encapsulates Limit runtime provider."""
    @staticmethod
    def get_runtime_service() -> LimitRuntimeService:
        """Return Runtime service."""
        return LimitRuntimeService()
