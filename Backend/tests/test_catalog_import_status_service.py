"""Module test catalog import status service.

Contains backend logic related to test catalog import status service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from Backend.application.services.catalog_import_status_service import (
    CatalogImportStatusService,
)


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    class CatalogImportFile:
        """Represent catalog import file and centralize responsibilities for this module."""
        pass


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self, record):
        """Initialize collaborators and configuration required by this component."""
        self._record = record

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Return catalog file for user for this workflow."""
        _ = (file_id, user_id)
        return self._record


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(record=None):
        """Run build service in this workflow."""
        repo = _CatalogFileRepoStub(record)
        service = CatalogImportStatusService(
            models=_ModelsStub,
            catalog_file_repository=repo,
        )
        return service, repo

    def test_get_record_or_404_returns_record():
        """Run test get record or 404 returns record in this workflow."""
        record = SimpleNamespace(id=10)
        service, _ = _build_service(record=record)
    
        found = service.get_record_or_404(file_id=10, user_id=1)
    
        assert found is record

    def test_get_record_or_404_raises_404_when_missing():
        """Run test get record or 404 raises 404 when missing in this workflow."""
        service, _ = _build_service(record=None)
    
        with pytest.raises(HTTPException) as exc:
            service.get_record_or_404(file_id=10, user_id=1)
    
        assert exc.value.status_code == 404

    @pytest.mark.parametrize(
        ("raw_status", "expected_status"),
        [
            ("IMPORTED", "DONE"),
            ("DONE", "DONE"),
            ("PARTIAL", "PARTIAL"),
            ("FAILED", "FAILED"),
            ("PROCESSING", "PROCESSING"),
            (None, "PROCESSING"),
        ],
    )
    def test_build_simple_status_maps_status(raw_status, expected_status):
        """Run test build simple status maps status in this workflow."""
        service, _ = _build_service()
        record = SimpleNamespace(
            status=raw_status,
            total_pages=9,
            pages_processed=4,
            result_summary=None,
        )
    
        payload = service.build_simple_status(record=record)
    
        assert payload["status"] == expected_status
        assert payload["pages_total"] == 9
        assert payload["pages_processed"] == 4
        assert payload["result_ready"] is False

    def test_build_simple_status_sets_result_ready_for_terminal_with_summary():
        """Run test build simple status sets result ready for terminal with summary in this workflow."""
        service, _ = _build_service()
        record = SimpleNamespace(
            status="FAILED",
            total_pages=5,
            pages_processed=5,
            result_summary={"errors": []},
        )
    
        payload = service.build_simple_status(record=record)
    
        assert payload["result_ready"] is True

    def test_build_result_response_returns_pending_jsonresponse():
        """Run test build result response returns pending jsonresponse in this workflow."""
        service, _ = _build_service()
        record = SimpleNamespace(status="PROCESSING", result_summary=None)
    
        response = service.build_result_response(record=record)
    
        assert isinstance(response, JSONResponse)
        assert response.status_code == 202
        data = json.loads(response.body.decode("utf-8"))
        assert data["ready"] is False
        assert data["status"] == "PROCESSING"

    def test_build_result_response_returns_result_summary_when_ready():
        """Run test build result response returns result summary when ready in this workflow."""
        service, _ = _build_service()
        summary = {"created": [], "updated": [], "errors": []}
        record = SimpleNamespace(status="DONE", result_summary=summary)
    
        response = service.build_result_response(record=record)
    
        assert response == summary

_build_service = _TopLevelFunctionSurface._build_service
test_get_record_or_404_returns_record = _TopLevelFunctionSurface.test_get_record_or_404_returns_record
test_get_record_or_404_raises_404_when_missing = _TopLevelFunctionSurface.test_get_record_or_404_raises_404_when_missing
test_build_simple_status_maps_status = _TopLevelFunctionSurface.test_build_simple_status_maps_status
test_build_simple_status_sets_result_ready_for_terminal_with_summary = _TopLevelFunctionSurface.test_build_simple_status_sets_result_ready_for_terminal_with_summary
test_build_result_response_returns_pending_jsonresponse = _TopLevelFunctionSurface.test_build_result_response_returns_pending_jsonresponse
test_build_result_response_returns_result_summary_when_ready = _TopLevelFunctionSurface.test_build_result_response_returns_result_summary_when_ready












