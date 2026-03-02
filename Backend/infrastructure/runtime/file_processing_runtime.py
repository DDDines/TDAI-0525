"""Module file processing runtime.

Contains backend logic related to file processing runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.file_processing_runtime_service import FileProcessingRuntimeService

class FileProcessingRuntimeProvider:

    """Represent file processing runtime provider and centralize responsibilities for this module."""
    @staticmethod
    def get_runtime_service() -> FileProcessingRuntimeService:
        """Return runtime service for this workflow."""
        return FileProcessingRuntimeService()
