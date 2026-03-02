"""Module test file processing pdf processing workflow.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_pdf_processing_workflow_usa_runtime_de_ingestao():
        """Execute test_pdf_processing_workflow_usa_runtime_de_ingestao.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeIngestionRuntime:
            """Class FakeIngestionRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def processar_arquivo_pdf(self, **kwargs):
                """Execute processar_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                called.update(kwargs)
                return [{"ok": True}]
    
        class FakePreviewRuntime:
            """Class FakePreviewRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def preview_arquivo_pdf(self, **kwargs):
                """Execute preview_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                return {"num_pages": 1}
    
        class FakeDispatchRuntime:
            """Class FakeDispatchRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def gerar_preview(self, **kwargs):
                """Execute gerar_preview.

                This callable is documented to make behavior explicit for readers.
                """
                return {"headers": []}
    
        workflow = file_processing.PdfProcessingWorkflow(
            pdf_ingestion_runtime=FakeIngestionRuntime(),
            pdf_preview_runtime=FakePreviewRuntime(),
            preview_dispatch_runtime=FakeDispatchRuntime(),
        )
    
        result = await workflow.processar_arquivo_pdf(
            conteudo_arquivo=b"pdf",
            mapeamento_colunas_usuario={"col_0": "nome_base"},
            usar_llm=False,
            product_type_id=4,
            pages=[12],
            region=[1.0, 2.0, 3.0, 4.0],
        )
    
        assert result == [{"ok": True}]
        assert called["conteudo_arquivo"] == b"pdf"
        assert called["mapeamento_colunas_usuario"] == {"col_0": "nome_base"}
        assert called["usar_llm"] is False
        assert called["product_type_id"] == 4
        assert called["pages"] == [12]
        assert called["region"] == [1.0, 2.0, 3.0, 4.0]

    @pytest.mark.asyncio
    async def test_pdf_processing_workflow_usa_runtime_de_preview():
        """Execute test_pdf_processing_workflow_usa_runtime_de_preview.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeIngestionRuntime:
            """Class FakeIngestionRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def processar_arquivo_pdf(self, **kwargs):
                """Execute processar_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                return []
    
        class FakePreviewRuntime:
            """Class FakePreviewRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def preview_arquivo_pdf(self, **kwargs):
                """Execute preview_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                called.update(kwargs)
                return {"num_pages": 2, "preview_images": []}
    
        class FakeDispatchRuntime:
            """Class FakeDispatchRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def gerar_preview(self, **kwargs):
                """Execute gerar_preview.

                This callable is documented to make behavior explicit for readers.
                """
                return {}
    
        workflow = file_processing.PdfProcessingWorkflow(
            pdf_ingestion_runtime=FakeIngestionRuntime(),
            pdf_preview_runtime=FakePreviewRuntime(),
            preview_dispatch_runtime=FakeDispatchRuntime(),
        )
    
        result = await workflow.preview_arquivo_pdf(
            conteudo_arquivo=b"pdf",
            ext=".pdf",
            start_page=3,
            page_count=4,
            dpi=144,
        )
    
        assert result["num_pages"] == 2
        assert called["conteudo_arquivo"] == b"pdf"
        assert called["ext"] == ".pdf"
        assert called["start_page"] == 3
        assert called["page_count"] == 4
        assert called["dpi"] == 144

    @pytest.mark.asyncio
    async def test_pdf_processing_workflow_usa_runtime_de_dispatch():
        """Execute test_pdf_processing_workflow_usa_runtime_de_dispatch.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        class FakeIngestionRuntime:
            """Class FakeIngestionRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def processar_arquivo_pdf(self, **kwargs):
                """Execute processar_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                return []
    
        class FakePreviewRuntime:
            """Class FakePreviewRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def preview_arquivo_pdf(self, **kwargs):
                """Execute preview_arquivo_pdf.

                This callable is documented to make behavior explicit for readers.
                """
                return {}
    
        class FakeDispatchRuntime:
            """Class FakeDispatchRuntime.

            Encapsulates one responsibility in the backend architecture.
            """
            async def gerar_preview(self, **kwargs):
                """Execute gerar_preview.

                This callable is documented to make behavior explicit for readers.
                """
                called.update(kwargs)
                return {"headers": ["h1"], "sample_rows": []}
    
        workflow = file_processing.PdfProcessingWorkflow(
            pdf_ingestion_runtime=FakeIngestionRuntime(),
            pdf_preview_runtime=FakePreviewRuntime(),
            preview_dispatch_runtime=FakeDispatchRuntime(),
        )
    
        result = await workflow.gerar_preview(
            conteudo_arquivo=b"raw",
            ext=".csv",
            max_rows=10,
        )
    
        assert result["headers"] == ["h1"]
        assert called["conteudo_arquivo"] == b"raw"
        assert called["ext"] == ".csv"
        assert called["max_rows"] == 10

test_pdf_processing_workflow_usa_runtime_de_ingestao = _TopLevelFunctionSurface.test_pdf_processing_workflow_usa_runtime_de_ingestao
test_pdf_processing_workflow_usa_runtime_de_preview = _TopLevelFunctionSurface.test_pdf_processing_workflow_usa_runtime_de_preview
test_pdf_processing_workflow_usa_runtime_de_dispatch = _TopLevelFunctionSurface.test_pdf_processing_workflow_usa_runtime_de_dispatch






