from __future__ import annotations
from Backend.infrastructure.runtime_services.ia_generation_runtime_service import IAGenerationRuntimeService

class _IAGenerationRuntimeProvider:

    @staticmethod
    def get_runtime_service() -> IAGenerationRuntimeService:
        return IAGenerationRuntimeService()
