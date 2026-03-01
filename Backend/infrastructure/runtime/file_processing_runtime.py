from __future__ import annotations

from Backend.infrastructure.runtime_services.file_processing_runtime_service import (
    FileProcessingRuntimeService,
)


class _FileProcessingRuntimeProvider:
    @staticmethod
    def get_runtime_service() -> FileProcessingRuntimeService:
        return FileProcessingRuntimeService()


get_runtime_service = _FileProcessingRuntimeProvider.get_runtime_service
