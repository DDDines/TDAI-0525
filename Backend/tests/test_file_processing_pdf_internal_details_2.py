"""Additional high-return coverage for PDF processing internals."""

from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest
from fastapi import HTTPException

from Backend.testing.runtime_apis import file_processing


class _SyncStream:
    def __init__(self, payload: bytes = b"pdf", error: Exception | None = None):
        self._payload = payload
        self._error = error
        self.closed = False

    def read(self):
        if self._error is not None:
            raise self._error
        return self._payload

    def close(self):
        self.closed = True


class _PdfContext:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _ImageStub:
    def save(self, destination, fmt=None, **kwargs):
        _ = fmt, kwargs
        if hasattr(destination, "write"):
            destination.write(b"img-bytes")
            return
        Path(destination).write_bytes(b"img-bytes")


class _RenderedPageImage:
    original = _ImageStub()


class _FakePage:
    def __init__(self, *, text="", tables=None):
        self.width = 100.0
        self.height = 200.0
        self._text = text
        self._tables = tables if tables is not None else []
        self.cropped_bbox = None

    def crop(self, bbox):
        self.cropped_bbox = bbox
        return self

    def extract_tables(self, table_settings=None):
        _ = table_settings
        return self._tables

    def extract_text(self):
        return self._text

    def to_image(self, resolution):
        _ = resolution
        return _RenderedPageImage()


class _FakeRepo:
    def __init__(self, catalog_file=None):
        self.catalog_file = catalog_file
        self.updates = []

    def get_catalog_file(self, file_id):
        _ = file_id
        return self.catalog_file

    def update_catalog_file(self, catalog_file):
        snapshot = {
            "status": catalog_file.status,
            "pages_processed": catalog_file.pages_processed,
            "total_pages": catalog_file.total_pages,
            "result_summary": catalog_file.result_summary,
        }
        self.updates.append(snapshot)


def _patch_storage(monkeypatch, tmp_path):
    monkeypatch.setattr(
        file_processing.settings,
        "UPLOAD_DIRECTORY",
        str(tmp_path / "uploads"),
        raising=False,
    )
    monkeypatch.setattr(
        file_processing.settings,
        "PREVIEW_DIRECTORY",
        str(tmp_path / "previews"),
        raising=False,
    )


def test_pdf_pages_to_images_impl_requires_poppler(tmp_path, monkeypatch):
    _patch_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(file_processing.shutil, "which", lambda *args, **kwargs: None)

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(b"pdf"))
    with pytest.raises(HTTPException, match="Poppler"):
        file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
            db=object(),
            file=upload,
            fornecedor_id=1,
            user_id=2,
            offset=0,
            limit=2,
        )


def test_pdf_pages_to_images_impl_handles_stream_and_save_errors(tmp_path, monkeypatch):
    _patch_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(file_processing.shutil, "which", lambda *args, **kwargs: "pdftoppm")

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(error=RuntimeError("stream broke")))
    with pytest.raises(HTTPException, match="Erro interno ao ler o ficheiro"):
        file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
            db=object(),
            file=upload,
            fornecedor_id=1,
            user_id=2,
            offset=0,
            limit=2,
        )
    assert upload.file.closed is True

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(b"pdf"))

    def fake_open(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("builtins.open", fake_open)
    with pytest.raises(HTTPException, match="Erro interno ao salvar o arquivo"):
        file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
            db=object(),
            file=upload,
            fornecedor_id=1,
            user_id=2,
            offset=0,
            limit=2,
        )


def test_pdf_pages_to_images_impl_handles_pdf_read_and_conversion_errors(tmp_path, monkeypatch):
    _patch_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(file_processing.shutil, "which", lambda *args, **kwargs: "pdftoppm")
    monkeypatch.setattr(
        file_processing,
        "FornecedorRepository",
        lambda db: SimpleNamespace(
            create_catalog_import_file=lambda **kwargs: SimpleNamespace(id=77)
        ),
    )

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(b"pdf"))
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pdf broken")),
    )
    with pytest.raises(HTTPException, match="Nao foi possivel ler o ficheiro PDF|NÃ£o foi possÃ­vel ler o ficheiro PDF"):
        file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
            db=object(),
            file=upload,
            fornecedor_id=1,
            user_id=2,
            offset=0,
            limit=2,
        )

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(b"pdf"))
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([object(), object(), object()]),
    )
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("convert fail")),
    )
    with pytest.raises(HTTPException, match="Erro ao processar o PDF"):
        file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
            db=object(),
            file=upload,
            fornecedor_id=1,
            user_id=2,
            offset=0,
            limit=2,
        )


def test_pdf_pages_to_images_impl_success(tmp_path, monkeypatch):
    _patch_storage(monkeypatch, tmp_path)
    monkeypatch.setattr(file_processing.shutil, "which", lambda *args, **kwargs: "pdftoppm")
    monkeypatch.setattr(
        file_processing,
        "FornecedorRepository",
        lambda db: SimpleNamespace(
            create_catalog_import_file=lambda **kwargs: SimpleNamespace(id=55)
        ),
    )
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([object(), object(), object()]),
    )
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [_ImageStub(), _ImageStub()],
    )

    upload = SimpleNamespace(filename="catalogo.pdf", file=_SyncStream(b"pdf"))
    result = file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
        db=object(),
        file=upload,
        fornecedor_id=1,
        user_id=2,
        offset=1,
        limit=2,
    )

    assert result["total_pages"] == 3
    assert result["import_file_id"] == 55
    assert result["image_urls"] == [
        "/static/previews/preview_55_2.png",
        "/static/previews/preview_55_3.png",
    ]


def test_extract_data_from_pdf_region_impl_returns_text_dataframe(monkeypatch):
    page = _FakePage(text="sku nome\nA1 Produto", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page]),
    )

    df = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=[0.1, 0.1, 0.9, 0.9],
    )

    assert page.cropped_bbox == (0.1, 0.1, 0.9, 0.9)
    assert list(df.columns) == ["sku", "nome"]
    assert df.iloc[0].to_dict() == {"sku": "A1", "nome": "Produto"}


def test_extract_data_from_pdf_region_impl_returns_ocr_guided_dataframe(monkeypatch):
    page = _FakePage(text="", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page]),
    )

    import PIL.ImageEnhance
    import PIL.ImageOps

    monkeypatch.setattr(PIL.ImageOps, "autocontrast", lambda image: image)
    monkeypatch.setattr(
        PIL.ImageEnhance,
        "Contrast",
        lambda image: SimpleNamespace(enhance=lambda factor: image),
    )

    helper = file_processing._PdfRegionExtractionUtils
    merged_lines = [
        [{"text": "SKU", "x": 0, "x0": 0}, {"text": "Nome", "x": 50, "x0": 50}],
        [{"text": "A1", "x": 0, "x0": 0}, {"text": "Produto", "x": 50, "x0": 50}],
    ]
    monkeypatch.setattr(helper, "group_words_by_line_ids", lambda words: merged_lines)
    monkeypatch.setattr(helper, "merge_words_in_line", lambda line_words: line_words)
    monkeypatch.setattr(
        helper,
        "detect_header_columns",
        lambda lines: {"headers": ["sku", "nome"], "bounds": [0, 50], "line_idx": 0},
    )
    monkeypatch.setattr(helper, "filter_ocr_rows", lambda rows: rows)
    monkeypatch.setattr(helper, "clean_df", lambda df: df)

    ocr_state = SimpleNamespace(
        available=True,
        exec_available=True,
        exec_failed_once=False,
        image_cls=SimpleNamespace(open=lambda stream: SimpleNamespace(convert=lambda mode: SimpleNamespace())),
        pytesseract=SimpleNamespace(
            Output=SimpleNamespace(DICT=object()),
            image_to_data=lambda img, output_type, config: {
                "text": ["SKU", "Nome", "A1", "Produto"],
                "conf": ["95", "95", "95", "95"],
                "left": [0, 50, 0, 50],
                "top": [0, 0, 20, 20],
                "width": [10, 10, 10, 10],
                "height": [10, 10, 10, 10],
                "block_num": [1, 1, 1, 1],
                "par_num": [1, 1, 1, 1],
                "line_num": [1, 1, 2, 2],
            },
        ),
    )

    df = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=ocr_state,
    )

    assert list(df.columns) == ["sku", "nome"]
    assert df.iloc[0].to_dict() == {"sku": "A1", "nome": "Produto"}


def test_extract_data_from_pdf_region_impl_handles_invalid_page_and_ocr_unavailable(monkeypatch):
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([_FakePage(text="", tables=[])]),
    )

    empty_invalid = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=9,
        region=None,
    )
    assert empty_invalid.empty is True

    empty_ocr = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=SimpleNamespace(
            available=False,
            exec_available=False,
            exec_failed_once=False,
            image_cls=None,
            pytesseract=None,
        ),
    )
    assert empty_ocr.empty is True


@pytest.mark.asyncio
async def test_extrair_pagina_pdf_impl_returns_image_text_and_table(monkeypatch):
    page = _FakePage(text="descricao da pagina")
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page]),
    )
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [_ImageStub()],
    )
    monkeypatch.setattr(
        file_processing.PdfProcessingWorkflow,
        "extract_data_from_pdf_region",
        lambda self, **kwargs: pd.DataFrame([{"sku": "A1", "nome": "Produto"}]),
    )

    result = await file_processing._FileProcessingImplementation._extrair_pagina_pdf_impl(
        conteudo_pdf=b"pdf-bytes",
        page_number=1,
        region=[1, 2, 3, 4],
    )

    assert result["image"].startswith("data:image/png;base64,")
    assert result["text"] == "descricao da pagina"
    assert result["table"] == [["sku", "nome"], ["A1", "Produto"]]
    assert page.cropped_bbox == (1.0, 2.0, 3.0, 4.0)


@pytest.mark.asyncio
async def test_extrair_pagina_pdf_impl_rejects_invalid_page(monkeypatch):
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([_FakePage(text="")]),
    )

    with pytest.raises(ValueError, match="Numero de pagina invalido|NÃºmero de pÃ¡gina invÃ¡lido"):
        await file_processing._FileProcessingImplementation._extrair_pagina_pdf_impl(
            conteudo_pdf=b"pdf-bytes",
            page_number=2,
            region=None,
        )


@pytest.mark.asyncio
async def test_process_pdf_job_impl_covers_success_missing_and_failure_paths(monkeypatch):
    repo_missing = _FakeRepo(catalog_file=None)
    await file_processing._FileProcessingImplementation._process_pdf_job_impl(
        job_id=1,
        pdf_path="C:/tmp/catalogo.pdf",
        start_page=1,
        mapping={"sku": "sku_original"},
        catalog_file_repository=repo_missing,
    )
    assert repo_missing.updates == []

    catalog_file = SimpleNamespace(
        status=None,
        total_pages=None,
        pages_processed=0,
        result_summary=None,
    )
    repo = _FakeRepo(catalog_file=catalog_file)
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([object(), object(), object(), object(), object(), object()]),
    )

    def fake_extract(file_path, page_number):
        _ = file_path
        if page_number == 2:
            raise RuntimeError("page failed")
        return {"headers": ["raw"], "rows": [{"raw": f"row-{page_number}"}]}

    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_single_page_impl",
        fake_extract,
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping: {"nome_base": row["raw"], "sku_original": row["raw"].upper()},
    )

    await file_processing._FileProcessingImplementation._process_pdf_job_impl(
        job_id=2,
        pdf_path="C:/tmp/catalogo.pdf",
        start_page=1,
        mapping={"sku": "sku_original"},
        catalog_file_repository=repo,
    )

    assert catalog_file.status == "PENDING_REVIEW"
    assert catalog_file.total_pages == 6
    assert catalog_file.pages_processed == 5
    assert len(catalog_file.result_summary["products"]) == 5
    assert repo.updates[0]["status"] == "PROCESSING"
    assert repo.updates[-1]["status"] == "PENDING_REVIEW"

    failing_catalog_file = SimpleNamespace(
        status=None,
        total_pages=None,
        pages_processed=0,
        result_summary=None,
    )
    failing_repo = _FakeRepo(catalog_file=failing_catalog_file)
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pdf exploded")),
    )

    await file_processing._FileProcessingImplementation._process_pdf_job_impl(
        job_id=3,
        pdf_path="C:/tmp/catalogo.pdf",
        start_page=1,
        mapping=None,
        catalog_file_repository=failing_repo,
    )
    assert failing_catalog_file.status == "FAILED"
    assert failing_repo.updates[-1]["status"] == "FAILED"


def test_extract_data_from_single_page_impl_covers_table_text_and_ocr(monkeypatch):
    page_table = _FakePage(tables=[[["sku", "nome"], ["A1", "Produto"]]])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page_table]),
    )
    table_result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    )
    assert table_result == {"headers": ["sku", "nome"], "rows": [["A1", "Produto"]]}

    page_text = _FakePage(text="sku nome\nA1 Produto")
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page_text]),
    )
    text_result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    )
    assert text_result == {"headers": ["sku", "nome"], "rows": [["A1", "Produto"]]}

    class FakePix:
        def tobytes(self):
            return b"image"

    class FakeDoc:
        page_count = 1

        def __init__(self):
            self.closed = False

        def load_page(self, index):
            _ = index
            return SimpleNamespace(get_pixmap=lambda dpi=300: FakePix())

        def close(self):
            self.closed = True

    fake_doc = FakeDoc()
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pdfplumber fail")),
    )
    monkeypatch.setitem(__import__("sys").modules, "fitz", SimpleNamespace(open=lambda path: fake_doc))
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda img: "sku nome\nB2 Produto OCR"),
    )
    import PIL.Image

    monkeypatch.setattr(PIL.Image, "open", lambda stream: object())

    ocr_result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    )
    assert ocr_result == {"headers": ["sku", "nome"], "rows": [["B2", "Produto", "OCR"]]}
    assert fake_doc.closed is True
