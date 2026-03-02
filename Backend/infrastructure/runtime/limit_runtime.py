"""Module limit runtime.

Contains backend logic related to limit runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.limit_runtime_service import LimitRuntimeService

class LimitRuntimeProvider:

    """Represent limit runtime provider and centralize responsibilities for this module."""
    @staticmethod
    def get_runtime_service() -> LimitRuntimeService:
        """Return runtime service for this workflow."""
        return LimitRuntimeService()
