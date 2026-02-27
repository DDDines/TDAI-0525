from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingTabularIngestionService:
    """Ingestao de arquivos tabulares (Excel/CSV)."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._port.processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._port.processar_arquivo_csv(*args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._port.preview_arquivo_excel(*args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._port.preview_arquivo_csv(*args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return self._port.processar_linha_padronizada(*args, **kwargs)
