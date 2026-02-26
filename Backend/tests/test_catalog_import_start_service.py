from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_start_service import (
    CatalogImportStartService,
)


class _QueryStub:
    def __init__(self, record):
        self._record = record

    def filter_by(self, **kwargs):
        _ = kwargs
        return self

    def first(self):
        return self._record


class _DbStub:
    def __init__(self, record):
        self._record = record
        self.committed = False
        self._bind = object()

    def query(self, model):
        _ = model
        return _QueryStub(self._record)

    def commit(self):
        self.committed = True

    def get_bind(self):
        return self._bind


class _CrudFornecedoresStub:
    def __init__(self, fornecedor=None):
        self._fornecedor = fornecedor

    def get_fornecedor(self, db, fornecedor_id):
        _ = (db, fornecedor_id)
        return self._fornecedor


class _FinalizeServiceStub:
    def __init__(self):
        self.calls = []
        self.direct_calls = []

    async def dispatch_or_run(self, *, background_tasks, db_session_factory, command):
        self.calls.append((background_tasks, db_session_factory, command))
        return {"ok": True}

    async def run_direct(self, *, db_session_factory, command):
        self.direct_calls.append((db_session_factory, command))
        return {"ok": True}


class _ModelsStub:
    class CatalogImportFile:
        pass


def _build_service(*, upload_dir: str, fornecedor=None, finalize_service=None):
    return CatalogImportStartService(
        models=_ModelsStub,
        crud_fornecedores=_CrudFornecedoresStub(fornecedor=fornecedor),
        settings=SimpleNamespace(UPLOAD_DIRECTORY=upload_dir),
        resolve_storage_path=lambda p: Path(p),
        finalize_service=finalize_service or _FinalizeServiceStub(),
    )


def test_get_catalog_file_or_404_success():
    service = _build_service(upload_dir=".")
    record = SimpleNamespace(id=1)

    found = service.get_catalog_file_or_404(db=_DbStub(record), file_id=1, user_id=9)

    assert found is record


def test_get_catalog_file_or_404_not_found():
    service = _build_service(upload_dir=".")

    with pytest.raises(HTTPException) as exc:
        service.get_catalog_file_or_404(db=_DbStub(None), file_id=1, user_id=9)

    assert exc.value.status_code == 404


def test_resolve_fornecedor_id_fallback_and_required_error():
    service = _build_service(upload_dir=".")
    record = SimpleNamespace(fornecedor_id=7)

    assert (
        service.resolve_fornecedor_id(
            catalog_file=record,
            fornecedor_id=None,
            required_message="fornecedor obrigatorio",
        )
        == 7
    )

    with pytest.raises(HTTPException) as exc:
        service.resolve_fornecedor_id(
            catalog_file=SimpleNamespace(fornecedor_id=None),
            fornecedor_id=None,
            required_message="fornecedor obrigatorio",
        )

    assert exc.value.status_code == 400


def test_mark_processing_updates_record_and_commits():
    service = _build_service(upload_dir=".")
    record = SimpleNamespace(status="DONE", fornecedor_id=None, pages_processed=3, total_pages=8)
    db = _DbStub(record)

    service.mark_processing(
        db=db,
        catalog_file=record,
        fornecedor_id=11,
        reset_pages=True,
    )

    assert record.status == "PROCESSING"
    assert record.fornecedor_id == 11
    assert record.pages_processed == 0
    assert record.total_pages == 0
    assert db.committed is True


def test_ensure_catalog_binary_exists(tmp_path):
    upload_dir = tmp_path / "uploads"
    (upload_dir / "catalogs").mkdir(parents=True)
    file_path = upload_dir / "catalogs" / "ok.pdf"
    file_path.write_text("x", encoding="utf-8")

    service = _build_service(upload_dir=str(upload_dir))
    service.ensure_catalog_binary_exists(catalog_file=SimpleNamespace(stored_filename="ok.pdf"))

    with pytest.raises(HTTPException) as exc:
        service.ensure_catalog_binary_exists(catalog_file=SimpleNamespace(stored_filename="missing.pdf"))
    assert exc.value.status_code == 404


def test_resolve_pdf_pages_validates_file_presence_and_extension(tmp_path):
    upload_dir = tmp_path / "uploads"
    (upload_dir / "catalogs").mkdir(parents=True)
    service = _build_service(upload_dir=str(upload_dir))

    with pytest.raises(HTTPException) as exc_missing:
        service.resolve_pdf_pages(
            catalog_file=SimpleNamespace(stored_filename="missing.pdf"),
            start_page=1,
        )
    assert exc_missing.value.status_code == 404

    txt_file = upload_dir / "catalogs" / "arquivo.txt"
    txt_file.write_text("conteudo", encoding="utf-8")
    with pytest.raises(HTTPException) as exc_ext:
        service.resolve_pdf_pages(
            catalog_file=SimpleNamespace(stored_filename="arquivo.txt"),
            start_page=1,
        )
    assert exc_ext.value.status_code == 400


def test_resolve_pdf_pages_returns_range_from_start(tmp_path):
    upload_dir = tmp_path / "uploads"
    (upload_dir / "catalogs").mkdir(parents=True)
    pdf_file = upload_dir / "catalogs" / "catalogo.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 fake")

    service = _build_service(upload_dir=str(upload_dir))
    service._count_pdf_pages = lambda _content: 5  # type: ignore[attr-defined]

    pages = service.resolve_pdf_pages(
        catalog_file=SimpleNamespace(stored_filename="catalogo.pdf"),
        start_page=3,
    )

    assert pages == [3, 4, 5]


def test_resolve_mapping_prefers_input_then_default():
    default_mapping = {"col_0": "nome_base"}
    service = _build_service(
        upload_dir=".",
        fornecedor=SimpleNamespace(default_column_mapping=default_mapping),
    )
    db = _DbStub(record=object())

    assert service.resolve_mapping(db=db, fornecedor_id=1, mapping={"col_1": "sku"}) == {"col_1": "sku"}
    assert service.resolve_mapping(db=db, fornecedor_id=1, mapping=None) == default_mapping


@pytest.mark.asyncio
async def test_dispatch_finalize_calls_finalize_service():
    finalize_service = _FinalizeServiceStub()
    service = _build_service(upload_dir=".", finalize_service=finalize_service)
    db = _DbStub(record=object())
    command = service.build_finalize_command(
        file_id=3,
        user_id=9,
        product_type_id=2,
        fornecedor_id=8,
        mapping={"col_0": "nome_base"},
        pages=[1, 2],
        region=[0.1, 0.2, 0.3, 0.4],
    )

    await service.dispatch_finalize(
        background_tasks=object(),
        db=db,
        command=command,
    )

    assert len(finalize_service.calls) == 1
    _, factory, called_command = finalize_service.calls[0]
    assert callable(factory)
    assert called_command.file_id == 3


@pytest.mark.asyncio
async def test_run_finalize_direct_calls_finalize_service():
    finalize_service = _FinalizeServiceStub()
    service = _build_service(upload_dir=".", finalize_service=finalize_service)
    db = _DbStub(record=object())
    command = service.build_finalize_command(
        file_id=12,
        user_id=5,
        product_type_id=None,
        fornecedor_id=8,
        mapping=None,
        pages=[3],
        region=None,
    )

    await service.run_finalize_direct(
        db=db,
        command=command,
    )

    assert len(finalize_service.direct_calls) == 1
    factory, called_command = finalize_service.direct_calls[0]
    assert callable(factory)
    assert called_command.file_id == 12
