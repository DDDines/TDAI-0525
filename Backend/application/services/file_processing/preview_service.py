from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPreviewService:
    """Preview de conteudo tabular e PDF."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._port.preview_arquivo_pdf(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self._port.gerar_preview(*args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await self._port.pdf_bytes_to_images(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return self._port.pdf_pages_to_images(*args, **kwargs)
