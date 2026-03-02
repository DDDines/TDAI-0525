"""Module pdf assets service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfAssetsService:
    """Operacoes de assets de PDF e anotacoes."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate_pdf_page_images.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Execute extract_pdf_region_image.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute parse_annotation_to_dataframe.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )
