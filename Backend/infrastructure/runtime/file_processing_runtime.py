"""File processing runtime.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.file_processing_runtime_service import FileProcessingRuntimeService

class FileProcessingRuntimeProvider:

    """Encapsulates File processing runtime provider."""
    @staticmethod
    def get_runtime_service() -> FileProcessingRuntimeService:
        """Return Runtime service."""
        return FileProcessingRuntimeService()
