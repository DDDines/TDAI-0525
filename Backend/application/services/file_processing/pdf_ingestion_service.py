from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfIngestionService:
    """Ingestao e extracao de PDF."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._port.processar_arquivo_pdf(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self._port.extrair_pagina_pdf(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return self._port.extract_data_from_pdf_region(*args, **kwargs)

    async def process_pdf_job(self, *args: Any, **kwargs: Any):
        return await self._port.process_pdf_job(*args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return self._port.extract_data_from_single_page(*args, **kwargs)
