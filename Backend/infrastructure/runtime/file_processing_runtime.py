"""Module file processing runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.file_processing_runtime_service import FileProcessingRuntimeService

class FileProcessingRuntimeProvider:

    """Class FileProcessingRuntimeProvider.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_runtime_service() -> FileProcessingRuntimeService:
        """Execute get_runtime_service.

        This callable is documented to make behavior explicit for readers.
        """
        return FileProcessingRuntimeService()
