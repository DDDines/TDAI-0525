"""Module web data extractor runtime.

Contains backend logic related to web data extractor runtime and documents its role in the OOP architecture.
"""

from __future__ import annotations
from Backend.infrastructure.runtime_services.web_data_extractor_runtime_service import WebDataExtractorRuntimeService

class WebDataExtractorRuntimeProvider:

    """Represent web data extractor runtime provider and centralize responsibilities for this module."""
    @staticmethod
    def get_runtime_service() -> WebDataExtractorRuntimeService:
        """Return runtime service for this workflow."""
        return WebDataExtractorRuntimeService()
