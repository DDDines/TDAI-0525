"""Module test fornecedor preview service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
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
    """Class _FileProcessingStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.generate_calls = []
        self.preview_calls = []
        self.extract_calls = []
        self._file_path = "/tmp/catalog.pdf"
        self._df = None

    def generate_pdf_page_images(self, path, file_id):
        """Execute generate_pdf_page_images.

        This callable is documented to make behavior explicit for readers.
        """
        self.generate_calls.append((path, file_id))
        return ["img://1", "img://2"]

    def pdf_pages_to_images(self, **kwargs):
        """Execute pdf_pages_to_images.

        This callable is documented to make behavior explicit for readers.
        """
        self.preview_calls.append(kwargs)
        return {"pages": [{"page_number": 1}]}

    def get_file_path_by_id(self, db, file_id):
        """Execute get_file_path_by_id.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (db, file_id)
        return self._file_path

    def extract_pdf_region_image(self, **kwargs):
        """Execute extract_pdf_region_image.

        This callable is documented to make behavior explicit for readers.
        """
        self.extract_calls.append(kwargs)
        return b"fake-bytes"

    def parse_annotation_to_dataframe(self, annotation):
        """Execute parse_annotation_to_dataframe.

        This callable is documented to make behavior explicit for readers.
        """
        _ = annotation
        return self._df

    def extract_data_from_pdf_region(self, **kwargs):
        """Execute extract_data_from_pdf_region.

        This callable is documented to make behavior explicit for readers.
        """
        _ = kwargs


class _WebExtractorStub:
    """Class _WebExtractorStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def extract_text_from_image_region(self, image_bytes):
        """Execute extract_text_from_image_region.

        This callable is documented to make behavior explicit for readers.
        """
        _ = image_bytes
        return "annotated"


class _UploadFileStub:
    """Class _UploadFileStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, filename: str, payload: bytes = b"pdf"):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.filename = filename
        self._payload = payload

    async def read(self):
        """Execute read.

        This callable is documented to make behavior explicit for readers.
        """
        return self._payload


class _DataFrameStub:
    """Class _DataFrameStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, empty: bool, columns=None, rows=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.empty = empty
        self._columns = columns or []
        self._rows = rows or []

    @property
    def columns(self):
        """Execute columns.

        This callable is documented to make behavior explicit for readers.
        """
        return SimpleNamespace(astype=lambda _type: SimpleNamespace(tolist=lambda: self._columns))

    def head(self, _limit):
        """Execute head.

        This callable is documented to make behavior explicit for readers.
        """
        return self

    def to_dict(self, orient):
        """Execute to_dict.

        This callable is documented to make behavior explicit for readers.
        """
        _ = orient
        return self._rows


class _BackgroundTasksStub:
    """Class _BackgroundTasksStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def add_task(self, fn, **kwargs):
        """Execute add_task.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append((fn, kwargs))


class _CatalogFileRepoStub:
    """Class _CatalogFileRepoStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._db = object()


class _PdfStub:
    """Class _PdfStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, pages_count):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.pages = [object() for _ in range(pages_count)]

    def __enter__(self):
        """Execute __enter__.

        This callable is documented to make behavior explicit for readers.
        """
        return self

    def __exit__(self, exc_type, exc, tb):
        """Execute __exit__.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (exc_type, exc, tb)
        return False


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service():
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        file_processing = _FileProcessingStub()
        catalog_repo = _CatalogFileRepoStub()
        service = FornecedorPreviewService(
            file_processing_service=file_processing,
            web_data_extractor_service=_WebExtractorStub(),
            catalog_file_repository=catalog_repo,
        )
        return service, file_processing, catalog_repo

    def test_preview_pages_rejects_non_pdf():
        """Execute test_preview_pages_rejects_non_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        service, _, _ = _build_service()
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(service.preview_pages(file=_UploadFileStub("catalog.csv")))
    
        assert exc.value.status_code == 400

    def test_preview_pages_generates_images():
        """Execute test_preview_pages_generates_images.

        This callable is documented to make behavior explicit for readers.
        """
        service, file_processing, _ = _build_service()
    
        payload = asyncio.run(
            service.preview_pages(file=_UploadFileStub("catalog.pdf", b"payload"))
        )
    
        assert payload["file_id"]
        assert payload["page_image_urls"] == ["img://1", "img://2"]
        assert len(file_processing.generate_calls) == 1

    def test_preview_pdf_rejects_invalid_extension():
        """Execute test_preview_pdf_rejects_invalid_extension.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_preview_catalog_from_region_returns_columns_and_rows.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_preview_catalog_from_region_raises_when_dataframe_empty.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_extract_data_from_pdf_bulk_schedules_all_pages.

        This callable is documented to make behavior explicit for readers.
        """
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

_build_service = _TopLevelFunctionSurface._build_service
test_preview_pages_rejects_non_pdf = _TopLevelFunctionSurface.test_preview_pages_rejects_non_pdf
test_preview_pages_generates_images = _TopLevelFunctionSurface.test_preview_pages_generates_images
test_preview_pdf_rejects_invalid_extension = _TopLevelFunctionSurface.test_preview_pdf_rejects_invalid_extension
test_preview_catalog_from_region_returns_columns_and_rows = _TopLevelFunctionSurface.test_preview_catalog_from_region_returns_columns_and_rows
test_preview_catalog_from_region_raises_when_dataframe_empty = _TopLevelFunctionSurface.test_preview_catalog_from_region_raises_when_dataframe_empty
test_extract_data_from_pdf_bulk_schedules_all_pages = _TopLevelFunctionSurface.test_extract_data_from_pdf_bulk_schedules_all_pages












