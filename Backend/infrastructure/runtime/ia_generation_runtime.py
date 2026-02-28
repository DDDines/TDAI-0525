from __future__ import annotations

from Backend.infrastructure.runtime_services.ia_generation_runtime_service import (
    IAGenerationRuntimeService,
    ia_generation_runtime_service,
)


def get_runtime_service() -> IAGenerationRuntimeService:
    return ia_generation_runtime_service
