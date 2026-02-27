import pytest

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_preview_dispatch_runtime_delega_legacy(monkeypatch):
    runtime = file_processing._PreviewDispatchRuntime()
    called = {}

    async def fake_legacy(**kwargs):
        called.update(kwargs)
        return {"headers": ["h1"], "sample_rows": []}

    monkeypatch.setattr(
        file_processing,
        "_gerar_preview_legacy_impl",
        fake_legacy,
    )

    result = await runtime.gerar_preview(
        conteudo_arquivo=b"raw",
        ext=".csv",
        max_rows=9,
    )

    assert result["headers"] == ["h1"]
    assert called["conteudo_arquivo"] == b"raw"
    assert called["ext"] == ".csv"
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
