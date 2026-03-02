"""Module web data extractor runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.web_data_extractor_runtime_service import WebDataExtractorRuntimeService

class WebDataExtractorRuntimeProvider:

    """Class WebDataExtractorRuntimeProvider.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_runtime_service() -> WebDataExtractorRuntimeService:
        """Execute get_runtime_service.

        This callable is documented to make behavior explicit for readers.
        """
        return WebDataExtractorRuntimeService()
