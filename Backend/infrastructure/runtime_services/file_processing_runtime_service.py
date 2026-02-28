from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import file_processing_module


class FileProcessingRuntimeService:
    """Explicit runtime service surface for file processing flows."""

    def __init__(self) -> None:
        self._catalog_storage = None
        self._line_mapping = None
        self._tabular_ingestion = None
        self._tabular_preview = None
        self._pdf_asset = None
        self._pdf_processing = None
        self._pdf_job = None

    def _get_catalog_storage(self):
        if self._catalog_storage is None:
            self._catalog_storage = file_processing_module.get_catalog_storage_workflow()
        return self._catalog_storage

    def _get_line_mapping(self):
        if self._line_mapping is None:
            self._line_mapping = file_processing_module.get_line_mapping_workflow()
        return self._line_mapping

    def _get_tabular_ingestion(self):
        if self._tabular_ingestion is None:
            self._tabular_ingestion = file_processing_module.get_tabular_ingestion_workflow()
        return self._tabular_ingestion

    def _get_tabular_preview(self):
        if self._tabular_preview is None:
            self._tabular_preview = file_processing_module.get_tabular_preview_workflow()
        return self._tabular_preview

    def _get_pdf_asset(self):
        if self._pdf_asset is None:
            self._pdf_asset = file_processing_module.get_pdf_asset_workflow()
        return self._pdf_asset

    def _get_pdf_processing(self):
        if self._pdf_processing is None:
            self._pdf_processing = file_processing_module.get_pdf_processing_workflow()
        return self._pdf_processing

    def _get_pdf_job(self):
        if self._pdf_job is None:
            self._pdf_job = file_processing_module.get_pdf_job_workflow()
        return self._pdf_job

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self._get_catalog_storage().save_uploaded_catalog(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self._get_catalog_storage().delete_catalog_file(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return self._get_catalog_storage().get_file_path_by_id(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._get_tabular_ingestion().processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._get_tabular_ingestion().processar_arquivo_csv(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_processing().processar_arquivo_pdf(*args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._get_tabular_preview().preview_arquivo_excel(*args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._get_tabular_preview().preview_arquivo_csv(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_processing().preview_arquivo_pdf(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_processing().gerar_preview(*args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_asset().pdf_bytes_to_images(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return self._get_pdf_asset().pdf_pages_to_images(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_asset().extrair_pagina_pdf(*args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return self._get_pdf_asset().generate_pdf_page_images(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return self._get_pdf_asset().extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return self._get_pdf_asset().parse_annotation_to_dataframe(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return self._get_pdf_processing().extract_data_from_pdf_region(*args, **kwargs)

    async def process_pdf_job(self, *args: Any, **kwargs: Any):
        return await self._get_pdf_job().process_pdf_job(*args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return self._get_pdf_job().extract_data_from_single_page(*args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return self._get_line_mapping().processar_linha_padronizada(*args, **kwargs)


file_processing_runtime_service = FileProcessingRuntimeService()
