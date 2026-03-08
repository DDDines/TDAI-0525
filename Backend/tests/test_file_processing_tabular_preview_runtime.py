"""Module test file processing tabular preview runtime.

Contains backend logic related to test file processing tabular preview runtime and documents its role in the OOP architecture.
"""

import pytest
import pandas as pd

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_tabular_preview_runtime_preview_excel(monkeypatch):
        """Run test tabular preview runtime preview excel in this workflow."""
        runtime = file_processing.TabularPreviewRuntime()

        monkeypatch.setattr(
            file_processing.TabularPreviewEngineRuntime,
            "_build_excel_preview_in_subprocess",
            lambda self, **kwargs: {"ok": True, "headers": ["a"], "sample_rows": [{"a": "1"}]},
        )

        result = await runtime.preview_arquivo_excel(b"PK\x03\x04xlsx", max_rows=1)
    
        assert result["headers"] == ["a"]
        assert result["sample_rows"] == [{"a": "1"}]

    @pytest.mark.asyncio
    async def test_preview_csv_impl_usa_runtime(monkeypatch):
        """Run test preview csv impl usa runtime in this workflow."""
        called = {}
    
        async def _fake_preview_arquivo_csv(self, **kwargs):
            """Run fake preview arquivo csv in this workflow."""
            _ = self
            called.update(kwargs)
            return {"headers": ["c1"], "sample_rows": [{"c1": "v"}]}
    
        monkeypatch.setattr(
            file_processing.TabularPreviewEngineRuntime,
            "preview_arquivo_csv",
            _fake_preview_arquivo_csv,
        )
    
        result = await file_processing._FileProcessingImplementation._preview_arquivo_csv_impl(
            b"csv-bytes",
            max_rows=3,
        )
    
        assert result["headers"] == ["c1"]
        assert called["conteudo_arquivo"] == b"csv-bytes"
        assert called["max_rows"] == 3

test_tabular_preview_runtime_preview_excel = _TopLevelFunctionSurface.test_tabular_preview_runtime_preview_excel
test_preview_csv_impl_usa_runtime = _TopLevelFunctionSurface.test_preview_csv_impl_usa_runtime




