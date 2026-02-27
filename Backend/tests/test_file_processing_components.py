from __future__ import annotations

import pytest

from Backend.application.services.file_processing_components import (
    CatalogExtractionService,
    CatalogPreviewService,
    CatalogStorageService,
)


class _LegacyFileModuleStub:
    def __init__(self) -> None:
        self.calls = []

    async def save_uploaded_catalog(self, *args, **kwargs):
        self.calls.append(("save_uploaded_catalog", args, kwargs))
        return {"id": 1}

    def delete_catalog_file(self, *args, **kwargs):
        self.calls.append(("delete_catalog_file", args, kwargs))
        return True

    async def gerar_preview(self, *args, **kwargs):
        self.calls.append(("gerar_preview", args, kwargs))
        return {"preview": []}

    async def processar_arquivo_csv(self, *args, **kwargs):
        self.calls.append(("processar_arquivo_csv", args, kwargs))
        return {"produtos": []}

    def processar_linha_padronizada(self, *args, **kwargs):
        self.calls.append(("processar_linha_padronizada", args, kwargs))
        return {"nome_base": "x"}


@pytest.mark.asyncio
async def test_catalog_storage_service_delegates_async_and_sync_calls():
    legacy = _LegacyFileModuleStub()
    service = CatalogStorageService(legacy)

    result = await service.save_uploaded_catalog("db", "file")
    deleted = service.delete_catalog_file("x.pdf")

    assert result == {"id": 1}
    assert deleted is True
    assert legacy.calls[0][0] == "save_uploaded_catalog"
    assert legacy.calls[1][0] == "delete_catalog_file"


@pytest.mark.asyncio
async def test_catalog_preview_service_delegates_preview_calls():
    legacy = _LegacyFileModuleStub()
    service = CatalogPreviewService(legacy)

    result = await service.gerar_preview("content", ".csv")

    assert result == {"preview": []}
    assert legacy.calls[0][0] == "gerar_preview"


@pytest.mark.asyncio
async def test_catalog_extraction_service_delegates_processing_calls():
    legacy = _LegacyFileModuleStub()
    service = CatalogExtractionService(legacy)

    result = await service.processar_arquivo_csv("bytes", {})

    assert result == {"produtos": []}
    assert legacy.calls[0][0] == "processar_arquivo_csv"


def test_catalog_extraction_service_uses_public_row_standardizer():
    legacy = _LegacyFileModuleStub()
    service = CatalogExtractionService(legacy)

    result = service.processar_linha_padronizada({"a": 1}, None)

    assert result == {"nome_base": "x"}
    assert legacy.calls[0][0] == "processar_linha_padronizada"
