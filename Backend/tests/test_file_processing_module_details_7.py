from __future__ import annotations

from types import SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _PdfContext:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeImage:
    width = 100
    height = 100

    def save(self, destination, format=None, **kwargs):
        _ = format, kwargs
        destination.write(b"img")

    def convert(self, mode):
        _ = mode
        return self

    def filter(self, filter_obj):
        _ = filter_obj
        return self

    def getdata(self):
        return [200] * (self.width * self.height)

    def point(self, func):
        _ = func
        return self


class _RenderedPage:
    original = _FakeImage()


class _FakePage:
    width = 100.0
    height = 200.0

    def __init__(self, *, tables=None, text=""):
        self._tables = tables if tables is not None else []
        self._text = text

    def extract_tables(self, table_settings=None):
        _ = table_settings
        return self._tables

    def extract_text(self):
        return self._text

    def crop(self, bbox):
        _ = bbox
        return self

    def to_image(self, resolution):
        _ = resolution
        return _RenderedPage()


def test_extract_data_from_pdf_region_impl_covers_empty_text_guided_empty_and_cluster_resize(monkeypatch):
    import PIL.ImageEnhance
    import PIL.ImageOps

    monkeypatch.setattr(PIL.ImageOps, "autocontrast", lambda image: image)
    monkeypatch.setattr(
        PIL.ImageEnhance,
        "Contrast",
        lambda image: SimpleNamespace(enhance=lambda factor: image),
    )
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([_FakePage(text="sku nome\nA1 Produto", tables=[])]),
    )

    helper = file_processing._PdfRegionExtractionUtils
    clean_calls = {"count": 0}

    def fake_clean_df(df):
        clean_calls["count"] += 1
        if clean_calls["count"] <= 2:
            return pd.DataFrame(columns=df.columns)
        return df

    cluster_calls = {"count": 0}

    def fake_cluster_positions(positions, tolerance):
        _ = positions, tolerance
        cluster_calls["count"] += 1
        if cluster_calls["count"] == 1:
            return list(range(17))
        return [0]

    merged_lines = [
        [{"text": "SKU", "x": 0, "x0": 0}, {"text": "Nome", "x": 150, "x0": 150}],
        [{"text": "A1", "x": 0, "x0": 0}, {"text": "Produto", "x": 150, "x0": 150}],
    ]
    monkeypatch.setattr(helper, "clean_df", fake_clean_df)
    monkeypatch.setattr(helper, "group_words_by_line_ids", lambda words: merged_lines)
    monkeypatch.setattr(
        helper,
        "merge_words_in_line",
        lambda line_words: [{"x0": item["x0"], "text": item["text"]} for item in line_words],
    )
    monkeypatch.setattr(
        helper,
        "detect_header_columns",
        lambda lines: {"headers": ["sku"], "bounds": [0], "line_idx": 0},
    )
    monkeypatch.setattr(helper, "filter_ocr_rows", lambda rows: rows)
    monkeypatch.setattr(helper, "cluster_positions", fake_cluster_positions)

    ocr_state = SimpleNamespace(
        available=True,
        exec_available=True,
        exec_failed_once=False,
        image_cls=SimpleNamespace(open=lambda stream: _FakeImage()),
        pytesseract=SimpleNamespace(
            Output=SimpleNamespace(DICT=object()),
            image_to_data=lambda img, output_type, config: {
                "text": ["SKU", "Nome", "A1", "Produto"],
                "conf": ["95", "95", "95", "95"],
                "left": [0, 150, 0, 150],
                "top": [0, 0, 20, 20],
                "width": [20, 20, 20, 20],
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

    assert clean_calls["count"] == 3
    assert cluster_calls["count"] == 2
    assert list(df.columns) == ["col_0"]
    assert not df.empty


def test_extract_data_from_single_page_impl_uses_ocr_after_single_text_line(monkeypatch):
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([_FakePage(text="linha unica", tables=[])]),
    )

    class _Doc:
        page_count = 1

        def load_page(self, index):
            _ = index
            return SimpleNamespace(get_pixmap=lambda dpi=300: SimpleNamespace(tobytes=lambda: b"img"))

        def close(self):
            return None

    monkeypatch.setitem(__import__("sys").modules, "fitz", SimpleNamespace(open=lambda path: _Doc()))
    monkeypatch.setitem(
        __import__("sys").modules,
        "pytesseract",
        SimpleNamespace(image_to_string=lambda img: "sku nome\nA1 Produto OCR"),
    )
    import PIL.Image

    monkeypatch.setattr(PIL.Image, "open", lambda stream: object())

    result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    )

    assert result == {"headers": ["sku", "nome"], "rows": [["A1", "Produto", "OCR"]]}


def test_ocr_runtime_state_covers_detected_binary_and_missing_candidate_paths(monkeypatch):
    fake_pytesseract = SimpleNamespace(
        pytesseract=SimpleNamespace(tesseract_cmd=None),
        get_tesseract_version=lambda: "5.0",
    )
    monkeypatch.setitem(__import__("sys").modules, "pytesseract", fake_pytesseract)
    monkeypatch.setitem(__import__("sys").modules, "PIL.Image", object())

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe: "C:/bin/tesseract.exe")
    state_with_binary = file_processing.OcrRuntimeState()
    assert state_with_binary.available is True
    assert fake_pytesseract.pytesseract.tesseract_cmd is None

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe: None)
    monkeypatch.setattr(file_processing.os.path, "exists", lambda path: False)
    state_without_candidate = file_processing.OcrRuntimeState()
    assert state_without_candidate.available is True
    assert fake_pytesseract.pytesseract.tesseract_cmd is None


def test_line_mapping_workflow_covers_reused_identity_paths():
    workflow = file_processing.LineMappingWorkflow()

    preserved_name = workflow.processar_linha_padronizada(
        {
            "sku_existing": "KEEP",
            "sku_inferido": "AB12 Nome Novo",
        },
        {
            "sku_existing": "sku_original",
            "sku_inferido": "sku_original",
        },
    )
    assert preserved_name["sku_original"] == "KEEP"
    assert preserved_name["nome_base"] == "Nome Novo"

    preserved_field = workflow.processar_linha_padronizada(
        {
            "sku": "ZX9",
            "marca_1": "Marca A",
            "marca_2": "Marca B",
        },
        {
            "sku": "sku_original",
            "marca_1": "marca",
            "marca_2": "marca",
        },
    )
    assert preserved_field["marca"] == "Marca A"


@pytest.mark.asyncio
async def test_csv_ingestion_runtime_keeps_comma_when_sniffer_fails(monkeypatch):
    runtime = file_processing.TabularIngestionRuntime()

    monkeypatch.setattr(
        file_processing.csv.Sniffer,
        "sniff",
        lambda self, sample: (_ for _ in ()).throw(RuntimeError("no sniff")),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        staticmethod(lambda row, mapping: {"sku_original": row.get("sku"), "nome_base": row.get("nome")}),
    )

    result = await runtime.processar_arquivo_csv(b"sku,nome\nA1,Produto")

    assert result == [{"sku_original": "A1", "nome_base": "Produto"}]


def test_pdf_ingestion_runtime_covers_false_paths_for_small_dataset_heuristic():
    runtime = file_processing.PdfIngestionRuntime()

    assert runtime._is_low_confidence_dataframe(
        pd.DataFrame(
            [
                {"col_0": "a-b-c-d-1 e-f-g-h-2 i-j-k-l-3 m-n-o-p-4"},
            ]
        )
    ) is False
