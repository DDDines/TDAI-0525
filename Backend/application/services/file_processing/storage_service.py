from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingStorageService:
    """Operacoes de storage de catalogos."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self._port.save_uploaded_catalog(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self._port.delete_catalog_file(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return self._port.get_file_path_by_id(*args, **kwargs)
