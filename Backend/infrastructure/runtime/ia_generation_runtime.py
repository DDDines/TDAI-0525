from __future__ import annotations
from Backend.infrastructure.runtime_services.ia_generation_runtime_service import IAGenerationRuntimeService

class IAGenerationRuntimeProvider:

    @staticmethod
    def get_runtime_service() -> IAGenerationRuntimeService:
        return IAGenerationRuntimeService()
