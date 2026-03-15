from __future__ import annotations

import builtins
import sys
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _FakePdfPage:
    width = 100.0
    height = 200.0

    def __init__(self, *, text="", tables=None, explode_tables=False):
        self._text = text
        self._tables = tables if tables is not None else []
        self._explode_tables = explode_tables
        self.cropped_bbox = None

    def extract_tables(self, *args, **kwargs):
        if self._explode_tables:
            raise RuntimeError("table explode")
        return self._tables

    def extract_text(self, *args, **kwargs):
        return self._text

    def crop(self, bbox):
        self.cropped_bbox = bbox
        return self


class _FakePdfContext:
    def __init__(self, pdf_obj):
        self._pdf_obj = pdf_obj

    def __enter__(self):
        return self._pdf_obj

    def __exit__(self, exc_type, exc, tb):
        return False


def test_line_mapping_and_helper_workflows_cover_remaining_branches(monkeypatch):
    impl = file_processing._FileProcessingImplementation

    class _LockedPdf(Exception):
        pass

    monkeypatch.setattr(file_processing, "PDFPasswordIncorrect", _LockedPdf, raising=False)
    assert impl._is_pdf_password_error(_LockedPdf("bloqueado")) is True
    assert impl._delete_catalog_file_impl("missing.pdf") is None

    line_runtime = file_processing.LineNormalizationRuntime()
    assert line_runtime.coerce_region_bbox(["a", "b", "c", "d"], 100, 100) == (None, "invalid")
    assert line_runtime.split_sku_nome_auto("ABC123 - Produto") == ("ABC123", "Produto")
    assert line_runtime.split_sku_nome_auto("ABC123 PRODUTO") == ("ABC123", "PRODUTO")

    workflow = file_processing.LineMappingWorkflow()
    result_nome = workflow.processar_linha_padronizada({"nome": "ABC123 Produto Premium"})
    assert result_nome["sku_original"] == "ABC123"
    assert result_nome["nome_base"] == "Produto Premium"

    result_sku = workflow.processar_linha_padronizada({"sku": "ZX9 Produto Tecnico"})
    assert result_sku["sku_original"] == "ZX9"
    assert result_sku["nome_base"] == "Produto Tecnico"

    merged = workflow.processar_linha_padronizada(
        {"nome": "AB12 Produto", "descricao": "Primeira", "coluna_extra": "Segunda"},
        {"coluna_extra": "descricao_original"},
    )
    assert merged["descricao_original"] == "Primeira | Segunda"

    discarded = workflow.processar_linha_padronizada({"coluna_extra": "---"})
    assert discarded["motivo_descarte"] == "Faltam nome_base e sku_original"
    assert workflow.processar_linha_padronizada({})["motivo_descarte"] == "Faltam nome_base e sku_original"
    assert workflow.processar_linha_padronizada({"nome": "---"})["motivo_descarte"] == (
        "nome_base sem conteÃºdo Ãºtil"
    )
    useful_unmapped = workflow.processar_linha_padronizada({"coluna_extra": "Produto Util"})
    assert useful_unmapped["nome_base"] == "Produto Util"

    dynamic_result = workflow.processar_linha_padronizada(
        {"nome": "AB12 Produto", "material_custom": "Aco"},
        {"material_custom": "attr:material"},
    )
    assert dynamic_result["dynamic_attributes"]["material"] == "Aco"

    runtime_wrapper = file_processing.LineMappingRuntime()
    wrapped = runtime_wrapper.processar_linha_padronizada({"nome": "AB12 Produto"})
    assert wrapped["sku_original"] == "AB12"


def test_pdf_text_and_confidence_helpers_cover_remaining_branches():
    runtime = file_processing.PdfIngestionRuntime()

    assert runtime._extract_structured_rows_from_text("") == []
    assert runtime._extract_structured_rows_from_text("Texto simples sem codigo  extra") == []
    assert runtime._is_low_confidence_dataframe(pd.DataFrame()) is True
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": None}])) is True
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": "aa"}])) is True
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": "A1"}])) is False
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": "texto curto"}])) is True
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": "ab", "col_1": "cd"}])) is True
    assert runtime._is_low_confidence_dataframe(pd.DataFrame([{"col_0": "texto alpha beta gamma"}])) is True

    produtos = []
    runtime._append_produto(produtos, None, None)
    runtime._append_produto(produtos, {"nome_base": "Filtro"}, None)
    assert produtos == []
    assert runtime._looks_like_toc_or_page_marker(None) is True
    assert runtime._looks_like_toc_or_page_marker("pagina 2") is True
    assert runtime._is_weak_name_only_identity(None) is True
    assert runtime._is_weak_name_only_identity("___") is True


def test_pdf_ingestion_runtime_builds_prioritized_multimodal_page_context(monkeypatch):
    runtime = file_processing.PdfIngestionRuntime()
    monkeypatch.setenv("PDF_LLM_MAX_PAGE_IMAGES", "2")
    monkeypatch.setenv("PDF_LLM_PAGE_SCAN_LIMIT", "4")
    monkeypatch.setattr(
        file_processing.PdfIngestionRuntime,
        "_render_pdf_page_image_data_url",
        staticmethod(lambda page: f"img://{page._text.split()[0].lower()}"),
    )

    pdf = SimpleNamespace(
        pages=[
            _FakePdfPage(text="Catalogo geral sumario institucional pagina 1"),
            _FakePdfPage(text="Produto Bosch referencia 0580454087B aplicacao motores flex"),
            _FakePdfPage(text="Especificacoes tecnicas codigo SKU 12972WV87B conteudo embalagem"),
            _FakePdfPage(text="Quem somos historia da empresa"),
        ]
    )

    result = runtime._build_pdf_page_image_context_urls(
        pdf=pdf,
        page_numbers=[1, 2, 3, 4],
        current_page_number=2,
        current_page_bbox=None,
    )

    assert result == ["img://produto", "img://especificacoes"]


@pytest.mark.asyncio
async def test_processar_arquivo_pdf_covers_none_pdf_invalid_pages_and_outer_failure(monkeypatch):
    runtime = file_processing.PdfIngestionRuntime()

    monkeypatch.setattr(file_processing.pdfplumber, "open", lambda *args, **kwargs: None)
    result_none_pdf = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        extraction_mode="modo-invalido",
    )
    assert "Falha desconhecida" in result_none_pdf[0]["erro_processamento_pdf"]

    page = _FakePdfPage(text="", tables=[], explode_tables=True)
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(SimpleNamespace(pages=[page])),
    )
    result_outer = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        extraction_mode="ocr",
    )
    assert "Falha critica ao ler arquivo PDF" in result_outer[0]["erro_processamento_pdf"]

    page_valid = _FakePdfPage(text="", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(SimpleNamespace(pages=[page_valid])),
    )
    result_invalid_page = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        pages=[2],
        extraction_mode="ocr",
    )
    assert "Nenhum dado de produto pode ser extraido" in result_invalid_page[0]["erro_processamento_pdf"]


@pytest.mark.asyncio
async def test_processar_arquivo_pdf_covers_region_table_and_text_fallback_branches(monkeypatch, tmp_path):
    runtime = file_processing.PdfIngestionRuntime()
    page = _FakePdfPage(
        text="SKU123 Produto Completo",
        tables=[[], [["sku"], ["A1", "Produto"]]],
    )
    pdf_obj = SimpleNamespace(pages=[page])

    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(pdf_obj),
    )

    region_calls = {"count": 0}

    def fake_region_extract(**kwargs):
        region_calls["count"] += 1
        if region_calls["count"] == 1:
            raise RuntimeError("region failed")
        if region_calls["count"] == 2:
            raise RuntimeError("fallback failed")
        return pd.DataFrame()

    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_pdf_region_impl",
        fake_region_extract,
    )

    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping=None: {"nome_base": row.get("nome_base"), "sku_original": row.get("sku_original")},
    )
    monkeypatch.setattr(
        runtime,
        "_extract_structured_rows_from_text",
        lambda page_text: [{"nome_base": "Texto Produto", "sku_original": "TXT-1"}],
    )

    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        pages=[1],
        region=[0.1, 0.1, 0.9, 0.9],
        extraction_mode="ocr",
    )

    assert result == [{"nome_base": "Texto Produto", "sku_original": "TXT-1"}]
    assert page.cropped_bbox == (10.0, 20.0, 90.0, 180.0)


@pytest.mark.asyncio
async def test_tabular_ingestion_runtime_covers_product_type_and_csv_fallbacks(monkeypatch):
    runtime = file_processing.TabularIngestionRuntime()

    class _FakeDataFrame:
        def __init__(self, rows):
            self._rows = rows

        def dropna(self, how="all", inplace=True):
            _ = how, inplace
            return None

        def iterrows(self):
            for idx, row in enumerate(self._rows):
                yield idx, SimpleNamespace(to_dict=lambda row=row: row)

    monkeypatch.setattr(
        file_processing.TabularIngestionEngineRuntime,
        "_parse_excel_records_in_subprocess",
        lambda self, **kwargs: {
            "ok": True,
            "records": [{"nome": "AB12 Produto"}, {"nome": None}],
        },
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping=None: (
            {"nome_base": "Produto", "sku_original": "AB12"} if row.get("nome") else None
        ),
    )
    excel_result = await runtime.processar_arquivo_excel(
        b"PK\x03\x04xlsx",
        product_type_id=9,
    )
    assert excel_result == [{"nome_base": "Produto", "sku_original": "AB12", "product_type_id": 9}]

    monkeypatch.setattr(
        file_processing.TabularIngestionEngineRuntime,
        "_parse_csv_records_in_subprocess",
        lambda self, **kwargs: {
            "ok": True,
            "records": [{"nome": "CSV Produto"}],
        },
    )
    csv_result = await runtime.processar_arquivo_csv(
        "nome;valor\nCSV Produto;10".encode("latin-1"),
        product_type_id=5,
    )
    assert csv_result == [{"nome_base": "Produto", "sku_original": "AB12", "product_type_id": 5}]


@pytest.mark.asyncio
async def test_processar_arquivo_pdf_covers_invalid_bbox_and_region_rows(monkeypatch):
    runtime = file_processing.PdfIngestionRuntime()
    page = _FakePdfPage(text="", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(SimpleNamespace(pages=[page])),
    )

    def fake_region_extract(**kwargs):
        if kwargs.get("region") is None:
            return pd.DataFrame()
        return pd.DataFrame([{"nome_base": "Produto Regiao", "sku_original": "REG-1"}])

    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_pdf_region_impl",
        fake_region_extract,
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping=None: row,
    )

    result_invalid_bbox = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        pages=[1],
        region=[0.9, 0.9, 0.1, 0.1],
        extraction_mode="ocr",
    )
    assert "Nenhum dado de produto pode ser extraido" in result_invalid_bbox[0]["erro_processamento_pdf"]

    result_region = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        pages=[1],
        region=[0.1, 0.1, 0.9, 0.9],
        extraction_mode="ocr",
    )
    assert result_region == [{"nome_base": "Produto Regiao", "sku_original": "REG-1"}]


@pytest.mark.asyncio
async def test_processar_arquivo_pdf_covers_structured_text_without_identity_and_llm_success(monkeypatch):
    page = _FakePdfPage(text=" ".join(["texto"] * 30), tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(SimpleNamespace(pages=[page])),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_pdf_region_impl",
        lambda **kwargs: pd.DataFrame(),
    )

    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(
            extrair_dados_produto_com_llm=lambda text: SimpleNamespace()
        )
    )

    rows = [{"descricao_original": "sem identidade"}]
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: rows)
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping=None: row,
    )
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        extraction_mode="ocr",
    )
    assert "Nenhum dado de produto pode ser extraido" in result[0]["erro_processamento_pdf"]

    async def fake_llm(**kwargs):
        assert kwargs["texto_pagina"]
        assert kwargs["page_image_data_urls"]
        return {"nome_base": "Produto via LLM", "sku_original": "LLM-1"}

    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(extrair_dados_produto_com_llm=fake_llm)
    )
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    monkeypatch.setattr(runtime, "_render_pdf_page_image_data_url", lambda page: "data:image/png;base64,AAA")
    monkeypatch.setattr(runtime, "_build_pdf_page_image_context_urls", lambda **kwargs: ["data:image/png;base64,AAA"])
    result_llm = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=True,
        extraction_mode="ia",
    )
    assert result_llm[0]["nome_base"] == "Produto via LLM"

    captured = {}

    async def fake_visual_llm(**kwargs):
        captured.update(kwargs)
        return {"nome_base": "Produto via Visao", "sku_original": "VIS-1"}

    page_no_text = _FakePdfPage(text="", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext(SimpleNamespace(pages=[page_no_text])),
    )
    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(extrair_dados_produto_com_llm=fake_visual_llm)
    )
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    monkeypatch.setattr(runtime, "_render_pdf_page_image_data_url", lambda page: "data:image/png;base64,AAA")
    monkeypatch.setattr(runtime, "_build_pdf_page_image_context_urls", lambda **kwargs: ["data:image/png;base64,AAA"])
    result_visual = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=True,
        extraction_mode="ia",
    )
    assert result_visual[0]["nome_base"] == "Produto via Visao"
    assert captured["texto_pagina"] is None
    assert captured["page_image_data_url"] == "data:image/png;base64,AAA"
    assert captured["page_image_data_urls"] == ["data:image/png;base64,AAA"]
