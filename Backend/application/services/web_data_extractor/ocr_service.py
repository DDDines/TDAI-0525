"""Ocr service.

"""

from __future__ import annotations

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorOCRService:
    """Encapsulates Web data extractor o c r service."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize dependencies for WebDataExtractorOCRService."""
        self._port = port

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self._port.extract_text_from_image_region(image_bytes)
