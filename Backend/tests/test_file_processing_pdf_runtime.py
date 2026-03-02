"""Module test file processing pdf runtime.

Contains backend logic related to test file processing pdf runtime and documents its role in the OOP architecture.
"""

import pytest

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
        )
    
        assert result == [{"source": "runtime"}]
        assert called["conteudo_arquivo"] == b"abc"
        assert called["mapeamento_colunas_usuario"] == {"col_1": "sku_original"}
        assert called["usar_llm"] is True
        assert called["product_type_id"] == 11
        assert called["pages"] == [1]
        assert called["region"] is None

test_pdf_runtime_retorna_erro_quando_falha_abrir_pdf = _TopLevelFunctionSurface.test_pdf_runtime_retorna_erro_quando_falha_abrir_pdf
test_pdf_runtime_detecta_erro_de_senha = _TopLevelFunctionSurface.test_pdf_runtime_detecta_erro_de_senha
test_processar_arquivo_pdf_impl_usa_runtime = _TopLevelFunctionSurface.test_processar_arquivo_pdf_impl_usa_runtime






