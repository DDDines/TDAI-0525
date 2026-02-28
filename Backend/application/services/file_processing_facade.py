from __future__ import annotations

from typing import Any

from Backend.application.services.file_processing import (
    FileProcessingOrchestratorService,
    FileProcessingPort,
)
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)


class FileProcessingFacade:
    """Explicit OOP facade for file processing."""

    def __init__(
        self,
        *,
        port: FileProcessingPort | None = None,
    ) -> None:
        effective_port = port or FileProcessingServiceAdapter()
        self._orchestrator = FileProcessingOrchestratorService(effective_port)
        self.storage = self._orchestrator.storage
        self.preview = self._orchestrator.preview
        self.extraction = self._orchestrator.pdf

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.save_uploaded_catalog(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.gerar_preview(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.preview_arquivo_pdf(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.processar_arquivo_pdf(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.processar_arquivo_csv(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.extrair_pagina_pdf(*args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return self._orchestrator.processar_linha_padronizada(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self._orchestrator.delete_catalog_file(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return self._orchestrator.get_file_path_by_id(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extract_data_from_pdf_region(*args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extract_data_from_single_page(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return self._orchestrator.parse_annotation_to_dataframe(*args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return self._orchestrator.generate_pdf_page_images(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return self._orchestrator.pdf_pages_to_images(*args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.pdf_bytes_to_images(*args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.preview_arquivo_excel(*args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.preview_arquivo_csv(*args, **kwargs)

    async def process_pdf_job(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.process_pdf_job(*args, **kwargs)
