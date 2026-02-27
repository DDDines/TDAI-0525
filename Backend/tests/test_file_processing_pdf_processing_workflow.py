import pytest

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_pdf_processing_workflow_usa_runtime_de_ingestao():
    called = {}

    class FakeIngestionRuntime:
        async def processar_arquivo_pdf(self, **kwargs):
            called.update(kwargs)
            return [{"ok": True}]

    class FakePreviewRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            return {"num_pages": 1}

    class FakeDispatchRuntime:
        async def gerar_preview(self, **kwargs):
            return {"headers": []}

    workflow = file_processing._PdfProcessingWorkflow(
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
    called = {}

    class FakeIngestionRuntime:
        async def processar_arquivo_pdf(self, **kwargs):
            return []

    class FakePreviewRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            called.update(kwargs)
            return {"num_pages": 2, "preview_images": []}

    class FakeDispatchRuntime:
        async def gerar_preview(self, **kwargs):
            return {}

    workflow = file_processing._PdfProcessingWorkflow(
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
    called = {}

    class FakeIngestionRuntime:
        async def processar_arquivo_pdf(self, **kwargs):
            return []

    class FakePreviewRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            return {}

    class FakeDispatchRuntime:
        async def gerar_preview(self, **kwargs):
            called.update(kwargs)
            return {"headers": ["h1"], "sample_rows": []}

    workflow = file_processing._PdfProcessingWorkflow(
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
