from __future__ import annotations

import io
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _FakeImage:
    def save(self, destination, format=None, **kwargs):
        _ = format, kwargs
        if hasattr(destination, "write"):
            destination.write(b"img")
            return
        Path(destination).write_bytes(b"img")

    def convert(self, mode):
        _ = mode
        return self


class _FakeRenderedPage:
    original = _FakeImage()


class _FakePage:
    width = 100.0
    height = 200.0

    def __init__(self, *, text="", tables=None):
        self._text = text
        self._tables = tables if tables is not None else []

    def extract_tables(self, *args, **kwargs):
        return self._tables

    def extract_text(self, *args, **kwargs):
        return self._text

    def crop(self, bbox):
        _ = bbox
        return self

    def to_image(self, resolution):
        _ = resolution
        return _FakeRenderedPage()


class _FakePdfContext:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def _patch_pdfplumber(monkeypatch, page):
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([page]),
    )


def test_extract_data_from_pdf_region_impl_covers_remaining_ocr_paths(monkeypatch):
    import PIL.ImageEnhance
    import PIL.ImageOps

    monkeypatch.setattr(PIL.ImageOps, "autocontrast", lambda image: image)
    monkeypatch.setattr(
        PIL.ImageEnhance,
        "Contrast",
        lambda image: SimpleNamespace(enhance=lambda factor: image),
    )

    page = _FakePage(text="", tables=[])
    _patch_pdfplumber(monkeypatch, page)

    df_no_image_class = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=SimpleNamespace(
            available=True,
            exec_available=True,
            exec_failed_once=False,
            image_cls=None,
            pytesseract=SimpleNamespace(),
        ),
    )
    assert df_no_image_class.empty is True

    df_no_pytesseract = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=SimpleNamespace(
            available=True,
            exec_available=True,
            exec_failed_once=False,
            image_cls=SimpleNamespace(open=lambda stream: _FakeImage()),
            pytesseract=None,
        ),
    )
    assert df_no_pytesseract.empty is True

    exploding_state = SimpleNamespace(
        available=True,
        exec_available=True,
        exec_failed_once=False,
        image_cls=SimpleNamespace(open=lambda stream: _FakeImage()),
        pytesseract=SimpleNamespace(
            Output=SimpleNamespace(DICT=object()),
            image_to_data=lambda img, output_type, config: (_ for _ in ()).throw(RuntimeError("ocr broke")),
        ),
    )
    first_empty = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=exploding_state,
    )
    second_empty = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=exploding_state,
    )
    assert first_empty.empty is True
    assert second_empty.empty is True
    assert exploding_state.exec_failed_once is True


def test_extract_data_from_pdf_region_impl_covers_header_cluster_and_empty_segments(monkeypatch):
    import PIL.ImageEnhance
    import PIL.ImageOps

    monkeypatch.setattr(PIL.ImageOps, "autocontrast", lambda image: image)
    monkeypatch.setattr(
        PIL.ImageEnhance,
        "Contrast",
        lambda image: SimpleNamespace(enhance=lambda factor: image),
    )

    page = _FakePage(text="", tables=[])
    _patch_pdfplumber(monkeypatch, page)

    helper = file_processing._PdfRegionExtractionUtils
    monkeypatch.setattr(helper, "group_words_by_line_ids", lambda words: [])
    monkeypatch.setattr(helper, "group_words_by_y", lambda words: [[{"x": 0, "w": 5, "x0": 0, "text": "A"}]])
    merge_calls = {"count": 0}

    def fake_merge(line_words):
        merge_calls["count"] += 1
        if merge_calls["count"] == 1:
            return []
        return [{"x0": 0, "x1": 5, "text": "A"}]

    monkeypatch.setattr(helper, "merge_words_in_line", fake_merge)

    ocr_state = SimpleNamespace(
        available=True,
        exec_available=True,
        exec_failed_once=False,
        image_cls=SimpleNamespace(open=lambda stream: _FakeImage()),
        pytesseract=SimpleNamespace(
            Output=SimpleNamespace(DICT=object()),
            image_to_data=lambda img, output_type, config: {
                "text": ["A", "B"],
                "conf": ["bad", "10"],
                "left": [0, 10],
                "top": [0, 0],
                "width": [5, 5],
                "height": [5, 5],
                "block_num": [1, 1],
                "par_num": [1, 1],
                "line_num": [0, 0],
            },
        ),
    )

    df_empty_segments = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=ocr_state,
    )
    assert df_empty_segments.empty is True

    monkeypatch.setattr(helper, "merge_words_in_line", lambda line_words: [{"x0": 0, "x1": 5, "text": "AA"}])
    monkeypatch.setattr(
        helper,
        "detect_header_columns",
        lambda lines: {"headers": ["sku"], "bounds": [0], "line_idx": 0},
    )

    rich_ocr_state = SimpleNamespace(
        available=True,
        exec_available=True,
        exec_failed_once=False,
        image_cls=SimpleNamespace(open=lambda stream: _FakeImage()),
        pytesseract=SimpleNamespace(
            Output=SimpleNamespace(DICT=object()),
            image_to_data=lambda img, output_type, config: {
                "text": ["SKU", "PRODUTO"],
                "conf": ["95", "95"],
                "left": [0, 20],
                "top": [0, 0],
                "width": [10, 10],
                "height": [10, 10],
                "block_num": [1, 1],
                "par_num": [1, 1],
                "line_num": [1, 1],
            },
        ),
    )
    monkeypatch.setattr(helper, "filter_ocr_rows", lambda rows: [])
    guided_empty_df = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=rich_ocr_state,
    )
    assert guided_empty_df.empty is True

    monkeypatch.setattr(helper, "filter_ocr_rows", lambda rows: rows)
    monkeypatch.setattr(helper, "cluster_positions", lambda positions, tolerance: [])
    monkeypatch.setattr(helper, "clean_df", lambda df: df)
    df_cluster = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=rich_ocr_state,
    )
    assert list(df_cluster.columns) == ["col_0"]


@pytest.mark.asyncio
async def test_pdf_page_and_job_helpers_cover_cleanup_and_required_repo(monkeypatch):
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([_FakePage(text="pagina sem tabela")]),
    )
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [_FakeImage()],
    )
    monkeypatch.setattr(
        file_processing.PdfProcessingWorkflow,
        "extract_data_from_pdf_region",
        lambda self, **kwargs: pd.DataFrame(),
    )
    original_unlink = Path.unlink
    monkeypatch.setattr(Path, "unlink", lambda self: (_ for _ in ()).throw(OSError("locked")))

    page_payload = await file_processing._FileProcessingImplementation._extrair_pagina_pdf_impl(
        conteudo_pdf=b"pdf",
        page_number=1,
        region=None,
    )
    assert page_payload["table"] is None

    monkeypatch.setattr(Path, "unlink", original_unlink)

    with pytest.raises(ValueError, match="catalog_file_repository is required"):
        await file_processing._FileProcessingImplementation._process_pdf_job_impl(
            job_id=1,
            pdf_path="C:/tmp/catalogo.pdf",
            start_page=1,
            mapping=None,
            catalog_file_repository=None,
        )


def test_single_page_ocr_and_ocr_runtime_cover_remaining_branches(monkeypatch):
    class _FakeDoc:
        page_count = 1

        def __init__(self):
            self.closed = False

        def load_page(self, index):
            _ = index
            return SimpleNamespace(get_pixmap=lambda dpi=300: SimpleNamespace(tobytes=lambda: b"img"))

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("pdfplumber fail")),
    )
    monkeypatch.setitem(__import__("sys").modules, "fitz", SimpleNamespace(open=lambda path: _FakeDoc()))
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda img: ""),
    )
    import PIL.Image

    monkeypatch.setattr(PIL.Image, "open", lambda stream: object())
    assert file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    ) == {"headers": [], "rows": []}

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe: None)
    monkeypatch.setattr(file_processing.os.path, "exists", lambda path: path.endswith("Tesseract-OCR\\tesseract.exe"))

    class _PytesseractModule:
        class pytesseract:
            tesseract_cmd = None

        @staticmethod
        def get_tesseract_version():
            return "5.0"

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", _PytesseractModule())
    import PIL.Image

    monkeypatch.setitem(__import__("sys").modules, "PIL.Image", PIL.Image)
    state_ok = file_processing.OcrRuntimeState()
    assert state_ok.available is True
    assert state_ok.exec_available is True

    class _BrokenPytesseractModule:
        class pytesseract:
            tesseract_cmd = None

        @staticmethod
        def get_tesseract_version():
            raise RuntimeError("sem tesseract")

    monkeypatch.setitem(__import__("sys").modules, "pytesseract", _BrokenPytesseractModule())
    state_fail = file_processing.OcrRuntimeState()
    assert state_fail.available is False
