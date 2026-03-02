"""Module ocr service.

Contains backend logic related to ocr service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorOCRService:
    """Represent web data extractor o c r service and centralize responsibilities for this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region for this workflow."""
        return self._port.extract_text_from_image_region(image_bytes)
