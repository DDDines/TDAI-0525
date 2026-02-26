from __future__ import annotations

from types import SimpleNamespace
import asyncio

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_file_service import (
    CatalogImportFileService,
)


class _CatalogImportFileModel:
    user_id = object()
    fornecedor_id = object()
    created_at = SimpleNamespace(desc=lambda: object())


class _ModelsStub:
    CatalogImportFile = _CatalogImportFileModel


class _QueryStub:
    def __init__(self, *, items=None, first_record=None):
        self._items = items or []
        self._first_record = first_record
        self.offset_value = None
        self.limit_value = None

    def filter(self, *args, **kwargs):
        _ = (args, kwargs)
        return self

    def filter_by(self, **kwargs):
        _ = kwargs
        return self

    def count(self):
        return len(self._items)

    def order_by(self, *args, **kwargs):
        _ = (args, kwargs)
        return self

    def offset(self, value):
        self.offset_value = value
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def all(self):
        return self._items

    def first(self):
        return self._first_record


class _DbStub:
    def __init__(self, *, items=None, first_record=None):
        self._items = items or []
        self._first_record = first_record
        self.deleted = []
        self.commits = 0

    def query(self, model):
        _ = model
        return _QueryStub(items=self._items, first_record=self._first_record)

    def delete(self, item):
        self.deleted.append(item)

    def commit(self):
        self.commits += 1


class _FileProcessingStub:
    def __init__(self):
        self.deleted_files = []

    def delete_catalog_file(self, stored_filename):
        self.deleted_files.append(stored_filename)


class _CatalogImportStartServiceStub:
    def __init__(self):
        self.calls = []
        self.catalog_file = SimpleNamespace(id=77, fornecedor_id=3)

    def get_catalog_file_or_404(self, **kwargs):
        self.calls.append(("get_catalog_file_or_404", kwargs))
        return self.catalog_file

    def resolve_fornecedor_id(self, **kwargs):
        self.calls.append(("resolve_fornecedor_id", kwargs))
        return kwargs.get("fornecedor_id") or self.catalog_file.fornecedor_id

    def mark_processing(self, **kwargs):
        self.calls.append(("mark_processing", kwargs))

    def resolve_mapping(self, **kwargs):
        self.calls.append(("resolve_mapping", kwargs))
        return kwargs.get("mapping") or {"col_0": "nome_base"}

    def build_finalize_command(self, **kwargs):
        self.calls.append(("build_finalize_command", kwargs))
        return SimpleNamespace(**kwargs)

    async def dispatch_finalize(self, **kwargs):
        self.calls.append(("dispatch_finalize", kwargs))


def _build_service():
    file_processing = _FileProcessingStub()
    start_service = _CatalogImportStartServiceStub()
    service = CatalogImportFileService(
        models=_ModelsStub,
        file_processing_service=file_processing,
        catalog_import_start_service=start_service,
    )
    return service, file_processing, start_service


def test_list_user_files_builds_page_payload():
    service, _, _ = _build_service()
    db = _DbStub(items=[SimpleNamespace(id=1), SimpleNamespace(id=2)])

    payload = service.list_user_files(
        db=db,
        user_id=10,
        fornecedor_id=3,
        skip=0,
        limit=10,
    )

    assert payload["total_items"] == 2
    assert len(payload["items"]) == 2
    assert payload["page"] == 1
    assert payload["limit"] == 10


def test_get_user_file_or_404_raises_when_missing():
    service, _, _ = _build_service()
    db = _DbStub(first_record=None)

    with pytest.raises(HTTPException) as exc:
        service.get_user_file_or_404(db=db, file_id=7, user_id=10)

    assert exc.value.status_code == 404


def test_delete_user_file_deletes_binary_and_record():
    service, file_processing, _ = _build_service()
    record = SimpleNamespace(id=7, stored_filename="abc.pdf")
    db = _DbStub(first_record=record)

    deleted = service.delete_user_file(db=db, file_id=7, user_id=10)

    assert deleted is record
    assert file_processing.deleted_files == ["abc.pdf"]
    assert db.deleted == [record]
    assert db.commits == 1


def test_reprocess_catalog_file_dispatches_finalize():
    service, _, start_service = _build_service()

    payload = asyncio.run(
        service.reprocess_catalog_file(
            background_tasks=object(),
            db=object(),
            file_id=99,
            user_id=10,
            product_type_id=4,
            fornecedor_id=3,
            mapping={"col_0": "nome_base"},
            pages=[1, 2],
            region=[1.0, 2.0, 3.0, 4.0],
        )
    )

    assert payload == {"status": "PROCESSING", "file_id": 99}
    called_methods = [name for name, _kwargs in start_service.calls]
    assert "dispatch_finalize" in called_methods
