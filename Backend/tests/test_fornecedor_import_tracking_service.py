"""Module test fornecedor import tracking service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_import_tracking_service import (
    FornecedorImportTrackingService,
)


class _CatalogFileRepoStub:
    """Class _CatalogFileRepoStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, record):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._record = record

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Execute get_catalog_file_for_user.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (file_id, user_id)
        return self._record


class _BackgroundTasksStub:
    """Class _BackgroundTasksStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def add_task(self, task, **kwargs):
        """Execute add_task.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append((task, kwargs))


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    class CatalogImportFile:
        """Class CatalogImportFile.

        Encapsulates one responsibility in the backend architecture.
        """
        pass


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(*, record=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        return FornecedorImportTrackingService(
            models=_ModelsStub,
            process_pdf_extraction_task=lambda **kwargs: kwargs,
            catalog_file_repository=_CatalogFileRepoStub(record),
        )

    def test_get_catalog_record_or_404_returns_record():
        """Execute test_get_catalog_record_or_404_returns_record.

        This callable is documented to make behavior explicit for readers.
        """
        record = SimpleNamespace(id=1)
        service = _build_service(record=record)
    
        found = service.get_catalog_record_or_404(
            file_id=1,
            user_id=9,
            not_found_detail="arquivo nao encontrado",
        )
    
        assert found is record

    def test_get_catalog_record_or_404_raises_when_missing():
        """Execute test_get_catalog_record_or_404_raises_when_missing.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_build_progress_payload_normalizes_total_pages.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_schedule_page_extraction_adds_task.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_build_import_job_status_payload_includes_result_for_completed.

        This callable is documented to make behavior explicit for readers.
        """
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










