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
    pass


class _ModelsStub:
    CatalogImportFile = _CatalogImportFileModel


class _QueryStub:
    def __init__(self, record):
        self._record = record

    def filter_by(self, **kwargs):
        _ = kwargs
        return self

    def first(self):
        return self._record


class _DbStub:
    def __init__(self, record=None):
        self.record = record
        self.added = []
        self.committed = 0
        self.refreshed = []

    def query(self, model):
        _ = model
        return _QueryStub(self.record)

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.committed += 1

    def refresh(self, obj):
        self.refreshed.append(obj)


class _UploadFileStub:
    def __init__(self, *, filename: str, content: bytes):
        self.filename = filename
        self._content = content
        self.seek_calls = []

    async def read(self):
        return self._content

    async def seek(self, pos: int):
        self.seek_calls.append(pos)


class _ColumnsStub(list):
    def tolist(self):
        return list(self)


class _DataFrameStub:
    def __init__(self, *, rows):
        self._rows = rows
        self.empty = len(rows) == 0
        self.columns = _ColumnsStub(list(rows[0].keys()) if rows else [])

    def to_dict(self, orient):
        _ = orient
        return self._rows


class _FileProcessingStub:
    def __init__(self):
        self.saved_record = None
        self.preview_response = None
        self.preview_tabular_response = None
        self.df_region = _DataFrameStub(rows=[])
        self.processed_rows = []
        self.single_page = {"image": "img", "text": "txt", "table": []}

    async def save_uploaded_catalog(self, file, fornecedor_id):
        _ = (file, fornecedor_id)
        return self.saved_record

    async def preview_arquivo_pdf(self, content, ext, start_page, page_count, dpi):
        _ = (content, ext, start_page, page_count, dpi)
        return self.preview_response

    async def gerar_preview(self, content, ext):
        _ = (content, ext)
        return self.preview_tabular_response

    def extract_data_from_pdf_region(self, file_path, page, selected_bbox):
        _ = (file_path, page, selected_bbox)
        return self.df_region

    def processar_linha_padronizada(self, row, mapping):
        _ = mapping
        self.processed_rows.append(row)
        if str(next(iter(row.values()), "")).strip():
            return {"nome_base": "ok"}
        return None

    async def extrair_pagina_pdf(self, content, page_number):
        _ = (content, page_number)
        return self.single_page


class _LoggerStub:
    def __init__(self):
        self.calls = []

    def info(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class _PageStub:
    def __init__(self, width=1000.0, height=1000.0, text=""):
        self.width = width
        self.height = height
        self._text = text

    def crop(self, bbox):
        _ = bbox
        return self

    def extract_text(self):
        return self._text


class _PdfStub:
    def __init__(self, pages):
        self.pages = pages


class _PdfCtx:
    def __init__(self, pdf):
        self._pdf = pdf

    def __enter__(self):
        return self._pdf

    def __exit__(self, exc_type, exc, tb):
        _ = (exc_type, exc, tb)
        return False


class _PdfPlumberStub:
    def __init__(self, pages):
        self._pages = pages

    def open(self, path):
        _ = path
        return _PdfCtx(_PdfStub(self._pages))


def _build_service(*, upload_dir: Path, record=None, pages=None):
    file_processing = _FileProcessingStub()
    logger = _LoggerStub()
    service = CatalogImportPreviewService(
        models=_ModelsStub,
        settings=SimpleNamespace(UPLOAD_DIRECTORY=str(upload_dir)),
        file_processing_service=file_processing,
        resolve_storage_path=lambda p: Path(p),
        logger=logger,
        pdfplumber_module=_PdfPlumberStub(pages or [_PageStub()]),
    )
    db = _DbStub(record=record)
    return service, file_processing, logger, db


def test_importar_catalogo_preview_pdf_success(tmp_path):
    record = SimpleNamespace(id=10, original_filename="catalogo.pdf", stored_filename="x.pdf")
    service, file_processing, _, db = _build_service(upload_dir=tmp_path, record=record)
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
            db=db,
            user_id=99,
        )
    )

    assert result["file_id"] == 10
    assert result["error"] is None
    assert record.user_id == 99
    assert db.committed == 1


def test_selecionar_regiao_uses_dataframe_rows(tmp_path):
    catalogs_dir = tmp_path / "catalogs"
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    (catalogs_dir / "arquivo.pdf").write_bytes(b"dummy")

    record = SimpleNamespace(id=1, stored_filename="arquivo.pdf")
    service, file_processing, _, db = _build_service(upload_dir=tmp_path, record=record)
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
        db=db,
        user_id=3,
    )

    assert result["preview_headers"] == ["col_1", "col_2"]
    assert len(result["preview_rows"]) == 2
    assert len(result["produtos"]) == 1


def test_extrair_pagina_unica_raises_404_when_record_missing(tmp_path):
    service, _, _, db = _build_service(upload_dir=tmp_path, record=None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.extrair_pagina_unica(
                file_id=1,
                page_number=1,
                db=db,
                user_id=7,
            )
        )

    assert exc.value.status_code == 404


def test_extrair_pagina_unica_success(tmp_path):
    catalogs_dir = tmp_path / "catalogs"
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    (catalogs_dir / "arquivo.pdf").write_bytes(b"pdf")

    record = SimpleNamespace(id=1, stored_filename="arquivo.pdf")
    service, _, _, db = _build_service(upload_dir=tmp_path, record=record)

    result = asyncio.run(
        service.extrair_pagina_unica(
            file_id=1,
            page_number=3,
            db=db,
            user_id=7,
        )
    )

    assert result["image"] == "img"
    assert result["text"] == "txt"
