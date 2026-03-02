"""Module storage service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingStorageService:
    """Operacoes de storage de catalogos."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ):
        """Execute save_uploaded_catalog.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete_catalog_file.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Execute get_file_path_by_id.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.get_file_path_by_id(db=db, file_id=file_id)
