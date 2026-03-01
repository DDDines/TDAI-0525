from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_tracking_service import (
    FornecedorImportTrackingService,
)


class _CatalogFileRepoStub:
    def __init__(self, record):
        self._record = record

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        _ = (file_id, user_id)
        return self._record


class _BackgroundTasksStub:
    def __init__(self):
        self.calls = []

    def add_task(self, task, **kwargs):
        self.calls.append((task, kwargs))


class _ModelsStub:
    class CatalogImportFile:
        pass


class _TopLevelFunctionSurface:

    def _build_service():
        return FornecedorImportTrackingService(
            models=_ModelsStub,
            process_pdf_extraction_task=lambda **kwargs: kwargs,
        )

    def test_get_catalog_record_or_404_returns_record():
        service = _build_service()
        record = SimpleNamespace(id=1)
    
        found = service.get_catalog_record_or_404(
            catalog_file_repo=_CatalogFileRepoStub(record),
            file_id=1,
            user_id=9,
            not_found_detail="arquivo nao encontrado",
        )
    
        assert found is record

    def test_get_catalog_record_or_404_raises_when_missing():
        service = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            service.get_catalog_record_or_404(
                catalog_file_repo=_CatalogFileRepoStub(None),
                file_id=1,
                user_id=9,
                not_found_detail="arquivo nao encontrado",
            )
    
        assert exc.value.status_code == 404
        assert exc.value.detail == "arquivo nao encontrado"

    def test_build_progress_payload_normalizes_total_pages():
        payload = FornecedorImportTrackingService.build_progress_payload(
            record=SimpleNamespace(status="PROCESSING", pages_processed=4, total_pages=None)
        )
    
        assert payload == {
            "status": "PROCESSING",
            "progress": 4,
            "pages_processed": 4,
            "total_pages": 0,
        }

    def test_schedule_page_extraction_adds_task():
        service = _build_service()
        background = _BackgroundTasksStub()
    
        service.schedule_page_extraction(
            background_tasks=background,
            import_job_id=100,
            page_number=5,
            db_url="postgresql://localhost/db",
        )
    
        assert len(background.calls) == 1
        _, kwargs = background.calls[0]
        assert kwargs["import_job_id"] == 100
        assert kwargs["page_number"] == 5

    def test_build_import_job_status_payload_includes_result_for_completed():
        record = SimpleNamespace(status="COMPLETED", resultado_json={"ok": True})
    
        payload = FornecedorImportTrackingService.build_import_job_status_payload(
            record=record
        )
    
        assert payload == {"status": "COMPLETED", "resultado_json": {"ok": True}}

_build_service = _TopLevelFunctionSurface._build_service
test_get_catalog_record_or_404_returns_record = _TopLevelFunctionSurface.test_get_catalog_record_or_404_returns_record
test_get_catalog_record_or_404_raises_when_missing = _TopLevelFunctionSurface.test_get_catalog_record_or_404_raises_when_missing
test_build_progress_payload_normalizes_total_pages = _TopLevelFunctionSurface.test_build_progress_payload_normalizes_total_pages
test_schedule_page_extraction_adds_task = _TopLevelFunctionSurface.test_schedule_page_extraction_adds_task
test_build_import_job_status_payload_includes_result_for_completed = _TopLevelFunctionSurface.test_build_import_job_status_payload_includes_result_for_completed










