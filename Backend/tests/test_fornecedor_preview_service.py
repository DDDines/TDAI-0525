"""Module test fornecedor preview service.

Contains backend logic related to test fornecedor preview service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace
import asyncio

import pytest
from fastapi import HTTPException

import Backend.application.services.fornecedor_preview_service as preview_module
from Backend.application.services.fornecedor_preview_service import (
    FornecedorPreviewService,
)


class _FileProcessingStub:
    """Represent file processing stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.generate_calls = []
        self.preview_calls = []
        self.extract_calls = []
        self._file_path = "/tmp/catalog.pdf"
        self._df = None

    def generate_pdf_page_images(self, path, file_id):
        """Run generate pdf page images in this workflow."""
        self.generate_calls.append((path, file_id))
        return ["img://1", "img://2"]

    def pdf_pages_to_images(self, **kwargs):
        """Run pdf pages to images in this workflow."""
        self.preview_calls.append(kwargs)
        return {"pages": [{"page_number": 1}]}

    def get_file_path_by_id(self, db, file_id):
        """Return file path by id for this workflow."""
        _ = (db, file_id)
        return self._file_path

    def extract_pdf_region_image(self, **kwargs):
        """Extract pdf region image for this workflow."""
        self.extract_calls.append(kwargs)
        return b"fake-bytes"

    def parse_annotation_to_dataframe(self, annotation):
        """Parse annotation to dataframe for this workflow."""
        _ = annotation
        return self._df

    def extract_data_from_pdf_region(self, **kwargs):
        """Extract data from pdf region for this workflow."""
        _ = kwargs


class _WebExtractorStub:
    """Represent web extractor stub and centralize responsibilities for this module."""
    def extract_text_from_image_region(self, image_bytes):
        """Extract text from image region for this workflow."""
        _ = image_bytes
        return "annotated"


class _UploadFileStub:
    """Represent upload file stub and centralize responsibilities for this module."""
    def __init__(self, filename: str, payload: bytes = b"pdf"):
        """Initialize collaborators and configuration required by this component."""
        self.filename = filename
        self._payload = payload

    async def read(self):
        """Run read in this workflow."""
        return self._payload


class _DataFrameStub:
    """Represent data frame stub and centralize responsibilities for this module."""
    def __init__(self, *, empty: bool, columns=None, rows=None):
        """Initialize collaborators and configuration required by this component."""
        self.empty = empty
        self._columns = columns or []
        self._rows = rows or []

    @property
    def columns(self):
        """Run columns in this workflow."""
        return SimpleNamespace(astype=lambda _type: SimpleNamespace(tolist=lambda: self._columns))

    def head(self, _limit):
        """Run head in this workflow."""
        return self

    def to_dict(self, orient):
        """Run to dict in this workflow."""
        _ = orient
        return self._rows


class _BackgroundTasksStub:
    """Represent background tasks stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def add_task(self, fn, **kwargs):
        """Run add task in this workflow."""
        self.calls.append((fn, kwargs))


class _DispatcherStub:
    """Represent dispatcher stub and centralize responsibilities for this module."""

    def __init__(self, *, use_celery: bool):
        """Initialize collaborators and configuration required by this component."""
        self._use_celery = use_celery
        self.named_calls = []

    def dispatch_named_or_background(self, *, background_tasks, task_name, task_kwargs, fallback_callable):
        """Capture Celery dispatches and mirror background fallback behavior."""
        if self._use_celery:
            self.named_calls.append((task_name, task_kwargs))
            return "async-result"
        background_tasks.add_task(fallback_callable, **task_kwargs)
        return None


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self._db = object()


class _PdfStub:
    """Represent pdf stub and centralize responsibilities for this module."""
    def __init__(self, pages_count):
        """Initialize collaborators and configuration required by this component."""
        self.pages = [object() for _ in range(pages_count)]

    def __enter__(self):
        """Run enter in this workflow."""
        return self

    def __exit__(self, exc_type, exc, tb):
        """Run exit in this workflow."""
        _ = (exc_type, exc, tb)
        return False


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, dispatcher_cls=None):
        """Run build service in this workflow."""
        file_processing = _FileProcessingStub()
        catalog_repo = _CatalogFileRepoStub()
        service = FornecedorPreviewService(
            file_processing_service=file_processing,
            web_data_extractor_service=_WebExtractorStub(),
            catalog_file_repository=catalog_repo,
            dispatcher_cls=dispatcher_cls or (lambda: _DispatcherStub(use_celery=False)),
        )
        return service, file_processing, catalog_repo

    def test_preview_pages_rejects_non_pdf():
        """Run test preview pages rejects non pdf in this workflow."""
        service, _, _ = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(service.preview_pages(file=_UploadFileStub("catalog.csv")))
    
        assert exc.value.status_code == 400

    def test_preview_pages_generates_images():
        """Run test preview pages generates images in this workflow."""
        service, file_processing, _ = _build_service()
    
        payload = asyncio.run(
            service.preview_pages(file=_UploadFileStub("catalog.pdf", b"payload"))
        )
    
        assert payload["file_id"]
        assert payload["page_image_urls"] == ["img://1", "img://2"]
        assert len(file_processing.generate_calls) == 1

    def test_preview_pdf_rejects_invalid_extension():
        """Run test preview pdf rejects invalid extension in this workflow."""
        service, _, catalog_file_repo = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            service.preview_pdf(
                file=SimpleNamespace(filename="catalog.txt"),
                fornecedor_id=1,
                user_id=2,
                offset=0,
                limit=10,
            )
    
        assert exc.value.status_code == 400

    def test_preview_catalog_from_region_returns_columns_and_rows():
        """Run test preview catalog from region returns columns and rows in this workflow."""
        service, file_processing, catalog_file_repo = _build_service()
        file_processing._df = _DataFrameStub(
            empty=False,
            columns=["col_0", "col_1"],
            rows=[{"col_0": "A", "col_1": "B"}],
        )
    
        payload = service.preview_catalog_from_region(
            file_id=1,
            page_number=2,
            region=[1.0, 2.0, 3.0, 4.0],
        )
    
        assert payload["columns"] == ["col_0", "col_1"]
        assert payload["data"] == [{"col_0": "A", "col_1": "B"}]

    def test_preview_catalog_from_region_raises_when_dataframe_empty():
        """Run test preview catalog from region raises when dataframe empty in this workflow."""
        service, file_processing, catalog_file_repo = _build_service()
        file_processing._df = _DataFrameStub(empty=True)
    
        with pytest.raises(HTTPException) as exc:
            service.preview_catalog_from_region(
                file_id=1,
                page_number=2,
                region=[1.0, 2.0, 3.0, 4.0],
            )
    
        assert exc.value.status_code == 400

    def test_extract_data_from_pdf_bulk_schedules_all_pages(monkeypatch):
        """Run test extract data from pdf bulk schedules all pages in this workflow."""
        service, file_processing, catalog_file_repo = _build_service()
        tasks = _BackgroundTasksStub()
    
        monkeypatch.setattr(preview_module.pdfplumber, "open", lambda _path: _PdfStub(3))
    
        payload = service.extract_data_from_pdf_bulk(
            background_tasks=tasks,
            file_id=1,
            region=[1.0, 2.0, 3.0, 4.0],
            pages=None,
            all_pages=True,
        )
    
        assert payload["total_pages"] == 3
        assert len(tasks.calls) == 3
        for fn, kwargs in tasks.calls:
            assert fn == file_processing.extract_data_from_pdf_region
            assert kwargs["region"] == [1.0, 2.0, 3.0, 4.0]

    def test_extract_data_from_pdf_bulk_dispatches_celery_when_enabled(monkeypatch):
        """Dispatch raw region extraction through Celery when configured."""
        dispatcher = _DispatcherStub(use_celery=True)
        service, _, _ = _build_service(dispatcher_cls=lambda: dispatcher)

        monkeypatch.setattr(preview_module.pdfplumber, "open", lambda _path: _PdfStub(2))

        payload = service.extract_data_from_pdf_bulk(
            background_tasks=_BackgroundTasksStub(),
            file_id=1,
            region=[1.0, 2.0, 3.0, 4.0],
            pages=None,
            all_pages=True,
        )

        assert payload["total_pages"] == 2
        assert dispatcher.named_calls == [
            (
                "pdf_extraction.region",
                {
                    "file_path": "/tmp/catalog.pdf",
                    "page_number": 1,
                    "region": [1.0, 2.0, 3.0, 4.0],
                },
            ),
            (
                "pdf_extraction.region",
                {
                    "file_path": "/tmp/catalog.pdf",
                    "page_number": 2,
                    "region": [1.0, 2.0, 3.0, 4.0],
                },
            ),
        ]

_build_service = _TopLevelFunctionSurface._build_service
test_preview_pages_rejects_non_pdf = _TopLevelFunctionSurface.test_preview_pages_rejects_non_pdf
test_preview_pages_generates_images = _TopLevelFunctionSurface.test_preview_pages_generates_images
test_preview_pdf_rejects_invalid_extension = _TopLevelFunctionSurface.test_preview_pdf_rejects_invalid_extension
test_preview_catalog_from_region_returns_columns_and_rows = _TopLevelFunctionSurface.test_preview_catalog_from_region_returns_columns_and_rows
test_preview_catalog_from_region_raises_when_dataframe_empty = _TopLevelFunctionSurface.test_preview_catalog_from_region_raises_when_dataframe_empty
test_extract_data_from_pdf_bulk_schedules_all_pages = _TopLevelFunctionSurface.test_extract_data_from_pdf_bulk_schedules_all_pages
test_extract_data_from_pdf_bulk_dispatches_celery_when_enabled = _TopLevelFunctionSurface.test_extract_data_from_pdf_bulk_dispatches_celery_when_enabled












