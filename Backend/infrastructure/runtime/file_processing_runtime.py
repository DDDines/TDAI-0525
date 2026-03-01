from __future__ import annotations

from Backend.infrastructure.runtime_services.file_processing_runtime_service import (
    FileProcessingRuntimeService,
)


def get_runtime_service() -> FileProcessingRuntimeService:
    return FileProcessingRuntimeService()
