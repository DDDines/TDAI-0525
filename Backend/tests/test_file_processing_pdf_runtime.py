"""Module test file processing pdf runtime.

Contains backend logic related to test file processing pdf runtime and documents its role in the OOP architecture.
"""

import pytest
import pandas as pd

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_pdf_runtime_retorna_erro_quando_falha_abrir_pdf(monkeypatch):
        """Run test pdf runtime retorna erro quando falha abrir pdf in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
    
        monkeypatch.setattr(
            file_processing.pdfplumber,
            "open",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("falha-forcada")),
        )
    
        result = await runtime.processar_arquivo_pdf(
            conteudo_arquivo=b"pdf-bytes",
            usar_llm=False,
        )
    
        assert isinstance(result, list)
        assert "erro_processamento_pdf" in result[0]
        assert "Falha ao abrir PDF" in result[0]["erro_processamento_pdf"]
        assert "falha-forcada" in result[0]["erro_processamento_pdf"]

    @pytest.mark.asyncio
    async def test_pdf_runtime_detecta_erro_de_senha(monkeypatch):
        """Run test pdf runtime detecta erro de senha in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
    
        class FakePasswordError(Exception):
            """Represent fake password error and centralize responsibilities for this module."""
            pass
    
        monkeypatch.setattr(
            file_processing.pdfplumber,
            "open",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                FakePasswordError("PDF password required")
            ),
        )
    
        result = await runtime.processar_arquivo_pdf(
            conteudo_arquivo=b"pdf-bytes",
            usar_llm=False,
        )
    
        assert isinstance(result, list)
        assert "erro_processamento_pdf" in result[0]
        assert "PDF protegido por senha" in result[0]["erro_processamento_pdf"]

    @pytest.mark.asyncio
    async def test_processar_arquivo_pdf_impl_usa_runtime(monkeypatch):
        """Run test processar arquivo pdf impl usa runtime in this workflow."""
        called = {}
    
        async def _fake_processar_arquivo_pdf(self, **kwargs):
            """Run fake processar arquivo pdf in this workflow."""
            called.update(kwargs)
            return [{"source": "runtime"}]
    
        monkeypatch.setattr(
            file_processing.PdfIngestionRuntime,
            "processar_arquivo_pdf",
            _fake_processar_arquivo_pdf,
        )
    
        result = await file_processing._FileProcessingImplementation._processar_arquivo_pdf_impl(
            conteudo_arquivo=b"abc",
            mapeamento_colunas_usuario={"col_1": "sku_original"},
            usar_llm=True,
            product_type_id=11,
            pages=[1],
            region=None,
            extraction_mode="ia",
        )
    
        assert result == [{"source": "runtime"}]
        assert called["conteudo_arquivo"] == b"abc"
        assert called["mapeamento_colunas_usuario"] == {"col_1": "sku_original"}
        assert called["usar_llm"] is True
        assert called["product_type_id"] == 11
        assert called["pages"] == [1]
        assert called["region"] is None
        assert called["extraction_mode"] == "ia"

    @pytest.mark.asyncio
    async def test_pdf_runtime_ignora_payload_de_descarte(monkeypatch):
        """Run test pdf runtime ignora payload de descarte in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()

        class FakePage:
            """Represent fake page and centralize responsibilities for this module."""

            width = 100
            height = 100

            def extract_tables(self, *args, **kwargs):
                """Run extract tables in this workflow."""
                return [[["col_0"], ["valor_linha"]]]

            def extract_text(self, *args, **kwargs):
                """Run extract text in this workflow."""
                return ""

            def crop(self, _bbox):
                """Run crop in this workflow."""
                return self

        class FakePdf:
            """Represent fake pdf and centralize responsibilities for this module."""

            pages = [FakePage()]

            def __enter__(self):
                """Run enter in this workflow."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Run exit in this workflow."""
                return False

        monkeypatch.setattr(file_processing.pdfplumber, "open", lambda *_args, **_kwargs: FakePdf())
        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_processar_linha_padronizada",
            lambda *_args, **_kwargs: {"motivo_descarte": "sem_nome_sku", "linha_original": {}},
        )

        result = await runtime.processar_arquivo_pdf(conteudo_arquivo=b"fake", usar_llm=False)
        assert isinstance(result, list)
        assert "erro_processamento_pdf" in result[0]
        assert "Nenhum dado de produto" in result[0]["erro_processamento_pdf"]

    @pytest.mark.asyncio
    async def test_pdf_runtime_aplica_fallback_tabular_ocr_sem_bbox(monkeypatch):
        """Run test pdf runtime aplica fallback tabular ocr sem bbox in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
        calls = {"extract_region": 0}

        class FakePage:
            """Represent fake page and centralize responsibilities for this module."""

            width = 100
            height = 100

            def extract_tables(self, *args, **kwargs):
                """Run extract tables in this workflow."""
                return []

            def extract_text(self, *args, **kwargs):
                """Run extract text in this workflow."""
                return ""

            def crop(self, _bbox):
                """Run crop in this workflow."""
                return self

        class FakePdf:
            """Represent fake pdf and centralize responsibilities for this module."""

            pages = [FakePage()]

            def __enter__(self):
                """Run enter in this workflow."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Run exit in this workflow."""
                return False

        def _fake_extract_data_from_pdf_region_impl(*, file_path, page_number, region=None, ocr_runtime_state=None):
            """Run fake extract data from pdf region impl in this workflow."""
            _ = file_path, page_number, region, ocr_runtime_state
            calls["extract_region"] += 1
            return pd.DataFrame([{"col_0": "SKU123 Produto Teste"}])

        monkeypatch.setattr(file_processing.pdfplumber, "open", lambda *_args, **_kwargs: FakePdf())
        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_extract_data_from_pdf_region_impl",
            _fake_extract_data_from_pdf_region_impl,
        )
        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_processar_linha_padronizada",
            lambda *_args, **_kwargs: {"nome_base": "Produto Teste", "sku_original": "SKU123"},
        )

        result = await runtime.processar_arquivo_pdf(conteudo_arquivo=b"fake", usar_llm=False)
        assert calls["extract_region"] >= 1
        assert isinstance(result, list)
        assert result
        assert result[0]["nome_base"] == "Produto Teste"
        assert result[0]["sku_original"] == "SKU123"

    @pytest.mark.asyncio
    async def test_pdf_runtime_table_mode_nao_executa_fallback_ocr(monkeypatch):
        """Run test pdf runtime table mode nao executa fallback ocr in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
        calls = {"extract_region": 0}

        class FakePage:
            """Represent fake page and centralize responsibilities for this module."""

            width = 100
            height = 100

            def extract_tables(self, *args, **kwargs):
                """Run extract tables in this workflow."""
                return []

            def extract_text(self, *args, **kwargs):
                """Run extract text in this workflow."""
                return "texto"

            def crop(self, _bbox):
                """Run crop in this workflow."""
                return self

        class FakePdf:
            """Represent fake pdf and centralize responsibilities for this module."""

            pages = [FakePage()]

            def __enter__(self):
                """Run enter in this workflow."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Run exit in this workflow."""
                return False

        def _fake_extract_data_from_pdf_region_impl(*, file_path, page_number, region=None, ocr_runtime_state=None):
            """Run fake extract data from pdf region impl in this workflow."""
            _ = file_path, page_number, region, ocr_runtime_state
            calls["extract_region"] += 1
            return pd.DataFrame([{"col_0": "SKU123 Produto Teste"}])

        monkeypatch.setattr(file_processing.pdfplumber, "open", lambda *_args, **_kwargs: FakePdf())
        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_extract_data_from_pdf_region_impl",
            _fake_extract_data_from_pdf_region_impl,
        )

        result = await runtime.processar_arquivo_pdf(
            conteudo_arquivo=b"fake",
            usar_llm=False,
            extraction_mode="table",
        )

        assert calls["extract_region"] == 0
        assert isinstance(result, list)
        assert "erro_processamento_pdf" in result[0]

    @pytest.mark.asyncio
    async def test_pdf_runtime_descarta_fallback_ocr_com_poucos_caracteres(monkeypatch):
        """Run test pdf runtime descarta fallback ocr com poucos caracteres in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
        calls = {"extract_region": 0}

        class FakePage:
            """Represent fake page and centralize responsibilities for this module."""

            width = 100
            height = 100

            def extract_tables(self, *args, **kwargs):
                """Run extract tables in this workflow."""
                return []

            def extract_text(self, *args, **kwargs):
                """Run extract text in this workflow."""
                return ""

            def crop(self, _bbox):
                """Run crop in this workflow."""
                return self

        class FakePdf:
            """Represent fake pdf and centralize responsibilities for this module."""

            pages = [FakePage()]

            def __enter__(self):
                """Run enter in this workflow."""
                return self

            def __exit__(self, exc_type, exc, tb):
                """Run exit in this workflow."""
                return False

        def _fake_extract_data_from_pdf_region_impl(*, file_path, page_number, region=None, ocr_runtime_state=None):
            """Run fake extract data from pdf region impl in this workflow."""
            _ = file_path, page_number, region, ocr_runtime_state
            calls["extract_region"] += 1
            return pd.DataFrame([{"col_0": "a1"}, {"col_0": "b2"}])

        monkeypatch.setattr(file_processing.pdfplumber, "open", lambda *_args, **_kwargs: FakePdf())
        monkeypatch.setattr(
            file_processing._FileProcessingImplementation,
            "_extract_data_from_pdf_region_impl",
            _fake_extract_data_from_pdf_region_impl,
        )

        result = await runtime.processar_arquivo_pdf(
            conteudo_arquivo=b"fake",
            usar_llm=False,
            extraction_mode="ocr",
        )

        assert calls["extract_region"] >= 1
        assert isinstance(result, list)
        assert "erro_processamento_pdf" in result[0]

    def test_pdf_runtime_descarta_marcadores_de_indice():
        """Run test pdf runtime descarta marcadores de indice in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
        produtos = []

        runtime._append_produto(
            produtos_extraidos=produtos,
            produto_padronizado={"nome_base": "Código Páginas"},
            product_type_id=None,
        )
        runtime._append_produto(
            produtos_extraidos=produtos,
            produto_padronizado={"nome_base": "519"},
            product_type_id=None,
        )
        runtime._append_produto(
            produtos_extraidos=produtos,
            produto_padronizado={"nome_base": "B47"},
            product_type_id=None,
        )

        assert produtos == []

    def test_pdf_runtime_mantem_fallback_conteudo_curto():
        """Run test pdf runtime mantem fallback conteudo curto in this workflow."""
        runtime = file_processing.PdfIngestionRuntime()
        produtos = []

        runtime._append_produto(
            produtos_extraidos=produtos,
            produto_padronizado={
                "nome_base": "Conteudo da Pagina 1",
                "dados_brutos_adicionais": {"texto_completo_pagina_1": "texto curto"},
            },
            product_type_id=None,
        )

        assert len(produtos) == 1
        assert produtos[0]["nome_base"] == "Conteudo da Pagina 1"

test_pdf_runtime_retorna_erro_quando_falha_abrir_pdf = _TopLevelFunctionSurface.test_pdf_runtime_retorna_erro_quando_falha_abrir_pdf
test_pdf_runtime_detecta_erro_de_senha = _TopLevelFunctionSurface.test_pdf_runtime_detecta_erro_de_senha
test_processar_arquivo_pdf_impl_usa_runtime = _TopLevelFunctionSurface.test_processar_arquivo_pdf_impl_usa_runtime
test_pdf_runtime_ignora_payload_de_descarte = _TopLevelFunctionSurface.test_pdf_runtime_ignora_payload_de_descarte
test_pdf_runtime_aplica_fallback_tabular_ocr_sem_bbox = _TopLevelFunctionSurface.test_pdf_runtime_aplica_fallback_tabular_ocr_sem_bbox
test_pdf_runtime_table_mode_nao_executa_fallback_ocr = _TopLevelFunctionSurface.test_pdf_runtime_table_mode_nao_executa_fallback_ocr
test_pdf_runtime_descarta_fallback_ocr_com_poucos_caracteres = _TopLevelFunctionSurface.test_pdf_runtime_descarta_fallback_ocr_com_poucos_caracteres
test_pdf_runtime_descarta_marcadores_de_indice = _TopLevelFunctionSurface.test_pdf_runtime_descarta_marcadores_de_indice
test_pdf_runtime_mantem_fallback_conteudo_curto = _TopLevelFunctionSurface.test_pdf_runtime_mantem_fallback_conteudo_curto






