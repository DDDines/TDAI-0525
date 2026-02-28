import pytest
import pandas as pd

from Backend.testing.runtime_apis import file_processing


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

    async def _fake_preview_arquivo_csv(self, **kwargs):
        _ = self
        called.update(kwargs)
        return {"headers": ["c1"], "sample_rows": [{"c1": "v"}]}

    monkeypatch.setattr(
        file_processing._TabularPreviewEngineRuntime,
        "preview_arquivo_csv",
        _fake_preview_arquivo_csv,
    )

    result = await file_processing._preview_arquivo_csv_impl(b"csv-bytes", max_rows=3)

    assert result["headers"] == ["c1"]
    assert called["conteudo_arquivo"] == b"csv-bytes"
    assert called["max_rows"] == 3

