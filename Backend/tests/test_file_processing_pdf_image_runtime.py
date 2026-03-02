"""Module test file processing pdf image runtime.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import base64

import pytest

from Backend.testing.runtime_apis import file_processing


class _FakeImage:
    """Class _FakeImage.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, payload: bytes) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.payload = payload

    def save(self, buffer, format=None):  # noqa: A002 - assinatura compativel com PIL
        """Execute save.

        This callable is documented to make behavior explicit for readers.
        """
        buffer.write(self.payload)


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    @pytest.mark.asyncio
    async def test_pdf_image_runtime_converte_para_base64(monkeypatch):
        """Execute test_pdf_image_runtime_converte_para_base64.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_pdf_bytes_to_images_impl_usa_runtime.

        This callable is documented to make behavior explicit for readers.
        """
        called = {}
    
        async def _fake_pdf_bytes_to_images(self, **kwargs):
            """Execute _fake_pdf_bytes_to_images.

            This callable is documented to make behavior explicit for readers.
            """
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




