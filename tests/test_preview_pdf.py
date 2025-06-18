import io
import subprocess
import sys

import pytest

try:
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        PageBreak,
        Paragraph,
    )
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.pdfgen import canvas
    from reportlab.platypus import (
        SimpleDocTemplate,
        Table,
        TableStyle,
        PageBreak,
        Paragraph,
    )
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet

from Backend.services.file_processing_service import preview_arquivo_pdf


def _create_pdf(pages: int = 1) -> bytes:
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(100, 750, f"Page {i + 1}")
        if i < pages - 1:
            c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def _create_pdf_with_table():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("Page 1 text", styles["Normal"]), PageBreak()]
    table = Table([["A", "B"], ["1", "2"]])
    table.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)
    story.append(PageBreak())
    story.append(Paragraph("Last page", styles["Normal"]))
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_preview_pdf_extracts_all():
    pdf_bytes = _create_pdf_with_table()
    res = await preview_arquivo_pdf(pdf_bytes, ".pdf")
    assert res["num_pages"] == 3
    assert res["table_pages"] == []
    assert len(res["preview_images"]) == 1
    assert {img["page"] for img in res["preview_images"]} == {1}
    assert len(res["sample_rows"]) == 1
    assert all(isinstance(v, str) for v in res["sample_rows"].values())


@pytest.mark.asyncio
async def test_preview_pdf_offset_and_limit():
    pdf_bytes = _create_pdf(pages=5)
    res = await preview_arquivo_pdf(pdf_bytes, ".pdf", start_page=2, page_count=2)
    assert res["num_pages"] == 5
    assert len(res["preview_images"]) == 2
    assert {img["page"] for img in res["preview_images"]} == {2, 3}
