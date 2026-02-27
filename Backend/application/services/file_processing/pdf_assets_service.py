from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfAssetsService:
    """Operacoes de assets de PDF e anotacoes."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return self._port.generate_pdf_page_images(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return self._port.extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return self._port.parse_annotation_to_dataframe(*args, **kwargs)
