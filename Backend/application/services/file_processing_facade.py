from __future__ import annotations

from typing import Any

from Backend.services import file_processing_service as legacy_file_processing_service


class FileProcessingFacade:
    """Adaptador OO para o módulo legado de processamento de arquivos.

    Mantém compatibilidade total via ``__getattr__`` para permitir migração
    incremental sem remover o código legado existente.
    """

    def __init__(self, legacy_module: Any = legacy_file_processing_service) -> None:
        self._legacy = legacy_module

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await self._legacy.save_uploaded_catalog(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await self._legacy.gerar_preview(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._legacy.preview_arquivo_pdf(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await self._legacy.processar_arquivo_pdf(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await self._legacy.processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await self._legacy.processar_arquivo_csv(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await self._legacy.extrair_pagina_pdf(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return self._legacy.delete_catalog_file(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._legacy, item)

