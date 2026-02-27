import pytest

from Backend.testing.runtime_apis import file_processing


@pytest.mark.asyncio
async def test_preview_dispatch_runtime_despacha_csv_para_runtime_tabular():
    called = {}

    class FakeTabularRuntime:
        async def preview_arquivo_excel(self, **kwargs):
            return {"headers": ["excel"], "sample_rows": []}

        async def preview_arquivo_csv(self, **kwargs):
            called.update(kwargs)
            return {"headers": ["h1"], "sample_rows": []}

    class FakePdfRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            return {"num_pages": 1, "preview_images": []}

    runtime = file_processing._PreviewDispatchRuntime(
        tabular_preview_runtime=FakeTabularRuntime(),
        pdf_preview_runtime=FakePdfRuntime(),
    )

    result = await runtime.gerar_preview(
        conteudo_arquivo=b"raw",
        ext=".csv",
        max_rows=9,
    )

    assert result["headers"] == ["h1"]
    assert called["conteudo_arquivo"] == b"raw"
    assert called["max_rows"] == 9


@pytest.mark.asyncio
async def test_gerar_preview_impl_usa_runtime(monkeypatch):
    called = {}

    class FakeDispatchRuntime:
        async def gerar_preview(self, **kwargs):
            called.update(kwargs)
            return {"num_pages": 3}

    monkeypatch.setattr(
        file_processing,
        "_preview_dispatch_runtime",
        FakeDispatchRuntime(),
    )

    result = await file_processing._gerar_preview_impl(
        conteudo_arquivo=b"x",
        ext=".pdf",
        max_rows=1,
    )

    assert result["num_pages"] == 3
    assert called["conteudo_arquivo"] == b"x"
    assert called["ext"] == ".pdf"
    assert called["max_rows"] == 1

