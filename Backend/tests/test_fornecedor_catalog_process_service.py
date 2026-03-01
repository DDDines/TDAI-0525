from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_catalog_process_service import (
    FornecedorCatalogProcessService,
)


class _CatalogImportFileModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.id = None


class _ModelsStub:
    CatalogImportFile = _CatalogImportFileModel


class _CrudFornecedoresStub:
    def __init__(self, fornecedor):
        self._fornecedor = fornecedor

    def get_fornecedor(self, db, fornecedor_id):
        _ = (db, fornecedor_id)
        return self._fornecedor


class _CatalogImportStartServiceStub:
    def __init__(self, source):
        self._source = source
        self.dispatched = []
        self.commands = []

    def get_catalog_file_or_404(self, **kwargs):
        _ = kwargs
        return self._source

    def resolve_pdf_pages(self, *, catalog_file, start_page):
        _ = catalog_file
        return [start_page, start_page + 1]

    def resolve_mapping(self, **kwargs):
        _ = kwargs
        return kwargs.get("mapping") or {"col_0": "nome_base"}

    def build_finalize_command(self, **kwargs):
        self.commands.append(kwargs)
        return SimpleNamespace(**kwargs)

    async def dispatch_finalize(self, **kwargs):
        self.dispatched.append(kwargs)
        return {"ok": True}


class _DbStub:
    def __init__(self):
        self.saved = []
        self._next_id = 900

    def save_catalog_file(self, *, catalog_file):
        self.saved.append(catalog_file)
        if getattr(catalog_file, "id", None) is None:
            catalog_file.id = self._next_id
            self._next_id += 1
        return catalog_file


def _build_service(*, fornecedor, source):
    fornecedor_repo = _CrudFornecedoresStub(fornecedor=fornecedor)
    catalog_file_repo = _DbStub()
    service = FornecedorCatalogProcessService(
        models=_ModelsStub,
        fornecedor_repo=fornecedor_repo,
        catalog_file_repository=catalog_file_repo,
        catalog_import_start_service=_CatalogImportStartServiceStub(source=source),
    )
    return service, catalog_file_repo


@pytest.mark.asyncio
async def test_start_full_processing_dispatches_job():
    fornecedor = SimpleNamespace(id=3, user_id=10)
    source = SimpleNamespace(original_filename="orig.pdf", stored_filename="stored.pdf")
    service, catalog_file_repo = _build_service(fornecedor=fornecedor, source=source)
    user = SimpleNamespace(id=10, is_superuser=False)

    result = await service.start_full_processing(
        background_tasks=object(),
        db_session_factory=lambda: object(),
        current_user=user,
        file_id=99,
        fornecedor_id=3,
        tipo_produto_id=7,
        start_page=4,
        region=[0.1, 0.2, 0.3, 0.4],
        mapping=None,
    )

    assert result["status"] == "PROCESSING"
    assert result["job_id"] == 900
    assert len(catalog_file_repo.saved) == 1

    start_stub = service._catalog_import_start_service
    assert len(start_stub.dispatched) == 1
    assert len(start_stub.commands) == 1
    command_data = start_stub.commands[0]
    assert command_data["file_id"] == 900
    assert command_data["product_type_id"] == 7
    assert command_data["pages"] == [4, 5]


@pytest.mark.asyncio
async def test_start_full_processing_raises_when_fornecedor_not_found():
    source = SimpleNamespace(original_filename="orig.pdf", stored_filename="stored.pdf")
    service, _ = _build_service(fornecedor=None, source=source)

    with pytest.raises(HTTPException) as exc:
        await service.start_full_processing(
            background_tasks=object(),
            db_session_factory=lambda: object(),
            current_user=SimpleNamespace(id=1, is_superuser=False),
            file_id=1,
            fornecedor_id=99,
            tipo_produto_id=1,
            start_page=1,
            region=None,
            mapping=None,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_start_full_processing_raises_when_user_not_allowed():
    fornecedor = SimpleNamespace(id=3, user_id=99)
    source = SimpleNamespace(original_filename="orig.pdf", stored_filename="stored.pdf")
    service, _ = _build_service(fornecedor=fornecedor, source=source)

    with pytest.raises(HTTPException) as exc:
        await service.start_full_processing(
            background_tasks=object(),
            db_session_factory=lambda: object(),
            current_user=SimpleNamespace(id=1, is_superuser=False),
            file_id=1,
            fornecedor_id=3,
            tipo_produto_id=1,
            start_page=1,
            region=None,
            mapping=None,
        )

    assert exc.value.status_code == 403
