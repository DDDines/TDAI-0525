from __future__ import annotations

from Backend.infrastructure.runtime_services.limit_runtime_service import (
    LimitRuntimeService,
)


class _LimitRuntimeProvider:
    @staticmethod
    def get_runtime_service() -> LimitRuntimeService:
        return LimitRuntimeService()


get_runtime_service = _LimitRuntimeProvider.get_runtime_service
