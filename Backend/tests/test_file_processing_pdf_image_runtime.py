"""Module test file processing pdf image runtime.

Contains backend logic related to test file processing pdf image runtime and documents its role in the OOP architecture.
"""

import base64

import pytest

from Backend.testing.runtime_apis import file_processing


class _FakeImage:
    """Represent fake image and centralize responsibilities for this module."""
    def __init__(self, payload: bytes) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.payload = payload

    def save(self, buffer, format=None):  # noqa: A002 - assinatura compativel com PIL
        """Run save in this workflow."""
        buffer.write(self.payload)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @pytest.mark.asyncio
    async def test_pdf_image_runtime_converte_para_base64(monkeypatch):
        """Run test pdf image runtime converte para base64 in this workflow."""
        runtime = file_processing.PdfImageConversionRuntime()
    
        monkeypatch.setattr(file_processing.shutil, "which", lambda *_args, **_kwargs: "pdftoppm")
        monkeypatch.setattr(
            file_processing,
            "convert_from_bytes",
            lambda *_args, **_kwargs: [_FakeImage(b"img-1"), _FakeImage(b"img-2")],
        )
    
        result = await runtime.pdf_bytes_to_images(
            conteudo_arquivo=b"pdf",
            max_pages=2,
            start_page=1,
            dpi=72,
        )
    
        assert result == [
            base64.b64encode(b"img-1").decode(),
            base64.b64encode(b"img-2").decode(),
        ]

    @pytest.mark.asyncio
    async def test_pdf_bytes_to_images_impl_usa_runtime(monkeypatch):
        """Run test pdf bytes to images impl usa runtime in this workflow."""
        called = {}
    
        async def _fake_pdf_bytes_to_images(self, **kwargs):
            """Run fake pdf bytes to images in this workflow."""
            _ = self
            called.update(kwargs)
            return ["abc"]
    
        monkeypatch.setattr(
            file_processing.PdfImageConversionRuntime,
            "pdf_bytes_to_images",
            _fake_pdf_bytes_to_images,
        )
    
        result = await file_processing._FileProcessingImplementation._pdf_bytes_to_images_impl(
            conteudo_arquivo=b"pdf",
            max_pages=3,
            start_page=2,
            dpi=150,
        )
    
        assert result == ["abc"]
        assert called["conteudo_arquivo"] == b"pdf"
        assert called["max_pages"] == 3
        assert called["start_page"] == 2
        assert called["dpi"] == 150

test_pdf_image_runtime_converte_para_base64 = _TopLevelFunctionSurface.test_pdf_image_runtime_converte_para_base64
test_pdf_bytes_to_images_impl_usa_runtime = _TopLevelFunctionSurface.test_pdf_bytes_to_images_impl_usa_runtime




