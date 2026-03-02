"""Web data extractor runtime.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.web_data_extractor_runtime_service import WebDataExtractorRuntimeService

class WebDataExtractorRuntimeProvider:

    """Encapsulates Web data extractor runtime provider."""
    @staticmethod
    def get_runtime_service() -> WebDataExtractorRuntimeService:
        """Return Runtime service."""
        return WebDataExtractorRuntimeService()
