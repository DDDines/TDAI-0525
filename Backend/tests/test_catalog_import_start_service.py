"""Module test catalog import start service.

Contains backend logic related to test catalog import start service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_start_service import (
    CatalogImportStartService,
)


class _FinalizeServiceStub:
    """Represent finalize service stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []
        self.direct_calls = []

    async def dispatch_or_run(self, *, background_tasks, command):
        """Dispatch or run for this workflow."""
        self.calls.append((background_tasks, command))
        return {"ok": True}

    async def run_direct(self, *, command):
        """Run direct for this workflow."""
        self.direct_calls.append(command)
        return {"ok": True}


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    class CatalogImportFile:
        """Represent catalog import file and centralize responsibilities for this module."""
        pass


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self, record):
        """Initialize collaborators and configuration required by this component."""
        self.record = record
        self.updated = []

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Return catalog file for user for this workflow."""
        _ = (file_id, user_id)
        return self.record

    def update_catalog_file(self, *, catalog_file):
        """Update catalog file for this workflow."""
        self.updated.append(catalog_file)
        return catalog_file


class _FornecedorRepoStub:
    """Represent fornecedor repo stub and centralize responsibilities for this module."""
    def __init__(self, fornecedor=None):
        """Initialize collaborators and configuration required by this component."""
        self._fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id: int):
        """Return fornecedor for this workflow."""
        _ = fornecedor_id
        return self._fornecedor


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, upload_dir: str, fornecedor=None, finalize_service=None, record=None):
        """Run build service in this workflow."""
        catalog_file_repo = _CatalogFileRepoStub(record)
        service = CatalogImportStartService(
            models=_ModelsStub,
            fornecedor_repo=_FornecedorRepoStub(fornecedor=fornecedor),
            catalog_file_repository=catalog_file_repo,
            settings=SimpleNamespace(UPLOAD_DIRECTORY=upload_dir),
            resolve_storage_path=lambda p: Path(p),
            finalize_service=finalize_service or _FinalizeServiceStub(),
        )
        return service, catalog_file_repo

    def test_get_catalog_file_or_404_success():
        """Run test get catalog file or 404 success in this workflow."""
        record = SimpleNamespace(id=1)
        service, _ = _build_service(upload_dir=".", record=record)
    
        found = service.get_catalog_file_or_404(
            file_id=1,
            user_id=9,
        )
    
        assert found is record

    def test_get_catalog_file_or_404_not_found():
        """Run test get catalog file or 404 not found in this workflow."""
        service, _ = _build_service(upload_dir=".", record=None)
    
        with pytest.raises(HTTPException) as exc:
            service.get_catalog_file_or_404(
                file_id=1,
                user_id=9,
            )
    
        assert exc.value.status_code == 404

    def test_resolve_fornecedor_id_fallback_and_required_error():
        """Run test resolve fornecedor id fallback and required error in this workflow."""
        service, _ = _build_service(upload_dir=".")
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
        """Run test mark processing updates record and commits in this workflow."""
        service, catalog_file_repo = _build_service(upload_dir=".")
        record = SimpleNamespace(status="DONE", fornecedor_id=None, pages_processed=3, total_pages=8)
    
        service.mark_processing(
            catalog_file=record,
            fornecedor_id=11,
            reset_pages=True,
        )
    
        assert record.status == "PROCESSING"
        assert record.fornecedor_id == 11
        assert record.pages_processed == 0
        assert record.total_pages == 0
        assert catalog_file_repo.updated == [record]

    def test_ensure_catalog_binary_exists(tmp_path):
        """Run test ensure catalog binary exists in this workflow."""
        upload_dir = tmp_path / "uploads"
        (upload_dir / "catalogs").mkdir(parents=True)
        file_path = upload_dir / "catalogs" / "ok.pdf"
        file_path.write_text("x", encoding="utf-8")
    
        service, _ = _build_service(upload_dir=str(upload_dir))
        service.ensure_catalog_binary_exists(catalog_file=SimpleNamespace(stored_filename="ok.pdf"))
    
        with pytest.raises(HTTPException) as exc:
            service.ensure_catalog_binary_exists(catalog_file=SimpleNamespace(stored_filename="missing.pdf"))
        assert exc.value.status_code == 404

    def test_resolve_pdf_pages_validates_file_presence_and_extension(tmp_path):
        """Run test resolve pdf pages validates file presence and extension in this workflow."""
        upload_dir = tmp_path / "uploads"
        (upload_dir / "catalogs").mkdir(parents=True)
        service, _ = _build_service(upload_dir=str(upload_dir))
    
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
        """Run test resolve pdf pages returns range from start in this workflow."""
        upload_dir = tmp_path / "uploads"
        (upload_dir / "catalogs").mkdir(parents=True)
        pdf_file = upload_dir / "catalogs" / "catalogo.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 fake")
    
        service, _ = _build_service(upload_dir=str(upload_dir))
        service._count_pdf_pages = lambda _content: 5  # type: ignore[attr-defined]
    
        pages = service.resolve_pdf_pages(
            catalog_file=SimpleNamespace(stored_filename="catalogo.pdf"),
            start_page=3,
        )
    
        assert pages == [3, 4, 5]

    def test_resolve_mapping_prefers_input_then_default():
        """Run test resolve mapping prefers input then default in this workflow."""
        default_mapping = {"col_0": "nome_base"}
        service, _ = _build_service(
            upload_dir=".",
            fornecedor=SimpleNamespace(default_column_mapping=default_mapping),
        )
        assert service.resolve_mapping(
            fornecedor_id=1,
            mapping={"col_1": "sku"},
        ) == {"col_1": "sku"}
        assert service.resolve_mapping(
            fornecedor_id=1,
            mapping=None,
        ) == default_mapping

    @pytest.mark.asyncio
    async def test_dispatch_finalize_calls_finalize_service():
        """Run test dispatch finalize calls finalize service in this workflow."""
        finalize_service = _FinalizeServiceStub()
        service, _ = _build_service(upload_dir=".", finalize_service=finalize_service)
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
            command=command,
        )
    
        assert len(finalize_service.calls) == 1
        _, called_command = finalize_service.calls[0]
        assert called_command.file_id == 3

    @pytest.mark.asyncio
    async def test_run_finalize_direct_calls_finalize_service():
        """Run test run finalize direct calls finalize service in this workflow."""
        finalize_service = _FinalizeServiceStub()
        service, _ = _build_service(upload_dir=".", finalize_service=finalize_service)
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
            command=command,
        )

        assert len(finalize_service.direct_calls) == 1
        called_command = finalize_service.direct_calls[0]
        assert called_command.file_id == 12

_build_service = _TopLevelFunctionSurface._build_service
test_get_catalog_file_or_404_success = _TopLevelFunctionSurface.test_get_catalog_file_or_404_success
test_get_catalog_file_or_404_not_found = _TopLevelFunctionSurface.test_get_catalog_file_or_404_not_found
test_resolve_fornecedor_id_fallback_and_required_error = _TopLevelFunctionSurface.test_resolve_fornecedor_id_fallback_and_required_error
test_mark_processing_updates_record_and_commits = _TopLevelFunctionSurface.test_mark_processing_updates_record_and_commits
test_ensure_catalog_binary_exists = _TopLevelFunctionSurface.test_ensure_catalog_binary_exists
test_resolve_pdf_pages_validates_file_presence_and_extension = _TopLevelFunctionSurface.test_resolve_pdf_pages_validates_file_presence_and_extension
test_resolve_pdf_pages_returns_range_from_start = _TopLevelFunctionSurface.test_resolve_pdf_pages_returns_range_from_start
test_resolve_mapping_prefers_input_then_default = _TopLevelFunctionSurface.test_resolve_mapping_prefers_input_then_default
test_dispatch_finalize_calls_finalize_service = _TopLevelFunctionSurface.test_dispatch_finalize_calls_finalize_service
test_run_finalize_direct_calls_finalize_service = _TopLevelFunctionSurface.test_run_finalize_direct_calls_finalize_service




















