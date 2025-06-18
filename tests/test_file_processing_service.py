import pytest
import base64
import io
import subprocess
import sys
from Backend.services import file_processing_service

# Ensure reportlab is available
try:
    import reportlab  # type: ignore
except ImportError:  # pragma: no cover - install at runtime
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    import reportlab  # type: ignore

from reportlab.pdfgen import canvas


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,encoding,esperado_nome,esperada_marca",
    [
        ("nome_base,marca\nA,B\n", "utf-8", "A", "B"),
        ("nome_base;marca\nC;D\n", "latin-1", "C", "D"),
        ("nome_base\tmarca\nE\tF\n", "cp1252", "E", "F"),
    ],
)
async def test_processar_arquivo_csv_encodings(
    data, encoding, esperado_nome, esperada_marca
):
    bytes_data = data.encode(encoding)
    resultado = await file_processing_service.processar_arquivo_csv(bytes_data)
    assert resultado
    assert resultado[0]["nome_base"] == esperado_nome
    assert resultado[0]["marca"] == esperada_marca


@pytest.mark.asyncio
async def test_pdf_pages_to_images_returns_base64():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Test")
    c.save()
    pdf_bytes = buf.getvalue()

    images = await file_processing_service.pdf_pages_to_images(pdf_bytes, max_pages=1)
    assert len(images) == 1
    decoded = base64.b64decode(images[0])
    assert decoded.startswith(b"\x89PNG")


@pytest.mark.asyncio
async def test_preview_arquivo_pdf_returns_page_info():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(100, 750, "Hello")
    c.showPage()
    c.drawString(100, 750, "World")
    c.save()
    pdf_bytes = buf.getvalue()

    res = await file_processing_service.preview_arquivo_pdf(pdf_bytes, ".pdf")
    assert res.get("num_pages") == 2
    assert res.get("table_pages") == []
    assert len(res["preview_images"]) == 1
    assert 1 in res["sample_rows"]
