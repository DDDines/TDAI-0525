import pytest

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_tabular_preview_runtime_delega_excel_legacy(monkeypatch):
    runtime = file_processing._TabularPreviewRuntime()
    called = {}

    async def fake_excel_legacy(**kwargs):
        called.update(kwargs)
        return {"headers": ["a"], "sample_rows": [{"a": "1"}]}

    monkeypatch.setattr(
        file_processing,
        "_preview_arquivo_excel_legacy_impl",
        fake_excel_legacy,
    )

    result = await runtime.preview_arquivo_excel(b"xlsx", max_rows=7)

    assert result["headers"] == ["a"]
    assert called["conteudo_arquivo"] == b"xlsx"
    assert called["max_rows"] == 7


@pytest.mark.asyncio
async def test_preview_csv_impl_usa_runtime(monkeypatch):
    called = {}

    class FakePreviewRuntime:
        async def preview_arquivo_excel(self, **kwargs):
            return {"headers": [], "sample_rows": []}

        async def preview_arquivo_csv(self, **kwargs):
            called.update(kwargs)
            return {"headers": ["c1"], "sample_rows": [{"c1": "v"}]}

    monkeypatch.setattr(
        file_processing,
        "_tabular_preview_runtime",
        FakePreviewRuntime(),
    )

    result = await file_processing._preview_arquivo_csv_impl(b"csv-bytes", max_rows=3)

    assert result["headers"] == ["c1"]
    assert called["conteudo_arquivo"] == b"csv-bytes"
    assert called["max_rows"] == 3
