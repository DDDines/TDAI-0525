"""Module test fornecedor catalog process service.

Contains backend logic related to test fornecedor catalog process service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_catalog_process_service import (
    FornecedorCatalogProcessService,
)


class _CrudFornecedoresStub:
    """Represent crud fornecedores stub and centralize responsibilities for this module."""
    def __init__(self, fornecedor):
        """Initialize collaborators and configuration required by this component."""
        self._fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id):
        """Return fornecedor for this workflow."""
        _ = fornecedor_id
        return self._fornecedor


class _CatalogImportStartServiceStub:
    """Represent catalog import start service stub and centralize responsibilities for this module."""
    def __init__(self, source):
        """Initialize collaborators and configuration required by this component."""
        self._source = source
        self.dispatched = []
        self.commands = []
        self.marked = []
        self.ensure_calls = []

    def get_catalog_file_or_404(self, **kwargs):
        """Return catalog file or 404 for this workflow."""
        _ = kwargs
        return self._source

    def mark_processing(self, **kwargs):
        """Capture mark_processing calls for this workflow."""
        self.marked.append(kwargs)

    def ensure_catalog_binary_exists(self, **kwargs):
        """Capture ensure_catalog_binary_exists calls for this workflow."""
        self.ensure_calls.append(kwargs)

    def resolve_pdf_pages(self, *, catalog_file, start_page):
        """Resolve pdf pages for this workflow."""
        _ = catalog_file
        return [start_page, start_page + 1]

    def resolve_mapping(self, **kwargs):
        """Resolve mapping for this workflow."""
        _ = kwargs
        return kwargs.get("mapping") or {"col_0": "nome_base"}

    def build_finalize_command(self, **kwargs):
        """Build finalize command for this workflow."""
        self.commands.append(kwargs)
        return SimpleNamespace(**kwargs)

    async def dispatch_finalize(self, **kwargs):
        """Dispatch finalize for this workflow."""
        self.dispatched.append(kwargs)
        return {"ok": True}


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, fornecedor, source):
        """Run build service in this workflow."""
        fornecedor_repo = _CrudFornecedoresStub(fornecedor=fornecedor)
        service = FornecedorCatalogProcessService(
            fornecedor_repo=fornecedor_repo,
            catalog_import_start_service=_CatalogImportStartServiceStub(source=source),
        )
        return service, fornecedor_repo

    @pytest.mark.asyncio
    async def test_start_full_processing_dispatches_job():
        """Run test start full processing dispatches job in this workflow."""
        fornecedor = SimpleNamespace(id=3, user_id=10)
        source = SimpleNamespace(id=900, original_filename="orig.pdf", stored_filename="stored.pdf")
        service, fornecedor_repo = _build_service(
            fornecedor=fornecedor,
            source=source,
        )
        user = SimpleNamespace(id=10, is_superuser=False)
    
        result = await service.start_full_processing(
            background_tasks=object(),
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
    
        start_stub = service._catalog_import_start_service
        assert len(start_stub.marked) == 1
        assert start_stub.marked[0]["catalog_file"] is source
        assert start_stub.marked[0]["fornecedor_id"] == 3
        assert len(start_stub.ensure_calls) == 1
        assert len(start_stub.dispatched) == 1
        assert len(start_stub.commands) == 1
        command_data = start_stub.commands[0]
        assert command_data["file_id"] == 900
        assert command_data["product_type_id"] == 7
        assert command_data["pages"] == [4, 5]

    @pytest.mark.asyncio
    async def test_start_full_processing_raises_when_fornecedor_not_found():
        """Run test start full processing raises when fornecedor not found in this workflow."""
        source = SimpleNamespace(id=900, original_filename="orig.pdf", stored_filename="stored.pdf")
        service, fornecedor_repo = _build_service(
            fornecedor=None,
            source=source,
        )
    
        with pytest.raises(HTTPException) as exc:
            await service.start_full_processing(
                background_tasks=object(),
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
        """Run test start full processing raises when user not allowed in this workflow."""
        fornecedor = SimpleNamespace(id=3, user_id=99)
        source = SimpleNamespace(id=900, original_filename="orig.pdf", stored_filename="stored.pdf")
        service, fornecedor_repo = _build_service(
            fornecedor=fornecedor,
            source=source,
        )
    
        with pytest.raises(HTTPException) as exc:
            await service.start_full_processing(
                background_tasks=object(),
                current_user=SimpleNamespace(id=1, is_superuser=False),
                file_id=1,
                fornecedor_id=3,
                tipo_produto_id=1,
                start_page=1,
                region=None,
                mapping=None,
            )
    
        assert exc.value.status_code == 403

_build_service = _TopLevelFunctionSurface._build_service
test_start_full_processing_dispatches_job = _TopLevelFunctionSurface.test_start_full_processing_dispatches_job
test_start_full_processing_raises_when_fornecedor_not_found = _TopLevelFunctionSurface.test_start_full_processing_raises_when_fornecedor_not_found
test_start_full_processing_raises_when_user_not_allowed = _TopLevelFunctionSurface.test_start_full_processing_raises_when_user_not_allowed






