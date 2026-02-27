import pytest

import Backend.services.file_processing_service as file_processing


@pytest.mark.asyncio
async def test_pdf_preview_runtime_delega_legacy(monkeypatch):
    runtime = file_processing._PdfPreviewRuntime()
    called = {}

    async def fake_preview_legacy(**kwargs):
        called.update(kwargs)
        return {"num_pages": 10, "preview_images": []}

    monkeypatch.setattr(
        file_processing,
        "_preview_arquivo_pdf_legacy_impl",
        fake_preview_legacy,
    )

    result = await runtime.preview_arquivo_pdf(
        conteudo_arquivo=b"pdf",
        ext=".pdf",
        start_page=2,
        page_count=4,
        dpi=96,
    )

    assert result["num_pages"] == 10
    assert called["conteudo_arquivo"] == b"pdf"
    assert called["ext"] == ".pdf"
    assert called["start_page"] == 2
    assert called["page_count"] == 4
    assert called["dpi"] == 96


@pytest.mark.asyncio
async def test_preview_pdf_impl_usa_runtime(monkeypatch):
    called = {}

    class FakePdfPreviewRuntime:
        async def preview_arquivo_pdf(self, **kwargs):
            called.update(kwargs)
            return {"num_pages": 1, "preview_images": ["x"]}

    monkeypatch.setattr(
        file_processing,
        "_pdf_preview_runtime",
        FakePdfPreviewRuntime(),
    )

    result = await file_processing._preview_arquivo_pdf_impl(
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
