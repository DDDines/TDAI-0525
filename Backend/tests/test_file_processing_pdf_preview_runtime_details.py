"""Additional detailed coverage for PDF preview and asset utilities."""

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace

import pytest

from Backend.testing.runtime_apis import file_processing


class _FakePdfPage:
    def __init__(self, *, tables=None, text="", crop_result=None, image_bytes=b"png"):
        self._tables = tables if tables is not None else []
        self._text = text
        self._crop_result = crop_result
        self._image_bytes = image_bytes

    def extract_tables(self):
        return self._tables

    def extract_text(self):
        return self._text

    def crop(self, bbox):
        _ = bbox
        return self._crop_result or self

    def to_image(self, resolution):
        _ = resolution

        class _Original:
            def __init__(self, payload):
                self._payload = payload

            def save(self, buffer, format=None):  # noqa: A002
                _ = format
                buffer.write(self._payload)

        return SimpleNamespace(original=_Original(self._image_bytes))


class _FakePdfContext:
    def __init__(self, pages):
        self.pages = pages

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeRenderedImage:
    def __init__(self, *, png_bytes: bytes, jpeg70_bytes: bytes, jpeg50_bytes: bytes):
        self._png = png_bytes
        self._jpeg70 = jpeg70_bytes
        self._jpeg50 = jpeg50_bytes
        self._mode = "png"
        self._quality = None

    def save(self, buffer, format=None, optimize=None, quality=None):  # noqa: A002
        _ = optimize
        payload = self._png
        if format == "JPEG":
            payload = self._jpeg50 if quality == 50 else self._jpeg70
        buffer.write(payload)
        self._quality = quality

    def convert(self, mode):
        _ = mode
        return self


@pytest.mark.asyncio
async def test_pdf_preview_runtime_builders_success_and_error(monkeypatch):
    runtime = file_processing.PdfPreviewRuntime(max_preview_workers=2)
    assert runtime._preview_executor is not None
    assert runtime._resolve_poppler_path() == file_processing.os.getenv("POPPLER_PATH") or file_processing.settings.POPPLER_PATH

    no_pool_runtime = file_processing.PdfPreviewRuntime(max_preview_workers=0)
    assert no_pool_runtime._preview_executor is None

    monkeypatch.setattr(file_processing.shutil, "which", lambda exe, path=None: "pdftoppm")
    monkeypatch.setattr(
        file_processing,
        "pdf_open",
        lambda stream: _FakePdfContext([SimpleNamespace(), SimpleNamespace(), SimpleNamespace()]),
    )

    def fake_build_page_processor(*, conteudo_arquivo, dpi, poppler_path):
        _ = conteudo_arquivo, dpi, poppler_path

        def _processor(page_number):
            return {
                "page": page_number,
                "has_table": page_number == 2,
                "snippet": f"snippet-{page_number}",
                "preview_image": {"page": page_number, "image": f"img-{page_number}"},
            }

        return _processor

    monkeypatch.setattr(runtime, "_build_page_processor", fake_build_page_processor)
    preview = await runtime.preview_arquivo_pdf(b"pdf", ext=".pdf", start_page=1, page_count=0, dpi=72)
    assert preview["num_pages"] == 3
    assert preview["table_pages"] == [2]
    assert preview["sample_rows"][1] == "snippet-1"
    assert preview["preview_images"][2]["image"] == "img-3"

    monkeypatch.setattr(file_processing, "pdf_open", lambda stream: (_ for _ in ()).throw(RuntimeError("pdf bad")))
    error = await runtime.preview_arquivo_pdf(b"pdf", ext=".pdf", start_page=1, page_count=1, dpi=72)
    assert error == {"error": "Falha ao ler arquivo PDF: pdf bad"}


def test_pdf_preview_runtime_process_page_selects_png_or_jpeg(monkeypatch):
    runtime = file_processing.PdfPreviewRuntime(max_preview_workers=0)
    monkeypatch.setattr(
        file_processing,
        "pdf_open",
        lambda stream: _FakePdfContext([_FakePdfPage(tables=[[1]], text="l1\nl2\nl3\nl4")]),
    )

    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [
            _FakeRenderedImage(png_bytes=b"p" * 10, jpeg70_bytes=b"j" * 20, jpeg50_bytes=b"k" * 15)
        ],
    )
    result_png = runtime._process_page(1, conteudo_arquivo=b"pdf", dpi=144, poppler_path=None)
    assert result_png["has_table"] is True
    assert result_png["snippet"] == "l1\nl2\nl3"
    assert result_png["preview_image"]["image"].startswith("data:image/png;base64,")

    monkeypatch.setattr(
        file_processing,
        "convert_from_bytes",
        lambda *args, **kwargs: [
            _FakeRenderedImage(png_bytes=b"p" * 20, jpeg70_bytes=b"j" * 30, jpeg50_bytes=b"k" * 5)
        ],
    )
    result_jpeg = runtime._process_page(1, conteudo_arquivo=b"pdf", dpi=144, poppler_path=None)
    assert result_jpeg["preview_image"]["image"].startswith("data:image/jpeg;base64,")


def test_pdf_asset_utility_runtime_direct_success_and_validation(monkeypatch, tmp_path):
    runtime = file_processing.PdfAssetUtilityRuntime()
    monkeypatch.chdir(tmp_path)

    class FakePixmap:
        def __init__(self, page_index):
            self.page_index = page_index

        def save(self, path):
            with open(path, "wb") as handle:
                handle.write(f"page-{self.page_index}".encode())

    class FakePageForPreview:
        def __init__(self, page_index):
            self.page_index = page_index

        def get_pixmap(self, dpi=150):
            _ = dpi
            return FakePixmap(self.page_index)

    class FakeFitzDoc:
        def __len__(self):
            return 25

        def load_page(self, index):
            return FakePageForPreview(index + 1)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    fake_fitz = ModuleType("fitz")
    fake_fitz.open = lambda file_path: FakeFitzDoc()
    monkeypatch.setitem(sys.modules, "fitz", fake_fitz)

    urls = runtime.generate_pdf_page_images("C:/tmp/catalogo.pdf", "abc")
    assert len(urls) == 20
    assert urls[0] == "/static/previews/abc/page-1.png"
    assert urls[-1] == "/static/previews/abc/page-20.png"

    cropped_page = _FakePdfPage(image_bytes=b"cropped")
    pages = [_FakePdfPage(crop_result=cropped_page), _FakePdfPage(image_bytes=b"second")]
    monkeypatch.setattr(file_processing.pdfplumber, "open", lambda file_path: _FakePdfContext(pages))

    assert runtime.extract_pdf_region_image("C:/tmp/catalogo.pdf", 2, None, 200) == b"second"
    assert runtime.extract_pdf_region_image("C:/tmp/catalogo.pdf", 1, [1, 2, 3, 4], 300) == b"cropped"

    with pytest.raises(ValueError, match="Numero de pagina invalido"):
        runtime.extract_pdf_region_image("C:/tmp/catalogo.pdf", 9, None, 300)
