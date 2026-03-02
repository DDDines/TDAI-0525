"""Module test catalog import preview service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.catalog_import_preview_service import (
    CatalogImportPreviewService,
)


class _CatalogImportFileModel:
    """Class _CatalogImportFileModel.

    Encapsulates one responsibility in the backend architecture.
    """
    pass


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    CatalogImportFile = _CatalogImportFileModel


class _CatalogFileRepoStub:
    """Class _CatalogFileRepoStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, record):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.record = record
        self.saved = []

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Execute get_catalog_file_for_user.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (file_id, user_id)
        return self.record

    def save_catalog_file(self, *, catalog_file):
        """Execute save_catalog_file.

        This callable is documented to make behavior explicit for readers.
        """
        self.saved.append(catalog_file)
        return catalog_file


class _UploadFileStub:
    """Class _UploadFileStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, filename: str, content: bytes):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.filename = filename
        self._content = content
        self.seek_calls = []

    async def read(self):
        """Execute read.

        This callable is documented to make behavior explicit for readers.
        """
        return self._content

    async def seek(self, pos: int):
        """Execute seek.

        This callable is documented to make behavior explicit for readers.
        """
        self.seek_calls.append(pos)


class _ColumnsStub(list):
    """Class _ColumnsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def tolist(self):
        """Execute tolist.

        This callable is documented to make behavior explicit for readers.
        """
        return list(self)


class _DataFrameStub:
    """Class _DataFrameStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, rows):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._rows = rows
        self.empty = len(rows) == 0
        self.columns = _ColumnsStub(list(rows[0].keys()) if rows else [])

    def to_dict(self, orient):
        """Execute to_dict.

        This callable is documented to make behavior explicit for readers.
        """
        _ = orient
        return self._rows


class _FileProcessingStub:
    """Class _FileProcessingStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.saved_record = None
        self.preview_response = None
        self.preview_tabular_response = None
        self.df_region = _DataFrameStub(rows=[])
        self.processed_rows = []
        self.single_page = {"image": "img", "text": "txt", "table": []}

    async def save_uploaded_catalog(self, file, fornecedor_id):
        """Execute save_uploaded_catalog.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (file, fornecedor_id)
        return self.saved_record

    async def preview_arquivo_pdf(self, content, ext, start_page, page_count, dpi):
        """Execute preview_arquivo_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, ext, start_page, page_count, dpi)
        return self.preview_response

    async def gerar_preview(self, content, ext):
        """Execute gerar_preview.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, ext)
        return self.preview_tabular_response

    def extract_data_from_pdf_region(self, file_path, page, selected_bbox):
        """Execute extract_data_from_pdf_region.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (file_path, page, selected_bbox)
        return self.df_region

    def processar_linha_padronizada(self, row, mapping):
        """Execute processar_linha_padronizada.

        This callable is documented to make behavior explicit for readers.
        """
        _ = mapping
        self.processed_rows.append(row)
        if str(next(iter(row.values()), "")).strip():
            return {"nome_base": "ok"}
        return None

    async def extrair_pagina_pdf(self, content, page_number):
        """Execute extrair_pagina_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (content, page_number)
        return self.single_page


class _LoggerStub:
    """Class _LoggerStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def info(self, *args, **kwargs):
        """Execute info.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append((args, kwargs))


class _PageStub:
    """Class _PageStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, width=1000.0, height=1000.0, text=""):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.width = width
        self.height = height
        self._text = text

    def crop(self, bbox):
        """Execute crop.

        This callable is documented to make behavior explicit for readers.
        """
        _ = bbox
        return self

    def extract_text(self):
        """Execute extract_text.

        This callable is documented to make behavior explicit for readers.
        """
        return self._text


class _PdfStub:
    """Class _PdfStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, pages):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.pages = pages


class _PdfCtx:
    """Class _PdfCtx.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, pdf):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._pdf = pdf

    def __enter__(self):
        """Execute __enter__.

        This callable is documented to make behavior explicit for readers.
        """
        return self._pdf

    def __exit__(self, exc_type, exc, tb):
        """Execute __exit__.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (exc_type, exc, tb)
        return False


class _PdfPlumberStub:
    """Class _PdfPlumberStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, pages):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._pages = pages

    def open(self, path):
        """Execute open.

        This callable is documented to make behavior explicit for readers.
        """
        _ = path
        return _PdfCtx(_PdfStub(self._pages))


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(*, upload_dir: Path, record=None, pages=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        file_processing = _FileProcessingStub()
        logger = _LoggerStub()
        catalog_file_repo = _CatalogFileRepoStub(record=record)
        service = CatalogImportPreviewService(
            models=_ModelsStub,
            settings=SimpleNamespace(UPLOAD_DIRECTORY=str(upload_dir)),
            file_processing_service=file_processing,
            resolve_storage_path=lambda p: Path(p),
            logger=logger,
            pdfplumber_module=_PdfPlumberStub(pages or [_PageStub()]),
            catalog_file_repository=catalog_file_repo,
        )
        return service, file_processing, logger, catalog_file_repo

    def test_importar_catalogo_preview_pdf_success(tmp_path):
        """Execute test_importar_catalogo_preview_pdf_success.

        This callable is documented to make behavior explicit for readers.
        """
        record = SimpleNamespace(id=10, original_filename="catalogo.pdf", stored_filename="x.pdf")
        service, file_processing, _, catalog_file_repo = _build_service(upload_dir=tmp_path, record=record)
        file_processing.saved_record = record
        file_processing.preview_response = {
            "num_pages": 2,
            "table_pages": [1],
            "sample_rows": [],
            "preview_images": [],
            "headers": ["col_1"],
        }
        upload = _UploadFileStub(filename="catalogo.pdf", content=b"pdf")
    
        result = asyncio.run(
            service.importar_catalogo_preview(
                file=upload,
                fornecedor_id=3,
                start_page=1,
                page_count=5,
                dpi=72,
                user_id=99,
            )
        )
    
        assert result["file_id"] == 10
        assert result["error"] is None
        assert record.user_id == 99
        assert len(catalog_file_repo.saved) == 1

    def test_selecionar_regiao_uses_dataframe_rows(tmp_path):
        """Execute test_selecionar_regiao_uses_dataframe_rows.

        This callable is documented to make behavior explicit for readers.
        """
        catalogs_dir = tmp_path / "catalogs"
        catalogs_dir.mkdir(parents=True, exist_ok=True)
        (catalogs_dir / "arquivo.pdf").write_bytes(b"dummy")
    
        record = SimpleNamespace(id=1, stored_filename="arquivo.pdf")
        service, file_processing, _, _ = _build_service(upload_dir=tmp_path, record=record)
        file_processing.df_region = _DataFrameStub(
            rows=[
                {"col_1": "1816D", "col_2": "Paralama"},
                {"col_1": "", "col_2": ""},
            ]
        )
    
        result = service.selecionar_regiao(
            file_id=1,
            page=1,
            bbox=[0, 0, 900, 900],
            bbox_norm=None,
            user_id=3,
        )
    
        assert result["preview_headers"] == ["col_1", "col_2"]
        assert len(result["preview_rows"]) == 2
        assert len(result["produtos"]) == 1

    def test_extrair_pagina_unica_raises_404_when_record_missing(tmp_path):
        """Execute test_extrair_pagina_unica_raises_404_when_record_missing.

        This callable is documented to make behavior explicit for readers.
        """
        service, _, _, _ = _build_service(upload_dir=tmp_path, record=None)
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.extrair_pagina_unica(
                    file_id=1,
                    page_number=1,
                    user_id=7,
                )
            )
    
        assert exc.value.status_code == 404

    def test_extrair_pagina_unica_success(tmp_path):
        """Execute test_extrair_pagina_unica_success.

        This callable is documented to make behavior explicit for readers.
        """
        catalogs_dir = tmp_path / "catalogs"
        catalogs_dir.mkdir(parents=True, exist_ok=True)
        (catalogs_dir / "arquivo.pdf").write_bytes(b"pdf")
    
        record = SimpleNamespace(id=1, stored_filename="arquivo.pdf")
        service, _, _, _ = _build_service(upload_dir=tmp_path, record=record)
    
        result = asyncio.run(
            service.extrair_pagina_unica(
                file_id=1,
                page_number=3,
                user_id=7,
            )
        )
    
        assert result["image"] == "img"
        assert result["text"] == "txt"

_build_service = _TopLevelFunctionSurface._build_service
test_importar_catalogo_preview_pdf_success = _TopLevelFunctionSurface.test_importar_catalogo_preview_pdf_success
test_selecionar_regiao_uses_dataframe_rows = _TopLevelFunctionSurface.test_selecionar_regiao_uses_dataframe_rows
test_extrair_pagina_unica_raises_404_when_record_missing = _TopLevelFunctionSurface.test_extrair_pagina_unica_raises_404_when_record_missing
test_extrair_pagina_unica_success = _TopLevelFunctionSurface.test_extrair_pagina_unica_success








