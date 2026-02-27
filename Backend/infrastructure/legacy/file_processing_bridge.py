from __future__ import annotations

from typing import Any, Optional

from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.services import file_processing_service


class LegacyFileProcessingBridge:
    """Bridge explicito para o modulo legado de processamento de arquivos."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or file_processing_service

    @staticmethod
    def _assert_legacy_allowed() -> None:
        assert_legacy_usage_allowed(
            "Backend.infrastructure.legacy.LegacyFileProcessingBridge"
        )

    def _call(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return getattr(self._module, method_name)(*args, **kwargs)

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return await getattr(self._module, method_name)(*args, **kwargs)

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self._call_async("save_uploaded_catalog", *args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self._call("delete_catalog_file", *args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return self._call("get_file_path_by_id", *args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._call_async("processar_arquivo_excel", *args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._call_async("processar_arquivo_csv", *args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._call_async("processar_arquivo_pdf", *args, **kwargs)

    async def preview_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._call_async("preview_arquivo_excel", *args, **kwargs)

    async def preview_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._call_async("preview_arquivo_csv", *args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._call_async("preview_arquivo_pdf", *args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self._call_async("gerar_preview", *args, **kwargs)

    async def pdf_bytes_to_images(self, *args: Any, **kwargs: Any):
        return await self._call_async("pdf_bytes_to_images", *args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return self._call("pdf_pages_to_images", *args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self._call_async("extrair_pagina_pdf", *args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return self._call("generate_pdf_page_images", *args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return self._call("extract_pdf_region_image", *args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return self._call("parse_annotation_to_dataframe", *args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return self._call("extract_data_from_pdf_region", *args, **kwargs)

    async def process_pdf_job(self, *args: Any, **kwargs: Any):
        return await self._call_async("process_pdf_job", *args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return self._call("extract_data_from_single_page", *args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return self._call("processar_linha_padronizada", *args, **kwargs)
