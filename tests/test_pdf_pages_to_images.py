import io
import base64
import subprocess
import sys

# ensure reportlab available
try:
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover - install at runtime
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.pdfgen import canvas

from Backend.services.file_processing_service import pdf_pages_to_images
import pytest


def _create_pdf(pages: int = 1):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(100, 750, f"Page {i+1}")
def _create_pdf(pages=1):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(100, 750, f"Page {i + 1}")
        if i < pages - 1:
            c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_pdf_pages_to_images_basic():
    pdf_bytes = _create_pdf()
    images = await pdf_pages_to_images(pdf_bytes)
    assert len(images) >= 1
    decoded = base64.b64decode(images[0])
    assert decoded.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_pdf_pages_to_images_respects_max_pages():
    pdf_bytes = _create_pdf(3)
async def test_pdf_pages_respects_max_pages():
    pdf_bytes = _create_pdf(pages=3)
    images = await pdf_pages_to_images(pdf_bytes, max_pages=2)
    assert len(images) == 2
