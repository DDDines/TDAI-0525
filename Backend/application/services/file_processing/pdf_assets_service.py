"""Pdf assets service.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfAssetsService:
    """Operacoes de assets de PDF e anotacoes."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._port = port

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Process Generate pdf page images."""
        return self._port.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Extract pdf region image."""
        return self._port.extract_pdf_region_image(
            file_path=file_path,
            page_number=page_number,
            region=region,
            dpi=dpi,
        )

    def parse_annotation_to_dataframe(
        self,
        annotation: object,
        vertical_tolerance: int = 5,
    ) -> pd.DataFrame:
        """Parse annotation to dataframe."""
        return self._port.parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )
