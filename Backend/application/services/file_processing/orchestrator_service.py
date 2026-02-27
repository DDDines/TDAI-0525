from __future__ import annotations

from typing import Any, Dict, Optional

from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.file_processing.pdf_assets_service import (
    FileProcessingPdfAssetsService,
)
from Backend.application.services.file_processing.pdf_ingestion_service import (
    FileProcessingPdfIngestionService,
)
from Backend.application.services.file_processing.preview_service import (
    FileProcessingPreviewService,
)
from Backend.application.services.file_processing.storage_service import (
    FileProcessingStorageService,
)
from Backend.application.services.file_processing.tabular_ingestion_service import (
    FileProcessingTabularIngestionService,
)


class FileProcessingOrchestratorService:
    """Servico OO unificado para processamento de arquivos de catalogo."""

    def __init__(self, port: FileProcessingPort) -> None:
        self._port = port
        self.storage = FileProcessingStorageService(port)
        self.tabular = FileProcessingTabularIngestionService(port)
        self.pdf = FileProcessingPdfIngestionService(port)
        self.preview = FileProcessingPreviewService(port)
        self.pdf_assets = FileProcessingPdfAssetsService(port)

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self.storage.save_uploaded_catalog(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self.storage.delete_catalog_file(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return self.storage.get_file_path_by_id(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self.tabular.processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self.tabular.processar_arquivo_csv(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self.pdf.processar_arquivo_pdf(*args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self.tabular.preview_arquivo_excel(*args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self.tabular.preview_arquivo_csv(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self.preview.preview_arquivo_pdf(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self.preview.gerar_preview(*args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await self.preview.pdf_bytes_to_images(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return self.preview.pdf_pages_to_images(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self.pdf.extrair_pagina_pdf(*args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return self.pdf_assets.generate_pdf_page_images(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return self.pdf_assets.extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return self.pdf_assets.parse_annotation_to_dataframe(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return self.pdf.extract_data_from_pdf_region(*args, **kwargs)

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        await self.pdf.process_pdf_job(
            job_id=job_id,
            pdf_path=pdf_path,
            start_page=start_page,
            mapping=mapping,
        )

    def extract_data_from_single_page(self, file_path: str, page_number: int) -> Dict[str, Any]:
        return self.pdf.extract_data_from_single_page(file_path=file_path, page_number=page_number)

    def processar_linha_padronizada(
        self,
        row: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
    ) -> Dict[str, Any]:
        return self.tabular.processar_linha_padronizada(row, mapeamento_colunas_usuario)
