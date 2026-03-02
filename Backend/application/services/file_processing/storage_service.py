"""Module storage service.

Contains backend logic related to storage service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingStorageService:
    """Operacoes de storage de catalogos."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ):
        """Run save uploaded catalog in this workflow."""
        return await self._port.save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Delete catalog file for this workflow."""
        return self._port.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Return file path by id for this workflow."""
        return self._port.get_file_path_by_id(db=db, file_id=file_id)
