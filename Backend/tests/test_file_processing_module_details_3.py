from __future__ import annotations

import asyncio
import builtins
import io
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pandas as pd
import pytest

from Backend.testing.runtime_apis import file_processing


class _ImageStub:
    def __init__(self, payload: bytes = b"img"):
        self.payload = payload

    def save(self, destination, format=None, **kwargs):
        _ = format, kwargs
        if hasattr(destination, "write"):
            destination.write(self.payload)
            return
        Path(destination).write_bytes(self.payload)

    def convert(self, mode):
        _ = mode
        return self


class _FakePdfPage:
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


class _FakePdfContext:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_file_processing_top_helpers_cover_password_delete_norm_preview_and_lookup(monkeypatch, tmp_path):
    impl = file_processing._FileProcessingImplementation

    class _PasswordError(Exception):
        pass

    monkeypatch.setattr(file_processing, "PDFPasswordIncorrect", _PasswordError, raising=False)
    assert impl._is_pdf_password_error(None) is False
    assert impl._is_pdf_password_error(RuntimeError("senha protegida")) is True
    assert impl._is_pdf_password_error(_PasswordError("locked")) is True
    assert impl._norm_text(" Valor ") == "valor"

    monkeypatch.setattr(file_processing.settings, "UPLOAD_DIRECTORY", str(tmp_path), raising=False)
    catalogs_dir = tmp_path / "catalogs"
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    target = catalogs_dir / "arquivo.pdf"
    target.write_bytes(b"pdf")

    original_unlink = Path.unlink

    def failing_unlink(self, *args, **kwargs):
        if self.name == "arquivo.pdf":
            raise OSError("locked")
        return original_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", failing_unlink)
    impl._delete_catalog_file_impl("arquivo.pdf")

    async def fake_generate_preview(self, **kwargs):
        return {"preview": kwargs["ext"]}

    monkeypatch.setattr(file_processing.PreviewDispatchRuntime, "gerar_preview", fake_generate_preview)
    preview = asyncio.run(impl._gerar_preview_impl(b"x", ".csv", max_rows=3))
    assert preview == {"preview": ".csv"}

    repo = SimpleNamespace(
        get_catalog_file=lambda file_id: (
            None if file_id == 2 else SimpleNamespace(stored_filename="saved.pdf")
        )
    )
    monkeypatch.setattr(file_processing, "CatalogImportFileRepository", lambda db: repo)
    assert impl._get_file_path_by_id_impl(db=object(), file_id="abc") is None
    assert impl._get_file_path_by_id_impl(db=object(), file_id="2") is None
    assert impl._get_file_path_by_id_impl(db=object(), file_id="1").endswith("saved.pdf")


@pytest.mark.asyncio
async def test_tabular_preview_dispatch_and_pdf_image_runtime_cover_fallbacks(monkeypatch):
    preview_runtime = file_processing.TabularPreviewEngineRuntime()
    assert preview_runtime._decode_csv_bytes(b"\xffproduto") == "ÿproduto"

    monkeypatch.setattr(file_processing.csv.Sniffer, "sniff", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("bad sniff")))
    assert preview_runtime._detect_csv_delimiter("a;b") == ";"
    assert preview_runtime._detect_csv_delimiter("a\tb") == "\t"
    assert preview_runtime._detect_csv_delimiter("ab") == ","

    monkeypatch.setattr(
        file_processing.TabularPreviewEngineRuntime,
        "_build_excel_preview_in_subprocess",
        lambda self, **kwargs: {
            "ok": False,
            "error_code": "FILE_PARSE_UNSAFE",
            "error": "excel fail",
        },
    )
    assert await preview_runtime.preview_arquivo_excel(b"PK\x03\x04xlsx") == {
        "error": "excel fail",
        "error_code": "FILE_PARSE_UNSAFE",
    }

    monkeypatch.setattr(
        file_processing.TabularPreviewEngineRuntime,
        "_build_csv_preview_in_subprocess",
        lambda self, **kwargs: {
            "ok": False,
            "error_code": "FILE_PARSE_UNSAFE",
            "error": "csv fail",
        },
    )
    assert await preview_runtime.preview_arquivo_csv(b"x") == {
        "error": "csv fail",
        "error_code": "FILE_PARSE_UNSAFE",
    }

    with pytest.raises(NotImplementedError):
        await file_processing._PreviewExtractor().extract(
            conteudo_arquivo=b"x",
            ext=".csv",
            max_rows=1,
        )

    with pytest.raises(ValueError, match="nao suportado"):
        file_processing._PreviewExtractorFactory(
            excel_extractor=SimpleNamespace(),
            csv_extractor=SimpleNamespace(),
            pdf_extractor=SimpleNamespace(),
        ).get_extractor(".txt")

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: None)
    pdf_preview = file_processing.PdfPreviewRuntime(max_preview_workers=0)
    assert await pdf_preview.preview_arquivo_pdf(b"pdf", ext=".pdf") == {
        "error": "Poppler (pdftoppm) executable not found. Install poppler-utils on Linux or set POPPLER_PATH to its directory."
    }

    image_runtime = file_processing.PdfImageConversionRuntime()
    with pytest.raises(RuntimeError, match="Poppler"):
        image_runtime._ensure_poppler_available(None)

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: "pdftoppm")
    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [_ImageStub(b"img-a"), _ImageStub(b"img-b")],
    )
    converted = image_runtime._convert_sync(
        conteudo_arquivo=b"%PDF-1.4",
        max_pages=2,
        start_page=1,
        dpi=144,
    )
    assert len(converted) == 2
    assert await image_runtime.pdf_bytes_to_images(b"%PDF-1.4", max_pages=1, start_page=1, dpi=144)


def test_pdf_utils_and_asset_runtime_cover_remaining_small_branches(monkeypatch, tmp_path):
    utils = file_processing._PdfRegionExtractionUtils
    assert utils.make_unique(["sku", "sku", None]) == ["sku", "sku_1", "col"]
    assert utils.clean_df(pd.DataFrame()) .empty is True
    assert utils.median_int([2, 4], 1) == 3
    assert utils.cluster_positions([1, 2, 20, 22], tolerance=3) == [1, 20]
    assert utils.header_field_for_text("material") == "material"
    assert utils.header_field_for_text("nada") is None
    assert utils.is_header_like_row("fab original descr") is True
    assert utils.filter_ocr_rows([{"col": "x"}]) == []
    assert utils.tables_to_df([[], [["sku"], ["A1"]]]).iloc[0].to_dict() == {"sku": "A1"}
    assert utils.group_words_by_line_ids([{"line": 0, "x": 0, "y": 0}, {"line": 1, "block": 1, "par": 1, "x": 1, "y": 2}]) == [[{"line": 1, "block": 1, "par": 1, "x": 1, "y": 2}]]
    assert utils.group_words_by_y([]) == []
    assert utils.merge_words_in_line(
        [
            {"x": 0, "w": 5, "text": "A"},
            {"x": 6, "w": 5, "text": ""},
            {"x": 40, "w": 5, "text": "B"},
        ]
    ) == [{"x0": 0, "x1": 5, "text": "A"}, {"x0": 40, "x1": 45, "text": "B"}]

    lines = [
        [{"text": "FAB ORIGINAL DESCR", "x0": 100, "x1": 200}],
        [{"text": "FAB ORIGINAL DESCR APLIC MATERIAL", "x0": 10, "x1": 210}],
    ]
    detected = utils.detect_header_columns(lines)
    assert detected["line_idx"] == 1
    assert detected["score"] >= 3

    runtime = file_processing.PdfAssetUtilityRuntime()

    original_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "fitz":
            raise ImportError("missing fitz")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="missing fitz"):
        runtime.generate_pdf_page_images("x.pdf", "10")
    monkeypatch.setattr(builtins, "__import__", original_import)

    monkeypatch.chdir(tmp_path)

    class _FakePixmap:
        def __init__(self, page_index):
            self.page_index = page_index

        def save(self, path):
            Path(path).write_bytes(f"page-{self.page_index}".encode())

    class _FakeDoc:
        def __len__(self):
            return 2

        def load_page(self, index):
            return SimpleNamespace(get_pixmap=lambda dpi=150: _FakePixmap(index + 1))

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_fitz = ModuleType("fitz")
    fake_fitz.open = lambda file_path: _FakeDoc()
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)
    assert runtime.generate_pdf_page_images("x.pdf", "11") == [
        "/static/previews/11/page-1.png",
        "/static/previews/11/page-2.png",
    ]


def test_extract_data_from_pdf_region_impl_covers_more_ocr_edges(monkeypatch):
    class _ExplodingPage(_FakePdfPage):
        def extract_tables(self, *args, **kwargs):
            raise RuntimeError("sem tabela")

    headers = " ".join(f"h{i}" for i in range(30))
    rows = "\n".join(" ".join(["x"] * 30) for _ in range(1201))
    page = _ExplodingPage(text=f"{headers}\n{rows}")
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([page]),
    )

    empty_df = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=SimpleNamespace(
            available=True,
            exec_available=True,
            exec_failed_once=False,
            image_cls=None,
            pytesseract=None,
        ),
    )
    assert empty_df.empty is True

    ocr_page = _FakePdfPage(text="", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([ocr_page]),
    )
    helper = file_processing._PdfRegionExtractionUtils
    monkeypatch.setattr(helper, "group_words_by_line_ids", lambda words: [])
    monkeypatch.setattr(helper, "group_words_by_y", lambda words: [[{"x": 0, "w": 5, "x0": 0, "text": "A"}]])
    monkeypatch.setattr(helper, "merge_words_in_line", lambda line_words: [])

    import PIL.ImageEnhance
    import PIL.ImageOps

    monkeypatch.setattr(PIL.ImageOps, "autocontrast", lambda image: image)
    monkeypatch.setattr(
        PIL.ImageEnhance,
        "Contrast",
        lambda image: SimpleNamespace(enhance=lambda factor: image),
    )

    empty_ocr_df = file_processing._FileProcessingImplementation._extract_data_from_pdf_region_impl(
        file_path="C:/tmp/catalogo.pdf",
        page_number=1,
        region=None,
        ocr_runtime_state=SimpleNamespace(
            available=True,
            exec_available=True,
            exec_failed_once=False,
            image_cls=SimpleNamespace(open=lambda stream: SimpleNamespace(convert=lambda mode: SimpleNamespace())),
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
        ),
    )
    assert empty_ocr_df.empty is True


@pytest.mark.asyncio
async def test_pdf_ingestion_runtime_covers_text_fallback_llm_and_non_llm_branches(monkeypatch):
    page = _FakePdfPage(text="texto bruto de catalogo", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([page]),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_extract_data_from_pdf_region_impl",
        lambda **kwargs: pd.DataFrame(),
    )
    monkeypatch.setattr(
        file_processing._FileProcessingImplementation,
        "_processar_linha_padronizada",
        lambda row, mapping=None: row,
    )

    async def llm_sem_identidade(text):
        return {"descricao_original": "sem identidade"}

    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(
            extrair_dados_produto_com_llm=llm_sem_identidade
        )
    )
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=True,
        extraction_mode="ia",
    )
    assert any("payload sem identidade" in item.lower() for item in result[0]["log_pdf"])

    async def llm_formato_invalido(text):
        return "payload invalido"

    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(
            extrair_dados_produto_com_llm=llm_formato_invalido
        )
    )
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=True,
        extraction_mode="ia",
    )
    assert any("formato inesperado" in item.lower() for item in result[0]["log_pdf"])

    async def llm_com_erro(text):
        raise RuntimeError("llm down")

    runtime = file_processing.PdfIngestionRuntime(
        web_data_extractor_service=SimpleNamespace(
            extrair_dados_produto_com_llm=llm_com_erro
        )
    )
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=True,
        extraction_mode="ia",
    )
    assert any("erro ao processar com llm" in item.lower() for item in result[0]["log_pdf"])

    short_page = _FakePdfPage(text="texto curto demais", tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([short_page]),
    )
    runtime = file_processing.PdfIngestionRuntime()
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        extraction_mode="ocr",
    )
    assert result[0]["nome_base"] == "Conteudo da Pagina 1"

    long_page = _FakePdfPage(text=" ".join(["texto"] * 30), tables=[])
    monkeypatch.setattr(
        file_processing.pdfplumber,
        "open",
        lambda *args, **kwargs: _FakePdfContext([long_page]),
    )
    runtime = file_processing.PdfIngestionRuntime()
    monkeypatch.setattr(runtime, "_extract_structured_rows_from_text", lambda page_text: [])
    result = await runtime.processar_arquivo_pdf(
        conteudo_arquivo=b"%PDF-1.4",
        usar_llm=False,
        extraction_mode="ocr",
    )
    assert any("texto sem padrao de linha de produto" in item.lower() for item in result[0]["log_pdf"])
