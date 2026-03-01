from __future__ import annotations

import asyncio
from types import SimpleNamespace

from Backend.application.services.catalog_import_workflow_service import (
    CatalogImportWorkflowService,
)


class _StartServiceStub:
    def __init__(self):
        self.calls = []
        self.record = SimpleNamespace(fornecedor_id=3, result_summary={"created": 1})

    def get_catalog_file_or_404(self, **kwargs):
        self.calls.append(("get", kwargs))
        return self.record

    def mark_processing(self, **kwargs):
        self.calls.append(("mark", kwargs))

    def ensure_catalog_binary_exists(self, **kwargs):
        self.calls.append(("ensure", kwargs))

    def resolve_mapping(self, **kwargs):
        self.calls.append(("resolve_mapping", kwargs))
        return kwargs.get("mapping") or {"col_1": "Nome Base"}

    def build_finalize_command(self, **kwargs):
        self.calls.append(("build", kwargs))
        return {"command": kwargs}

    async def dispatch_finalize(self, **kwargs):
        self.calls.append(("dispatch", kwargs))

    def resolve_fornecedor_id(self, **kwargs):
        self.calls.append(("resolve_fornecedor", kwargs))
        return kwargs["fornecedor_id"]

    def resolve_pdf_pages(self, **kwargs):
        self.calls.append(("resolve_pages", kwargs))
        return [1, 2, 3]

    async def run_finalize_direct(self, **kwargs):
        self.calls.append(("run_direct", kwargs))


class _StatusServiceStub:
    def __init__(self):
        self.calls = []
        self.record = SimpleNamespace(status="DONE", result_summary={"ok": True})

    def get_record_or_404(self, **kwargs):
        self.calls.append(("get", kwargs))
        return self.record

    def build_simple_status(self, **kwargs):
        self.calls.append(("simple", kwargs))
        return {"status": "DONE", "result_ready": True}

    def build_result_response(self, **kwargs):
        self.calls.append(("result", kwargs))
        return {"created": 1}


class _TopLevelFunctionSurface:

    def test_importar_catalogo_finalizar_dispatches_and_returns_processing():
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
        start = _StartServiceStub()
        status = _StatusServiceStub()
        service = CatalogImportWorkflowService(start_service=start, status_service=status)
    
        detailed = service.importar_catalogo_status(file_id=1, user_id=2)
        simple = service.importar_catalogo_status_simple(file_id=1, user_id=2)
        result = service.importar_catalogo_result(file_id=1, user_id=2)
    
        assert detailed.status == "DONE"
        assert simple["result_ready"] is True
        assert result["created"] == 1

    def test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes():
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
    
        assert result == {"created": 1}
        assert any(call[0] == "run_direct" for call in start.calls)

test_importar_catalogo_finalizar_dispatches_and_returns_processing = _TopLevelFunctionSurface.test_importar_catalogo_finalizar_dispatches_and_returns_processing
test_importar_catalogo_status_and_result_delegate_to_status_service = _TopLevelFunctionSurface.test_importar_catalogo_status_and_result_delegate_to_status_service
test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes = _TopLevelFunctionSurface.test_importar_catalogo_finalizar_todas_paginas_runs_direct_and_refreshes




