from __future__ import annotations
from Backend.infrastructure.runtime_services.limit_runtime_service import LimitRuntimeService

class LimitRuntimeProvider:

    @staticmethod
    def get_runtime_service() -> LimitRuntimeService:
        return LimitRuntimeService()
