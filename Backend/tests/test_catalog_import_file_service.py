"""Module test catalog import file service.

Contains backend logic related to test catalog import file service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace
import asyncio

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_file_service import (
    CatalogImportFileService,
)


class _CatalogImportFileModel:
    """Represent catalog import file model and centralize responsibilities for this module."""
    user_id = object()
    fornecedor_id = object()
    created_at = SimpleNamespace(desc=lambda: object())


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    CatalogImportFile = _CatalogImportFileModel


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self, *, items=None, first_record=None):
        """Initialize collaborators and configuration required by this component."""
        self._items = items or []
        self._first_record = first_record
        self.deleted = []

    def list_catalog_files_for_user(self, *, user_id: int, fornecedor_id: int | None, skip: int, limit: int):
        """List catalog files for user for this workflow."""
        _ = (user_id, fornecedor_id, skip, limit)
        return self._items, len(self._items)

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Return catalog file for user for this workflow."""
        _ = (file_id, user_id)
        return self._first_record

    def delete_catalog_file(self, *, catalog_file):
        """Delete catalog file for this workflow."""
        self.deleted.append(catalog_file)
        return None


class _FileProcessingStub:
    """Represent file processing stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.deleted_files = []

    def delete_catalog_file(self, stored_filename):
        """Delete catalog file for this workflow."""
        self.deleted_files.append(stored_filename)


class _CatalogImportStartServiceStub:
    """Represent catalog import start service stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []
        self.catalog_file = SimpleNamespace(id=77, fornecedor_id=3)

    def get_catalog_file_or_404(self, **kwargs):
        """Return catalog file or 404 for this workflow."""
        self.calls.append(("get_catalog_file_or_404", kwargs))
        return self.catalog_file

    def resolve_fornecedor_id(self, **kwargs):
        """Resolve fornecedor id for this workflow."""
        self.calls.append(("resolve_fornecedor_id", kwargs))
        return kwargs.get("fornecedor_id") or self.catalog_file.fornecedor_id

    def mark_processing(self, **kwargs):
        """Mark processing for this workflow."""
        self.calls.append(("mark_processing", kwargs))

    def resolve_mapping(self, **kwargs):
        """Resolve mapping for this workflow."""
        self.calls.append(("resolve_mapping", kwargs))
        return kwargs.get("mapping") or {"col_0": "nome_base"}

    def build_finalize_command(self, **kwargs):
        """Build finalize command for this workflow."""
        self.calls.append(("build_finalize_command", kwargs))
        return SimpleNamespace(**kwargs)

    async def dispatch_finalize(self, **kwargs):
        """Dispatch finalize for this workflow."""
        self.calls.append(("dispatch_finalize", kwargs))


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, catalog_file_repo=None, fornecedor_repo=None):
        """Run build service in this workflow."""
        file_processing = _FileProcessingStub()
        start_service = _CatalogImportStartServiceStub()
        catalog_file_repo = catalog_file_repo or _CatalogFileRepoStub()
        fornecedor_repo = fornecedor_repo or object()
        service = CatalogImportFileService(
            models=_ModelsStub,
            file_processing_service=file_processing,
            catalog_import_start_service=start_service,
            catalog_file_repository=catalog_file_repo,
            fornecedor_repository=fornecedor_repo,
        )
        return service, file_processing, start_service, catalog_file_repo, fornecedor_repo

    def test_list_user_files_builds_page_payload():
        """Run test list user files builds page payload in this workflow."""
        repo = _CatalogFileRepoStub(items=[SimpleNamespace(id=1), SimpleNamespace(id=2)])
        service, _, _, _, _ = _build_service(catalog_file_repo=repo)
    
        payload = service.list_user_files(
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
        """Run test get user file or 404 raises when missing in this workflow."""
        repo = _CatalogFileRepoStub(first_record=None)
        service, _, _, _, _ = _build_service(catalog_file_repo=repo)
    
        with pytest.raises(HTTPException) as exc:
            service.get_user_file_or_404(file_id=7, user_id=10)
    
        assert exc.value.status_code == 404

    def test_delete_user_file_deletes_binary_and_record():
        """Run test delete user file deletes binary and record in this workflow."""
        record = SimpleNamespace(id=7, stored_filename="abc.pdf")
        repo = _CatalogFileRepoStub(first_record=record)
        service, file_processing, _, _, _ = _build_service(catalog_file_repo=repo)
    
        deleted = service.delete_user_file(file_id=7, user_id=10)
    
        assert deleted is record
        assert file_processing.deleted_files == ["abc.pdf"]
        assert repo.deleted == [record]

    def test_reprocess_catalog_file_dispatches_finalize():
        """Run test reprocess catalog file dispatches finalize in this workflow."""
        catalog_repo = _CatalogFileRepoStub(first_record=SimpleNamespace(id=99))
        service, _, start_service, _, _ = _build_service(
            catalog_file_repo=catalog_repo,
            fornecedor_repo=object(),
        )
    
        payload = asyncio.run(
            service.reprocess_catalog_file(
                background_tasks=object(),
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

_build_service = _TopLevelFunctionSurface._build_service
test_list_user_files_builds_page_payload = _TopLevelFunctionSurface.test_list_user_files_builds_page_payload
test_get_user_file_or_404_raises_when_missing = _TopLevelFunctionSurface.test_get_user_file_or_404_raises_when_missing
test_delete_user_file_deletes_binary_and_record = _TopLevelFunctionSurface.test_delete_user_file_deletes_binary_and_record
test_reprocess_catalog_file_dispatches_finalize = _TopLevelFunctionSurface.test_reprocess_catalog_file_dispatches_finalize








