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

    def get_catalog_file_or_404(self, *, db, file_id, user_id):
        _ = (db, file_id, user_id)
        return self._source

    def resolve_pdf_pages(self, *, catalog_file, start_page):
        _ = catalog_file
        return [start_page, start_page + 1]

    def resolve_mapping(self, *, db, fornecedor_id, mapping):
        _ = (db, fornecedor_id)
        return mapping or {"col_0": "nome_base"}

    def build_finalize_command(self, **kwargs):
        self.commands.append(kwargs)
        return SimpleNamespace(**kwargs)

    async def dispatch_finalize(self, *, background_tasks, db, command):
        self.dispatched.append((background_tasks, db, command))
        return {"ok": True}


class _DbStub:
    def __init__(self):
        self.added = []
        self.committed = 0
        self.refreshed = 0
        self._next_id = 900

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed += 1

    def refresh(self, item):
        self.refreshed += 1
        if getattr(item, "id", None) is None:
            item.id = self._next_id
            self._next_id += 1


def _build_service(*, fornecedor, source):
    return FornecedorCatalogProcessService(
        models=_ModelsStub,
        crud_fornecedores=_CrudFornecedoresStub(fornecedor=fornecedor),
        catalog_import_start_service=_CatalogImportStartServiceStub(source=source),
    )


@pytest.mark.asyncio
async def test_start_full_processing_dispatches_job():
    fornecedor = SimpleNamespace(id=3, user_id=10)
    source = SimpleNamespace(original_filename="orig.pdf", stored_filename="stored.pdf")
    db = _DbStub()
    service = _build_service(fornecedor=fornecedor, source=source)
    user = SimpleNamespace(id=10, is_superuser=False)

    result = await service.start_full_processing(
        background_tasks=object(),
        db=db,
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
    assert db.committed == 1
    assert len(db.added) == 1

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
    service = _build_service(fornecedor=None, source=source)

    with pytest.raises(HTTPException) as exc:
        await service.start_full_processing(
            background_tasks=object(),
            db=_DbStub(),
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
    service = _build_service(fornecedor=fornecedor, source=source)

    with pytest.raises(HTTPException) as exc:
        await service.start_full_processing(
            background_tasks=object(),
            db=_DbStub(),
            current_user=SimpleNamespace(id=1, is_superuser=False),
            file_id=1,
            fornecedor_id=3,
            tipo_produto_id=1,
            start_page=1,
            region=None,
            mapping=None,
        )

    assert exc.value.status_code == 403
