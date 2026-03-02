"""Module ocr service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorOCRService:
    """Class WebDataExtractorOCRService.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Execute extract_text_from_image_region.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.extract_text_from_image_region(image_bytes)
