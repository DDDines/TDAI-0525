"""Document pdf assets service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfAssetsService:
    """Operacoes de assets de PDF e anotacoes."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize injected dependencies and runtime configuration for File Processing Pdf Assets Service."""
        self._port = port

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate pdf page images as part of this module workflow."""
        return self._port.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Execute extract pdf region image as part of this module workflow."""
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
        """Parse annotation to dataframe into structured data used by downstream logic."""
        return self._port.parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )
