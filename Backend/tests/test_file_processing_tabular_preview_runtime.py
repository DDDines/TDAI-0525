import pytest
import pandas as pd

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_tabular_preview_runtime_preview_excel(monkeypatch):
    runtime = file_processing._TabularPreviewRuntime()

    monkeypatch.setattr(
        file_processing.pd,
        "read_excel",
        lambda *_args, **_kwargs: pd.DataFrame([{"a": "1"}, {"a": "2"}]),
    )

    result = await runtime.preview_arquivo_excel(b"xlsx", max_rows=1)

    assert result["headers"] == ["a"]
    assert result["sample_rows"] == [{"a": "1"}]


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
