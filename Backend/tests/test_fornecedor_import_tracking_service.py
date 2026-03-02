"""Module test fornecedor import tracking service.

Contains backend logic related to test fornecedor import tracking service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_tracking_service import (
    FornecedorImportTrackingService,
)


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self, record):
        """Initialize collaborators and configuration required by this component."""
        self._record = record

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Return catalog file for user for this workflow."""
        _ = (file_id, user_id)
        return self._record


class _BackgroundTasksStub:
    """Represent background tasks stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def add_task(self, task, **kwargs):
        """Run add task in this workflow."""
        self.calls.append((task, kwargs))


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    class CatalogImportFile:
        """Represent catalog import file and centralize responsibilities for this module."""
        pass


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, record=None):
        """Run build service in this workflow."""
        return FornecedorImportTrackingService(
            models=_ModelsStub,
            process_pdf_extraction_task=lambda **kwargs: kwargs,
            catalog_file_repository=_CatalogFileRepoStub(record),
        )

    def test_get_catalog_record_or_404_returns_record():
        """Run test get catalog record or 404 returns record in this workflow."""
        record = SimpleNamespace(id=1)
        service = _build_service(record=record)
    
        found = service.get_catalog_record_or_404(
            file_id=1,
            user_id=9,
            not_found_detail="arquivo nao encontrado",
        )
    
        assert found is record

    def test_get_catalog_record_or_404_raises_when_missing():
        """Run test get catalog record or 404 raises when missing in this workflow."""
        service = _build_service(record=None)
    
        with pytest.raises(HTTPException) as exc:
            service.get_catalog_record_or_404(
                file_id=1,
                user_id=9,
                not_found_detail="arquivo nao encontrado",
            )
    
        assert exc.value.status_code == 404
        assert exc.value.detail == "arquivo nao encontrado"

    def test_build_progress_payload_normalizes_total_pages():
        """Run test build progress payload normalizes total pages in this workflow."""
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
        """Run test schedule page extraction adds task in this workflow."""
        service = _build_service()
        background = _BackgroundTasksStub()
    
        service.schedule_page_extraction(
            background_tasks=background,
            import_job_id=100,
            page_number=5,
        )
    
        assert len(background.calls) == 1
        _, kwargs = background.calls[0]
        assert kwargs["import_job_id"] == 100
        assert kwargs["page_number"] == 5
        assert "db_url" not in kwargs

    def test_build_import_job_status_payload_includes_result_for_completed():
        """Run test build import job status payload includes result for completed in this workflow."""
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










