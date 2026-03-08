"""Module test catalog import preview service.

Contains backend logic related to test catalog import preview service and documents its role in the OOP architecture.
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
    """Represent catalog import file model and centralize responsibilities for this module."""
    pass


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    CatalogImportFile = _CatalogImportFileModel


class _CatalogFileRepoStub:
    """Represent catalog file repo stub and centralize responsibilities for this module."""
    def __init__(self, record):
        """Initialize collaborators and configuration required by this component."""
        self.record = record
        self.saved = []

    def get_catalog_file_for_user(self, *, file_id: int, user_id: int):
        """Return catalog file for user for this workflow."""
        _ = (file_id, user_id)
        return self.record

    def save_catalog_file(self, *, catalog_file):
        """Run save catalog file in this workflow."""
        self.saved.append(catalog_file)
        return catalog_file


class _UploadFileStub:
    """Represent upload file stub and centralize responsibilities for this module."""
    def __init__(self, *, filename: str, content: bytes):
        """Initialize collaborators and configuration required by this component."""
        self.filename = filename
        self._content = content
        self.seek_calls = []

    async def read(self):
        """Run read in this workflow."""
        return self._content

    async def seek(self, pos: int):
        """Run seek in this workflow."""
        self.seek_calls.append(pos)


class _ColumnsStub(list):
    """Represent columns stub and centralize responsibilities for this module."""
    def tolist(self):
        """Run tolist in this workflow."""
        return list(self)


class _DataFrameStub:
    """Represent data frame stub and centralize responsibilities for this module."""
    def __init__(self, *, rows):
        """Initialize collaborators and configuration required by this component."""
        self._rows = rows
        self.empty = len(rows) == 0
        self.columns = _ColumnsStub(list(rows[0].keys()) if rows else [])

    def to_dict(self, orient):
        """Run to dict in this workflow."""
        _ = orient
        return self._rows


class _FileProcessingStub:
    """Represent file processing stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.saved_record = None
        self.preview_response = None
        self.preview_tabular_response = None
        self.df_region = _DataFrameStub(rows=[])
        self.processed_rows = []
        self.single_page = {"image": "img", "text": "txt", "table": []}

    async def save_uploaded_catalog(self, file, fornecedor_id):
        """Run save uploaded catalog in this workflow."""
        _ = (file, fornecedor_id)
        return self.saved_record

    async def preview_arquivo_pdf(self, content, ext, start_page, page_count, dpi):
        """Run preview arquivo pdf in this workflow."""
        _ = (content, ext, start_page, page_count, dpi)
        return self.preview_response

    async def gerar_preview(self, content, ext):
        """Run gerar preview in this workflow."""
        _ = (content, ext)
        return self.preview_tabular_response

    def extract_data_from_pdf_region(self, file_path, page, selected_bbox):
        """Extract data from pdf region for this workflow."""
        _ = (file_path, page, selected_bbox)
        return self.df_region

    def processar_linha_padronizada(self, row, mapping):
        """Run processar linha padronizada in this workflow."""
        _ = mapping
        self.processed_rows.append(row)
        if str(next(iter(row.values()), "")).strip():
            return {"nome_base": "ok"}
        return None

    async def extrair_pagina_pdf(self, content, page_number):
        """Run extrair pagina pdf in this workflow."""
        _ = (content, page_number)
        return self.single_page


class _LoggerStub:
    """Represent logger stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def info(self, *args, **kwargs):
        """Run info in this workflow."""
        self.calls.append((args, kwargs))

    def exception(self, *args, **kwargs):
        """Run exception in this workflow."""
        self.calls.append((args, kwargs))


class _PageStub:
    """Represent page stub and centralize responsibilities for this module."""
    def __init__(self, width=1000.0, height=1000.0, text=""):
        """Initialize collaborators and configuration required by this component."""
        self.width = width
        self.height = height
        self._text = text

    def crop(self, bbox):
        """Run crop in this workflow."""
        _ = bbox
        return self

    def extract_text(self):
        """Extract text for this workflow."""
        return self._text


class _PdfStub:
    """Represent pdf stub and centralize responsibilities for this module."""
    def __init__(self, pages):
        """Initialize collaborators and configuration required by this component."""
        self.pages = pages


class _PdfCtx:
    """Represent pdf ctx and centralize responsibilities for this module."""
    def __init__(self, pdf):
        """Initialize collaborators and configuration required by this component."""
        self._pdf = pdf

    def __enter__(self):
        """Run enter in this workflow."""
        return self._pdf

    def __exit__(self, exc_type, exc, tb):
        """Run exit in this workflow."""
        _ = (exc_type, exc, tb)
        return False


class _PdfPlumberStub:
    """Represent pdf plumber stub and centralize responsibilities for this module."""
    def __init__(self, pages):
        """Initialize collaborators and configuration required by this component."""
        self._pages = pages

    def open(self, path):
        """Run open in this workflow."""
        _ = path
        return _PdfCtx(_PdfStub(self._pages))


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, upload_dir: Path, record=None, pages=None):
        """Run build service in this workflow."""
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
        """Run test importar catalogo preview pdf success in this workflow."""
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
        """Run test selecionar regiao uses dataframe rows in this workflow."""
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
        """Run test extrair pagina unica raises 404 when record missing in this workflow."""
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
        """Run test extrair pagina unica success in this workflow."""
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

    def test_importar_catalogo_preview_tabular_paths_and_exception(tmp_path):
        """Cover non-PDF preview success, tabular error, and generic exception fallback."""
        upload = _UploadFileStub(filename="catalogo.xlsx", content=b"xlsx")
        record = SimpleNamespace(id=11, original_filename="catalogo.xlsx", stored_filename="x.xlsx")
        service, file_processing, logger, catalog_file_repo = _build_service(upload_dir=tmp_path, record=record)
        file_processing.saved_record = record
        file_processing.preview_tabular_response = {
            "sample_rows": [{"sku": "1"}],
            "headers": ["sku"],
        }

        success = asyncio.run(
            service.importar_catalogo_preview(
                file=upload,
                fornecedor_id=None,
                start_page=1,
                page_count=1,
                dpi=72,
                user_id=77,
            )
        )
        assert success["num_pages"] == 1
        assert success["headers"] == ["sku"]
        assert upload.seek_calls == [0]
        assert catalog_file_repo.saved[0].user_id == 77
        assert logger.calls

        file_processing.preview_tabular_response = {"error": "planilha invalida"}
        error_result = asyncio.run(
            service.importar_catalogo_preview(
                file=upload,
                fornecedor_id=None,
                start_page=1,
                page_count=1,
                dpi=72,
                user_id=77,
            )
        )
        assert error_result["error"] == "planilha invalida"
        assert error_result["sample_rows"] == []

        async def _boom(*_args, **_kwargs):
            raise RuntimeError("preview quebrou")

        file_processing.preview_arquivo_pdf = _boom
        record.original_filename = "catalogo.pdf"
        upload_pdf = _UploadFileStub(filename="catalogo.pdf", content=b"pdf")
        fail_result = asyncio.run(
            service.importar_catalogo_preview(
                file=upload_pdf,
                fornecedor_id=None,
                start_page=1,
                page_count=1,
                dpi=72,
                user_id=77,
            )
        )
        assert "Falha ao gerar preview de PDF" in fail_result["error"]
        assert fail_result["sample_rows"] == {}

    def test_selecionar_regiao_fallback_text_and_validation_paths(tmp_path):
        """Cover text fallback, invalid page/bbox, missing file, and generic processing errors."""
        catalogs_dir = tmp_path / "catalogs"
        catalogs_dir.mkdir(parents=True, exist_ok=True)
        (catalogs_dir / "arquivo.pdf").write_bytes(b"dummy")

        page = _PageStub(text="Nome: Produto X\nMarca: Marca Y\n\nSKU: 123\nDescricao: Texto")
        record = SimpleNamespace(id=2, stored_filename="arquivo.pdf")
        service, file_processing, logger, _ = _build_service(upload_dir=tmp_path, record=record, pages=[page])
        file_processing.df_region = _DataFrameStub(rows=[])

        fallback_result = service.selecionar_regiao(
            file_id=2,
            page=1,
            bbox=[0, 0, 900, 900],
            bbox_norm=[0, 0, 1, 1],
            user_id=9,
        )
        assert fallback_result["preview_headers"] == ["nome", "marca", "sku", "descricao"]
        assert fallback_result["produtos"]
        assert any("fallback de texto" in item for item in fallback_result["log"])
        assert logger.calls

        with pytest.raises(HTTPException) as invalid_page:
            service.selecionar_regiao(
                file_id=2,
                page=99,
                bbox=[0, 0, 100, 100],
                bbox_norm=None,
                user_id=9,
            )
        assert invalid_page.value.status_code == 400

        with pytest.raises(HTTPException) as invalid_bbox:
            service.selecionar_regiao(
                file_id=2,
                page=1,
                bbox=[10, 10, 5, 5],
                bbox_norm=None,
                user_id=9,
            )
        assert invalid_bbox.value.status_code == 400

        missing_record = SimpleNamespace(id=2, stored_filename="inexistente.pdf")
        missing_service, _, _, _ = _build_service(upload_dir=tmp_path, record=missing_record, pages=[page])
        with pytest.raises(HTTPException) as missing_file:
            missing_service.selecionar_regiao(
                file_id=2,
                page=1,
                bbox=[0, 0, 100, 100],
                bbox_norm=None,
                user_id=9,
            )
        assert missing_file.value.status_code == 404

        def _explode(*_args, **_kwargs):
            raise RuntimeError("extract fail")

        file_processing.extract_data_from_pdf_region = _explode
        with pytest.raises(HTTPException) as generic_error:
            service.selecionar_regiao(
                file_id=2,
                page=1,
                bbox=[0, 0, 100, 100],
                bbox_norm=None,
                user_id=9,
            )
        assert generic_error.value.status_code == 500

    def test_extrair_pagina_unica_validation_and_helper_paths(tmp_path):
        """Cover page extraction error paths and preview row/text parsing helpers."""
        catalogs_dir = tmp_path / "catalogs"
        catalogs_dir.mkdir(parents=True, exist_ok=True)
        (catalogs_dir / "arquivo.pdf").write_bytes(b"pdf")
        record = SimpleNamespace(id=3, stored_filename="arquivo.pdf")
        service, file_processing, _, repo = _build_service(upload_dir=tmp_path, record=record)

        assert service._resolve_catalog_file_repo() is repo
        assert service._get_record_or_404(catalog_file_repo=repo, file_id=3, user_id=1) is record
        assert service._build_catalog_path(record).as_posix().endswith("/catalogs/arquivo.pdf")
        assert service._normalize_preview_row({"a": None, "b": float("nan"), "c": "ok"}) == {
            "a": None,
            "b": None,
            "c": "ok",
        }
        parsed_rows = service._parse_key_value_rows("Nome Base: Item\nMarca: Teste\nNome Base: Outro\nCodigo: 123")
        assert parsed_rows == [{"nome_base": "Item", "marca": "Teste"}, {"nome_base": "Outro", "sku": "123"}]
        extracted_rows = service._extract_text_rows(
            file_path=service._build_catalog_path(record),
            page=1,
            selected_bbox=[0, 0, 10, 10],
        )
        assert extracted_rows == []

        async def _raise_value_error(*_args, **_kwargs):
            raise ValueError("page invalid")

        file_processing.extrair_pagina_pdf = _raise_value_error
        with pytest.raises(HTTPException) as value_error:
            asyncio.run(
                service.extrair_pagina_unica(
                    file_id=3,
                    page_number=1,
                    user_id=1,
                )
            )
        assert value_error.value.status_code == 400

        async def _raise_runtime_error(*_args, **_kwargs):
            raise RuntimeError("page crash")

        file_processing.extrair_pagina_pdf = _raise_runtime_error
        with pytest.raises(HTTPException) as runtime_error:
            asyncio.run(
                service.extrair_pagina_unica(
                    file_id=3,
                    page_number=1,
                    user_id=1,
                )
            )
        assert runtime_error.value.status_code == 500

        (catalogs_dir / "arquivo.pdf").unlink()
        with pytest.raises(HTTPException) as missing_file:
            asyncio.run(
                service.extrair_pagina_unica(
                    file_id=3,
                    page_number=1,
                    user_id=1,
                )
            )
        assert missing_file.value.status_code == 404

_build_service = _TopLevelFunctionSurface._build_service
test_importar_catalogo_preview_pdf_success = _TopLevelFunctionSurface.test_importar_catalogo_preview_pdf_success
test_selecionar_regiao_uses_dataframe_rows = _TopLevelFunctionSurface.test_selecionar_regiao_uses_dataframe_rows
test_extrair_pagina_unica_raises_404_when_record_missing = _TopLevelFunctionSurface.test_extrair_pagina_unica_raises_404_when_record_missing
test_extrair_pagina_unica_success = _TopLevelFunctionSurface.test_extrair_pagina_unica_success
test_importar_catalogo_preview_tabular_paths_and_exception = _TopLevelFunctionSurface.test_importar_catalogo_preview_tabular_paths_and_exception
test_selecionar_regiao_fallback_text_and_validation_paths = _TopLevelFunctionSurface.test_selecionar_regiao_fallback_text_and_validation_paths
test_extrair_pagina_unica_validation_and_helper_paths = _TopLevelFunctionSurface.test_extrair_pagina_unica_validation_and_helper_paths








