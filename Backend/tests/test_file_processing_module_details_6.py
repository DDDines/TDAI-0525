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


class _FakePage:
    def __init__(self, *, tables=None, text=""):
        self._tables = tables if tables is not None else []
        self._text = text

    def extract_tables(self, table_settings=None):
        _ = table_settings
        return self._tables

    def extract_text(self):
        return self._text


def test_extract_data_from_single_page_impl_handles_invalid_pages_and_close_failures(monkeypatch):
    page = _FakePage()
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page]),
    )

    class _Doc:
        page_count = 1

        def close(self):
            raise RuntimeError("close failed")

    monkeypatch.setitem(__import__("sys").modules, "fitz", SimpleNamespace(open=lambda path: _Doc()))
    monkeypatch.setitem(__import__("sys").modules, "pytesseract", SimpleNamespace(image_to_string=lambda img: ""))
    import PIL.Image

    monkeypatch.setattr(PIL.Image, "open", lambda stream: object())

    result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=2,
    )

    assert result == {"headers": [], "rows": []}


def test_extract_data_from_single_page_impl_skips_sparse_tables_and_returns_text_rows(monkeypatch):
    page = _FakePage(
        tables=[
            [["sku"]],
            [["sku", "nome"], ["", ""]],
        ],
        text="sku nome\nA1 Produto",
    )
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([page]),
    )

    result = file_processing._FileProcessingImplementation._extract_data_from_single_page_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
    )

    assert result == {"headers": ["sku", "nome"], "rows": [["A1", "Produto"]]}


def test_pdf_pages_to_images_impl_returns_empty_batch_when_offset_is_beyond_total_pages(tmp_path, monkeypatch):
    monkeypatch.setattr(file_processing.settings, "UPLOAD_DIRECTORY", str(tmp_path / "uploads"), raising=False)
    monkeypatch.setattr(file_processing.settings, "PREVIEW_DIRECTORY", str(tmp_path / "previews"), raising=False)
    monkeypatch.setattr(file_processing.shutil, "which", lambda *args, **kwargs: "pdftoppm")
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([object(), object()]),
    )

    upload = SimpleNamespace(
        filename="catalogo.pdf",
        file=SimpleNamespace(read=lambda: b"pdf", close=lambda: None),
    )

    class _Repo:
        def __init__(self, _db):
            pass

        def create_catalog_import_file(self, **kwargs):
            return SimpleNamespace(id=77)

    monkeypatch.setattr(file_processing, "FornecedorRepository", _Repo)
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("should not convert")),
    )

    result = file_processing._FileProcessingImplementation._pdf_pages_to_images_impl(
        db=object(),
        file=upload,
        fornecedor_id=1,
        user_id=2,
        offset=5,
        limit=2,
    )

    assert result == {"image_urls": [], "total_pages": 2, "import_file_id": 77}


def test_line_normalization_runtime_covers_exception_and_mapping_skip_paths():
    runtime = file_processing.LineNormalizationRuntime()

    class _BrokenStr:
        def __str__(self):
            raise RuntimeError("broken")

    assert runtime.limpar_valor_extraido(_BrokenStr()) is None
    assert runtime.valor_tem_conteudo_util(None) is False
    assert runtime.valor_tem_conteudo_util("   ") is False
    assert runtime.normalizar_mapeamento_usuario(
        {
            None: "nome_base",
            "sku_original": None,
            "descricao_original": "   ",
            "nome_base": "COL_0",
        },
        {},
    ) == {"nome_base": "COL_0"}


@pytest.mark.asyncio
async def test_csv_ingestion_runtime_uses_tab_delimiter_and_skips_empty_rows(monkeypatch):
    runtime = file_processing.TabularIngestionRuntime()
    calls = []

    def fake_process(row, mapping):
        _ = mapping
        calls.append(dict(row))
        if row.get("sku") == "A1":
            return None
        return {"nome_base": row.get("nome"), "sku_original": row.get("sku")}

    monkeypatch.setattr(file_processing.csv.Sniffer, "sniff", lambda self, sample: (_ for _ in ()).throw(RuntimeError("no sniff")))
    monkeypatch.setattr(file_processing._FileProcessingImplementation, "_processar_linha_padronizada", staticmethod(fake_process))

    result = await runtime.processar_arquivo_csv("sku\tnome\nA1\tIgnorar\nB2\tProduto".encode("utf-8"))

    assert len(calls) == 2
    assert result == [{"nome_base": "Produto", "sku_original": "B2"}]


def test_pdf_ingestion_runtime_covers_remaining_low_confidence_small_dataframe_paths():
    runtime = file_processing.PdfIngestionRuntime()

    assert runtime._is_low_confidence_dataframe(
        file_processing.pd.DataFrame(
            [
                {"col_0": "ab cd ef gh ij"},
                {"col_0": "ab"},
            ]
        )
    ) is True
    assert runtime._is_low_confidence_dataframe(
        pd.DataFrame(
            [
                {"col_0": "aa bb cc dd"},
            ]
        )
    ) is True


def test_pdf_ingestion_runtime_low_confidence_false_paths_and_line_mapping_edges():
    runtime = file_processing.PdfIngestionRuntime()
    workflow = file_processing.LineMappingWorkflow()

    assert runtime._is_low_confidence_dataframe(
        pd.DataFrame(
            [
                {"col_0": "ab cd ef gh ij", "col_1": "12 34"},
            ]
        )
    ) is False
    assert runtime._is_low_confidence_dataframe(
        pd.DataFrame(
            [
                {"col_0": "a 1 b 2 c 3 d 4 e 5"},
            ]
        )
    ) is False

    auto_only_name = workflow.processar_linha_padronizada(
        {"combo": "Produto livre", "sku": "ZX9"},
        {"combo": "auto:sku_nome", "sku": "sku_original"},
    )
    assert auto_only_name["sku_original"] == "ZX9"
    assert auto_only_name["nome_base"] == "Produto livre"

    ignored_empty_attr = workflow.processar_linha_padronizada(
        {"nome": "Produto Util", "extra_attr": "Aco"},
        {"extra_attr": "attr:"},
    )
    assert ignored_empty_attr["nome_base"] == "Produto Util"
    assert "dynamic_attributes" not in ignored_empty_attr

    split_nome_preserves_existing_identity = workflow.processar_linha_padronizada(
        {"nome": "Nome Manual", "sku_col": "ZX9", "nome_col": "AB12 Produto Base"},
        {"sku_col": "sku_original", "nome_col": "nome_base"},
    )
    assert split_nome_preserves_existing_identity["sku_original"] == "ZX9"
    assert split_nome_preserves_existing_identity["nome_base"] == "Nome Manual"

    split_sku_promotes_name = workflow.processar_linha_padronizada(
        {"sku_col": "AB12 Produto SKU"},
        {"sku_col": "sku_original"},
    )
    assert split_sku_promotes_name["sku_original"] == "AB12"
    assert split_sku_promotes_name["nome_base"] == "Produto SKU"

    duplicate_description = workflow.processar_linha_padronizada(
        {"descricao": "Base", "extra": "Base", "sku": "ZX9"},
        {"extra": "descricao_original"},
    )
    assert duplicate_description["descricao_original"] == "Base"

    weak_name_with_sku = workflow.processar_linha_padronizada({"nome": "---", "sku": "ZX9"})
    assert weak_name_with_sku["sku_original"] == "ZX9"
    assert "motivo_descarte" not in weak_name_with_sku


@pytest.mark.asyncio
async def test_pdf_preview_runtime_handles_partial_page_results(monkeypatch):
    runtime = file_processing.PdfPreviewRuntime(max_preview_workers=0)
    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: "pdftoppm")
    monkeypatch.setattr(
        file_processing,
        "pdf_open",
        lambda stream: _PdfContext([object(), object()]),
    )

    def fake_build_page_processor(*, conteudo_arquivo, dpi, poppler_path):
        _ = conteudo_arquivo, dpi, poppler_path

        def _processor(page_number):
            if page_number == 1:
                return {"page": 1, "has_table": False, "snippet": "linha 1"}
            return {"page": 2, "has_table": True, "preview_image": {"page": 2, "image": "img-2"}}

        return _processor

    monkeypatch.setattr(runtime, "_build_page_processor", fake_build_page_processor)

    result = await runtime.preview_arquivo_pdf(b"%PDF-1.4", ext=".pdf", start_page=1, page_count=2, dpi=72)

    assert result["table_pages"] == [2]
    assert result["sample_rows"] == {1: "linha 1"}
    assert result["preview_images"] == [{"page": 2, "image": "img-2"}]


def test_pdf_region_utils_cover_single_char_filter_and_duplicate_header_positions():
    utils = file_processing._PdfRegionExtractionUtils

    detected = utils.detect_header_columns(
        [
            [{"text": "FAB", "x0": 40, "x1": 50}, {"text": "FAB", "x0": 10, "x1": 20}, {"text": "DESCR", "x0": 80, "x1": 90}, {"text": "MATERIAL", "x0": 120, "x1": 140}],
        ]
    )
    filtered = utils.filter_ocr_rows([{"a": "X", "b": ""}, {"a": "SKU123", "b": "Produto"}])

    assert detected["bounds"][0] == 10
    assert filtered == [{"a": "SKU123", "b": "Produto"}]

    detected_keep_first = utils.detect_header_columns(
        [
            [{"text": "FAB", "x0": 10, "x1": 20}, {"text": "FAB", "x0": 40, "x1": 50}, {"text": "DESCR", "x0": 80, "x1": 90}, {"text": "MATERIAL", "x0": 120, "x1": 140}],
        ]
    )
    assert detected_keep_first["bounds"][0] == 10


def test_ocr_runtime_state_covers_candidate_path_scan(monkeypatch):
    fake_pytesseract = SimpleNamespace(
        pytesseract=SimpleNamespace(tesseract_cmd=None),
        get_tesseract_version=lambda: "5.0",
    )
    monkeypatch.setitem(__import__("sys").modules, "pytesseract", fake_pytesseract)
    monkeypatch.setitem(__import__("sys").modules, "PIL.Image", object())
    monkeypatch.setattr(file_processing.shutil, "which", lambda exe: None)
    monkeypatch.setattr(
        file_processing.os.path,
        "exists",
        lambda path: path.endswith("(x86)\\Tesseract-OCR\\tesseract.exe"),
    )

    state = file_processing.OcrRuntimeState()

    assert state.available is True
    assert state.exec_available is True
    assert fake_pytesseract.pytesseract.tesseract_cmd.endswith("tesseract.exe")


@pytest.mark.asyncio
async def test_process_pdf_job_impl_covers_none_products_and_preload_failure(monkeypatch):
    repo_updates = []

    class _CatalogFile:
        status = "PENDING"
        total_pages = 0
        pages_processed = 0
        result_summary = None

    class _Repo:
        def __init__(self, catalog_file=None, fail=False):
            self.catalog_file = catalog_file
            self.fail = fail

        def get_catalog_file(self, file_id):
            _ = file_id
            if self.fail:
                raise RuntimeError("db down")
            return self.catalog_file

        def update_catalog_file(self, catalog_file):
            repo_updates.append((catalog_file.status, catalog_file.pages_processed, catalog_file.result_summary))

    await file_processing._FileProcessingImplementation._process_pdf_job_impl(
        job_id=1,
        pdf_path="C:/tmp/catalogo.pdf",
        catalog_file_repository=_Repo(fail=True),
    )
    assert repo_updates == []

    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _PdfContext([object()]),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_single_page_impl",
        staticmethod(lambda file_path, page: {"rows": [{"x": 1}], "headers": ["x"]}),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        staticmethod(lambda row, mapping: None),
    )

    repo = _Repo(catalog_file=_CatalogFile())
    await file_processing._FileProcessingImplementation._process_pdf_job_impl(
        job_id=2,
        pdf_path="C:/tmp/catalogo.pdf",
        catalog_file_repository=repo,
    )

    assert repo_updates[-1][0] == "PENDING_REVIEW"
    assert repo_updates[-1][2] == {"products": []}
