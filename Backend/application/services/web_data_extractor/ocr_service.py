from __future__ import annotations

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorOCRService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    def extract_text_from_image_region(self, image_bytes: bytes):
        return self._port.extract_text_from_image_region(image_bytes)
