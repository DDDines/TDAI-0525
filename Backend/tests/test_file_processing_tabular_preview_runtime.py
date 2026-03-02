"""Module test file processing tabular preview runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import pytest
import pandas as pd

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_tabular_preview_runtime_preview_excel(monkeypatch):
        """Execute test_tabular_preview_runtime_preview_excel.

        This callable is documented to make behavior explicit for readers.
        """
        runtime = file_processing.TabularPreviewRuntime()
    
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
        """Execute test_preview_csv_impl_usa_runtime.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        async def _fake_preview_arquivo_csv(self, **kwargs):
            """Execute _fake_preview_arquivo_csv.

            This callable is documented to make behavior explicit for readers.
            """
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




