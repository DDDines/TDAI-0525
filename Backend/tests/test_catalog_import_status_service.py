"""Module test catalog import status service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
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
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    class CatalogImportFile:
        """Class CatalogImportFile.

        Encapsulates one responsibility in the backend architecture.
        """
        pass


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


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(record=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        repo = _CatalogFileRepoStub(record)
        service = CatalogImportStatusService(
            models=_ModelsStub,
            catalog_file_repository=repo,
        )
        return service, repo

    def test_get_record_or_404_returns_record():
        """Execute test_get_record_or_404_returns_record.

        This callable is documented to make behavior explicit for readers.
        """
        record = SimpleNamespace(id=10)
        service, _ = _build_service(record=record)
    
        found = service.get_record_or_404(file_id=10, user_id=1)
    
        assert found is record

    def test_get_record_or_404_raises_404_when_missing():
        """Execute test_get_record_or_404_raises_404_when_missing.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_build_simple_status_maps_status.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_build_simple_status_sets_result_ready_for_terminal_with_summary.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_build_result_response_returns_pending_jsonresponse.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service()
        record = SimpleNamespace(status="PROCESSING", result_summary=None)
    
        response = service.build_result_response(record=record)
    
        assert isinstance(response, JSONResponse)
        assert response.status_code == 202
        data = json.loads(response.body.decode("utf-8"))
        assert data["ready"] is False
        assert data["status"] == "PROCESSING"

    def test_build_result_response_returns_result_summary_when_ready():
        """Execute test_build_result_response_returns_result_summary_when_ready.

        This callable is documented to make behavior explicit for readers.
        """
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












