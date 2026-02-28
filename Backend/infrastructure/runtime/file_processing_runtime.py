from __future__ import annotations

from Backend.infrastructure.runtime_services.file_processing_runtime_service import (
    FileProcessingRuntimeService,
    file_processing_runtime_service,
)


def get_runtime_service() -> FileProcessingRuntimeService:
    return file_processing_runtime_service
