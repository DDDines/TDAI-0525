from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import JSONResponse

from Backend.application.services.catalog_import_status_service import (
    CatalogImportStatusService,
)


class _QueryStub:
    def __init__(self, record):
        self._record = record

    def filter_by(self, **kwargs):
        _ = kwargs
        return self

    def first(self):
        return self._record


class _DbStub:
    def __init__(self, record):
        self._record = record

    def query(self, model):
        _ = model
        return _QueryStub(self._record)


class _ModelsStub:
    class CatalogImportFile:
        pass


def _build_service():
    return CatalogImportStatusService(models=_ModelsStub)


def test_get_record_or_404_returns_record():
    record = SimpleNamespace(id=10)
    service = _build_service()

    found = service.get_record_or_404(db=_DbStub(record), file_id=10, user_id=1)

    assert found is record


def test_get_record_or_404_raises_404_when_missing():
    service = _build_service()

    with pytest.raises(HTTPException) as exc:
        service.get_record_or_404(db=_DbStub(None), file_id=10, user_id=1)

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
    service = _build_service()
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
    service = _build_service()
    record = SimpleNamespace(
        status="FAILED",
        total_pages=5,
        pages_processed=5,
        result_summary={"errors": []},
    )

    payload = service.build_simple_status(record=record)

    assert payload["result_ready"] is True


def test_build_result_response_returns_pending_jsonresponse():
    service = _build_service()
    record = SimpleNamespace(status="PROCESSING", result_summary=None)

    response = service.build_result_response(record=record)

    assert isinstance(response, JSONResponse)
    assert response.status_code == 202
    data = json.loads(response.body.decode("utf-8"))
    assert data["ready"] is False
    assert data["status"] == "PROCESSING"


def test_build_result_response_returns_result_summary_when_ready():
    service = _build_service()
    summary = {"created": [], "updated": [], "errors": []}
    record = SimpleNamespace(status="DONE", result_summary=summary)

    response = service.build_result_response(record=record)

    assert response == summary
