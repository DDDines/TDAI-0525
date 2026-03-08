"""Focused coverage for preview/PDF utility branches in file processing runtime."""

from __future__ import annotations

import base64
from types import SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _FakeImage:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def save(self, buffer, format=None):  # noqa: A002
        _ = format
        buffer.write(self.payload)


@pytest.mark.asyncio
async def test_preview_extractors_and_factory_delegate():
    calls = []

    class FakeTabularRuntime:
        async def preview_arquivo_excel(self, **kwargs):
            calls.append(("excel", kwargs))
            return {"kind": "excel", "rows": kwargs["max_rows"]}

        async def preview_arquivo_csv(self, **kwargs):
            calls.append(("csv", kwargs))
            return {"kind": "csv", "rows": kwargs["max_rows"]}

    class FakePdfRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            calls.append(("pdf", kwargs))
            return {"kind": "pdf", "ext": kwargs["ext"]}

    excel_extractor = file_processing._ExcelPreviewExtractor(FakeTabularRuntime())
    csv_extractor = file_processing._CsvPreviewExtractor(FakeTabularRuntime())
    pdf_extractor = file_processing._PdfPreviewExtractor(FakePdfRuntime())
    factory = file_processing._PreviewExtractorFactory(
        excel_extractor=excel_extractor,
        csv_extractor=csv_extractor,
        pdf_extractor=pdf_extractor,
    )

    assert factory.get_extractor(".xlsx") is excel_extractor
    assert factory.get_extractor(".xls") is excel_extractor
    assert factory.get_extractor(".csv") is csv_extractor
    assert factory.get_extractor(".pdf") is pdf_extractor

    assert await excel_extractor.extract(conteudo_arquivo=b"x", ext=".xlsx", max_rows=4) == {"kind": "excel", "rows": 4}
    assert await csv_extractor.extract(conteudo_arquivo=b"y", ext=".csv", max_rows=5) == {"kind": "csv", "rows": 5}
    assert await pdf_extractor.extract(conteudo_arquivo=b"z", ext=".pdf", max_rows=99) == {"kind": "pdf", "ext": ".pdf"}

    with pytest.raises(ValueError):
        factory.get_extractor(".bin")

    with pytest.raises(NotImplementedError):
        await file_processing._PreviewExtractor().extract(conteudo_arquivo=b"1", ext=".txt", max_rows=1)

    assert calls == [
        ("excel", {"conteudo_arquivo": b"x", "max_rows": 4}),
        ("csv", {"conteudo_arquivo": b"y", "max_rows": 5}),
        ("pdf", {"conteudo_arquivo": b"z", "ext": ".pdf", "start_page": 1, "page_count": 1}),
    ]


def test_pdf_image_conversion_runtime_helpers(monkeypatch):
    runtime = file_processing.PdfImageConversionRuntime()

    monkeypatch.setenv("POPPLER_PATH", "C:/poppler/bin")
    monkeypatch.setattr(file_processing.settings, "POPPLER_PATH", None, raising=False)
    assert runtime._resolve_poppler_path() == "C:/poppler/bin"

    monkeypatch.delenv("POPPLER_PATH", raising=False)
    monkeypatch.setattr(file_processing.settings, "POPPLER_PATH", "D:/poppler", raising=False)
    assert runtime._resolve_poppler_path() == "D:/poppler"

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: None)
    with pytest.raises(RuntimeError, match="Poppler"):
        runtime._ensure_poppler_available("C:/missing")

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: f"{path or 'PATH'}/{exe}")
    assert runtime._ensure_poppler_available("C:/ok") == "C:/ok"

    received = {}
    monkeypatch.setattr(runtime, "_resolve_poppler_path", lambda: "C:/resolved")
    monkeypatch.setattr(runtime, "_ensure_poppler_available", lambda path: path)

    def fake_convert_from_bytes(conteudo_arquivo, **kwargs):
        received["conteudo_arquivo"] = conteudo_arquivo
        received.update(kwargs)
        return [_FakeImage(b"img-a"), _FakeImage(b"img-b")]

    monkeypatch.setattr(file_processing, "convert_from_bytes", fake_convert_from_bytes)
    result = runtime._convert_sync(b"pdf", max_pages=0, start_page=3, dpi=144)

    assert result == [
        base64.b64encode(b"img-a").decode(),
        base64.b64encode(b"img-b").decode(),
    ]
    assert received == {
        "conteudo_arquivo": b"pdf",
        "first_page": 3,
        "last_page": None,
        "dpi": 144,
        "fmt": "png",
        "poppler_path": "C:/resolved",
    }


def test_pdf_region_utils_cover_remaining_branches():
    utils = file_processing._PdfRegionExtractionUtils

    assert utils.make_unique(["Codigo", "Codigo", None, ""]) == ["Codigo", "Codigo_1", "col", "col_1"]

    empty_df = utils.clean_df(pd.DataFrame())
    assert empty_df.empty is True

    cleaned = utils.clean_df(pd.DataFrame([[None, "x"], [None, None], ["y", None]], columns=["drop", "keep"]))
    assert list(cleaned.columns) == ["drop", "keep"]
    assert cleaned.iloc[0].tolist() == ["", "x"]
    assert cleaned.iloc[1].tolist() == ["y", ""]

    assert utils.median_int([], 9) == 9
    assert utils.median_int([1, 5, 3], 0) == 3
    assert utils.median_int([2, 6, 8, 10], 0) == 7
    assert utils.cluster_positions([10, 12, 30, 65, 70], tolerance=5) == [10, 30, 65]
    assert utils.normalize_ocr_snippet("Descri\u00e7\u00e3o \u00e7\u00e3 10%") == "DESCRICAO CA 10"

    assert utils.header_field_for_text("") is None
    assert utils.header_field_for_text("FAB") == "n_fab"
    assert utils.header_field_for_text("Original") == "n_original"
    assert utils.header_field_for_text("Descr.") == "descricao"
    assert utils.header_field_for_text("Aplicacao") == "aplicacao"
    assert utils.header_field_for_text("MAT") == "material"
    assert utils.header_field_for_text("Desconhecido") is None

    assert utils.detect_header_columns([]) is None
    merged_lines = [
        [{"text": "FAB ORIGINAL DESCR APLIC MATERIAL", "x0": 10, "x1": 110}],
        [
            {"text": "FAB", "x0": 15, "x1": 25},
            {"text": "DESCR", "x0": 60, "x1": 120},
            {"text": "MATERIAL", "x0": 180, "x1": 230},
        ],
    ]
    detected = utils.detect_header_columns(merged_lines)
    assert detected["line_idx"] == 0
    assert detected["headers"] == ["n_fab", "n_original", "descricao", "aplicacao", "material"]
    assert len(detected["bounds"]) == 5
    assert detected["score"] == 5

    assert utils.is_header_like_row("fab original descr") is True
    assert utils.is_header_like_row("produto comum") is False

    raw_rows = [
        {"a": "", "b": ""},
        {"a": "FAB ORIGINAL", "b": "DESCR"},
        {"a": "-", "b": ""},
        {"a": "A", "b": ""},
        {"a": "SKU123", "b": "Produto Teste"},
    ]
    assert utils.filter_ocr_rows(raw_rows) == [{"a": "SKU123", "b": "Produto Teste"}]

    df = utils.tables_to_df([
        [["Codigo", "Descricao", "Descricao"], ["1", "Pastilha", "Dianteira"], ["2", "Disco"]],
        None,
    ])
    assert list(df.columns) == ["Codigo", "Descricao", "Descricao_1"]
    assert df.iloc[1].tolist() == ["2", "Disco", ""]

    line_grouped = utils.group_words_by_line_ids([
        {"block": 1, "par": 1, "line": 2, "y": 40},
        {"block": 1, "par": 1, "line": 1, "y": 10},
        {"block": 1, "par": 1, "line": 0, "y": 5},
        {"block": 2, "par": 1, "line": 1, "y": 25},
    ])
    assert [len(line) for line in line_grouped] == [1, 1, 1]
    assert line_grouped[0][0]["y"] == 10
    assert line_grouped[1][0]["y"] == 25
    assert line_grouped[2][0]["y"] == 40

    assert utils.group_words_by_y([]) == []
    grouped_by_y = utils.group_words_by_y([
        {"text": "B", "x": 30, "y": 12, "h": 10},
        {"text": "A", "x": 10, "y": 10, "h": 10},
        {"text": "C", "x": 15, "y": 40, "h": 20},
    ])
    assert [len(line) for line in grouped_by_y] == [2, 1]

    assert utils.merge_words_in_line([]) == []
    merged = utils.merge_words_in_line([
        {"text": "ABC", "x": 10, "w": 15},
        {"text": "123", "x": 28, "w": 15},
        {"text": "Produto", "x": 80, "w": 30},
        {"text": "", "x": 120, "w": 10},
    ])
    assert merged == [
        {"x0": 10, "x1": 43, "text": "ABC 123"},
        {"x0": 80, "x1": 110, "text": "Produto"},
    ]


def test_pdf_asset_utility_runtime_parses_annotation_and_wraps_failures():
    runtime = file_processing.PdfAssetUtilityRuntime()

    annotation = SimpleNamespace(
        pages=[
            SimpleNamespace(
                blocks=[
                    SimpleNamespace(
                        paragraphs=[
                            SimpleNamespace(
                                words=[
                                    SimpleNamespace(
                                        symbols=[SimpleNamespace(text="A"), SimpleNamespace(text="1")],
                                        bounding_box=SimpleNamespace(vertices=[SimpleNamespace(x=10, y=10), SimpleNamespace(x=20, y=10)]),
                                    ),
                                    SimpleNamespace(
                                        symbols=[SimpleNamespace(text="B")],
                                        bounding_box=SimpleNamespace(vertices=[SimpleNamespace(x=80, y=12), SimpleNamespace(x=90, y=12)]),
                                    ),
                                    SimpleNamespace(
                                        symbols=[SimpleNamespace(text="C")],
                                        bounding_box=SimpleNamespace(vertices=[SimpleNamespace(x=12, y=40), SimpleNamespace(x=22, y=40)]),
                                    ),
                                ]
                            )
                        ]
                    )
                ]
            )
        ]
    )

    df = runtime.parse_annotation_to_dataframe(annotation, vertical_tolerance=5)
    assert list(df.columns) == ["col_1", "col_2"]
    assert df.iloc[0].tolist() == ["A1", "B"]
    assert df.iloc[1].tolist() == ["C", ""]
    assert runtime.parse_annotation_to_dataframe(SimpleNamespace(pages=[])).empty is True

    broken_annotation = SimpleNamespace(
        pages=[
            SimpleNamespace(
                blocks=[
                    SimpleNamespace(
                        paragraphs=[
                            SimpleNamespace(words=[SimpleNamespace(symbols=[])])
                        ]
                    )
                ]
            )
        ]
    )
    with pytest.raises(file_processing.HTTPException) as exc:
        runtime.parse_annotation_to_dataframe(broken_annotation)
    assert exc.value.status_code == 500
