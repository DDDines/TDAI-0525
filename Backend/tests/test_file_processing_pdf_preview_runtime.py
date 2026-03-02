"""Module test file processing pdf preview runtime.

Contains backend logic related to test file processing pdf preview runtime and documents its role in the OOP architecture.
"""

import pytest

from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_pdf_preview_runtime_retorna_erro_sem_poppler(monkeypatch):
        """Run test pdf preview runtime retorna erro sem poppler in this workflow."""
        runtime = file_processing.PdfPreviewRuntime()
        original_getenv = file_processing.os.getenv
    
        monkeypatch.setattr(
            file_processing.os,
            "getenv",
            lambda key, default=None: None if key == "POPPLER_PATH" else original_getenv(key, default),
        )
        monkeypatch.setattr(file_processing.settings, "POPPLER_PATH", None, raising=False)
        monkeypatch.setattr(file_processing.shutil, "which", lambda *_args, **_kwargs: None)
    
        result = await runtime.preview_arquivo_pdf(
            conteudo_arquivo=b"pdf",
            ext=".pdf",
            start_page=2,
            page_count=4,
            dpi=96,
        )
    
        assert "error" in result
        assert "Poppler" in result["error"]

    @pytest.mark.asyncio
    async def test_preview_pdf_impl_usa_runtime(monkeypatch):
        """Run test preview pdf impl usa runtime in this workflow."""
        called = {}
    
        async def _fake_preview_arquivo_pdf(self, **kwargs):
            """Run fake preview arquivo pdf in this workflow."""
            _ = self
            called.update(kwargs)
            return {"num_pages": 1, "preview_images": ["x"]}
    
        monkeypatch.setattr(
            file_processing.PdfPreviewRuntime,
            "preview_arquivo_pdf",
            _fake_preview_arquivo_pdf,
        )
    
        result = await file_processing._FileProcessingImplementation._preview_arquivo_pdf_impl(
            conteudo_arquivo=b"pdf",
            ext=".pdf",
            start_page=1,
            page_count=1,
            dpi=72,
        )
    
        assert result["num_pages"] == 1
        assert result["preview_images"] == ["x"]
        assert called["conteudo_arquivo"] == b"pdf"
        assert called["ext"] == ".pdf"
        assert called["start_page"] == 1
        assert called["page_count"] == 1
        assert called["dpi"] == 72

test_pdf_preview_runtime_retorna_erro_sem_poppler = _TopLevelFunctionSurface.test_pdf_preview_runtime_retorna_erro_sem_poppler
test_preview_pdf_impl_usa_runtime = _TopLevelFunctionSurface.test_preview_pdf_impl_usa_runtime




