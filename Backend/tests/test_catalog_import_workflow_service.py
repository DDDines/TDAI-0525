"""Module test catalog import workflow service.

Contains backend logic related to test catalog import workflow service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

from Backend.application.services.catalog_import_workflow_service import (
    CatalogImportWorkflowService,
)


class _StartServiceStub:
    """Represent start service stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []
        self.record = SimpleNamespace(fornecedor_id=3, result_summary={"created": 1})

    def get_catalog_file_or_404(self, **kwargs):
        """Return catalog file or 404 for this workflow."""
        self.calls.append(("get", kwargs))
        return self.record

    def mark_processing(self, **kwargs):
        """Mark processing for this workflow."""
        self.calls.append(("mark", kwargs))

    def ensure_catalog_binary_exists(self, **kwargs):
        """Ensure catalog binary exists for this workflow."""
        self.calls.append(("ensure", kwargs))

    def resolve_mapping(self, **kwargs):
        """Resolve mapping for this workflow."""
        self.calls.append(("resolve_mapping", kwargs))
        return kwargs.get("mapping") or {"col_1": "Nome Base"}

    def build_finalize_command(self, **kwargs):
        """Build finalize command for this workflow."""
        self.calls.append(("build", kwargs))
        return {"command": kwargs}

    async def dispatch_finalize(self, **kwargs):
        """Dispatch finalize for this workflow."""
        self.calls.append(("dispatch", kwargs))

    def resolve_fornecedor_id(self, **kwargs):
        """Resolve fornecedor id for this workflow."""
        self.calls.append(("resolve_fornecedor", kwargs))
        return kwargs["fornecedor_id"]

    def resolve_pdf_pages(self, **kwargs):
        """Resolve pdf pages for this workflow."""
        self.calls.append(("resolve_pages", kwargs))
        return [1, 2, 3]

    async def run_finalize_direct(self, **kwargs):
        """Run finalize direct for this workflow."""
        self.calls.append(("run_direct", kwargs))


class _StatusServiceStub:
    """Represent status service stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []
        self.record = SimpleNamespace(status="DONE", result_summary={"ok": True})

    def get_record_or_404(self, **kwargs):
        """Return record or 404 for this workflow."""
        self.calls.append(("get", kwargs))
        return self.record

    def build_simple_status(self, **kwargs):
        """Build simple status for this workflow."""
        self.calls.append(("simple", kwargs))
        return {"status": "DONE", "result_ready": True}

    def build_result_response(self, **kwargs):
        """Build result response for this workflow."""
        self.calls.append(("result", kwargs))
        return {"created": 1}


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_importar_catalogo_finalizar_dispatches_and_returns_processing():
        """Run test importar catalogo finalizar dispatches and returns processing in this workflow."""
        start = _StartServiceStub()
        status = _StatusServiceStub()
        service = CatalogImportWorkflowService(start_service=start, status_service=status)
    
        result = asyncio.run(
            service.importar_catalogo_finalizar(
                background_tasks=object(),
                file_id=10,
                product_type_id=4,
                fornecedor_id=3,
                mapping=None,
                pages=[12],
                region=[0.1, 0.1, 0.9, 0.9],
                user_id=99,
            )
        )
    
        assert result == {"status": "PROCESSING", "file_id": 10}
        assert any(call[0] == "dispatch" for call in start.calls)

    def test_importar_catalogo_status_and_result_delegate_to_status_service():
        """Run test importar catalogo status and result delegate to status service in this workflow."""
        start = _StartServiceStub()
        status = _StatusServiceStub()
        service = CatalogImportWorkflowService(start_service=start, status_service=status)
    
        detailed = service.importar_catalogo_status(
            file_id=1,
            user_id=2,
        )
        simple = service.importar_catalogo_status_simple(
            file_id=1,
            user_id=2,
        )
        result = service.importar_catalogo_result(
            file_id=1,
            user_id=2,
        )
    
        assert detailed.status == "DONE"
        assert simple["result_ready"] is True
        assert result["created"] == 1

    def test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes():
        """Run test importar catalogo finalizar todas paginas runs direct and refreshes in this workflow."""
        start = _StartServiceStub()
        status = _StatusServiceStub()
        service = CatalogImportWorkflowService(start_service=start, status_service=status)
    
        result = asyncio.run(
            service.importar_catalogo_finalizar_todas_paginas(
                file_id=20,
                start_page=2,
                mapping={"col_0": "Nome Base"},
                user_id=5,
            )
        )
    
        assert result == {"ok": True}
        assert any(call[0] == "run_direct" for call in start.calls)

test_importar_catalogo_finalizar_dispatches_and_returns_processing = _TopLevelFunctionSurface.test_importar_catalogo_finalizar_dispatches_and_returns_processing
test_importar_catalogo_status_and_result_delegate_to_status_service = _TopLevelFunctionSurface.test_importar_catalogo_status_and_result_delegate_to_status_service
test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes = _TopLevelFunctionSurface.test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes




