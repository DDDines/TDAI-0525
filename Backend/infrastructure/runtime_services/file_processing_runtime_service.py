from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import file_processing_module


class FileProcessingRuntimeService:
    """Explicit runtime service surface for file processing flows."""

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await file_processing_module.save_uploaded_catalog(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return file_processing_module.delete_catalog_file(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return file_processing_module.get_file_path_by_id(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await file_processing_module.processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await file_processing_module.processar_arquivo_csv(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await file_processing_module.processar_arquivo_pdf(*args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await file_processing_module.preview_arquivo_excel(*args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await file_processing_module.preview_arquivo_csv(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await file_processing_module.preview_arquivo_pdf(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await file_processing_module.gerar_preview(*args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await file_processing_module.pdf_bytes_to_images(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return file_processing_module.pdf_pages_to_images(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await file_processing_module.extrair_pagina_pdf(*args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return file_processing_module.generate_pdf_page_images(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return file_processing_module.extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return file_processing_module.parse_annotation_to_dataframe(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return file_processing_module.extract_data_from_pdf_region(*args, **kwargs)

    async def process_pdf_job(self, *args: Any, **kwargs: Any):
        return await file_processing_module.process_pdf_job(*args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return file_processing_module.extract_data_from_single_page(*args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return file_processing_module.processar_linha_padronizada(*args, **kwargs)


file_processing_runtime_service = FileProcessingRuntimeService()

