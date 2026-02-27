import base64

import pytest

import Backend.services.file_processing_service as file_processing


class _FakeImage:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def save(self, buffer, format=None):  # noqa: A002 - assinatura compativel com PIL
        buffer.write(self.payload)


@pytest.mark.asyncio
async def test_pdf_image_runtime_converte_para_base64(monkeypatch):
    runtime = file_processing._PdfImageConversionRuntime()

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
    called = {}

    class FakeRuntime:
        async def pdf_bytes_to_images(self, **kwargs):
            called.update(kwargs)
            return ["abc"]

    monkeypatch.setattr(file_processing, "_pdf_image_conversion_runtime", FakeRuntime())

    result = await file_processing._pdf_bytes_to_images_impl(
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
