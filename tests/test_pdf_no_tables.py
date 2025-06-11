import asyncio
import io
import subprocess
import sys

import pytest

# Ensure reportlab is available
try:
    import reportlab # type: ignore
except ImportError:  # pragma: no cover - install at runtime
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    import reportlab # type: ignore

from reportlab.pdfgen import canvas

from Backend.services import file_processing_service


def _create_pdf(pages_text):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i, text in enumerate(pages_text):
        c.drawString(100, 750, text)
        if i < len(pages_text) - 1:
            c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def test_processar_pdf_sem_tabelas_extrai_texto():
    pdf_bytes = _create_pdf(["Primeira pagina", "Segunda pagina"])
    res = asyncio.run(
        file_processing_service.processar_arquivo_pdf(pdf_bytes, usar_llm=False)
    )
    assert len(res) == 2
    assert res[0]["dados_brutos_adicionais"]["texto_completo_pagina_1"].startswith("Primeira")
    assert res[1]["dados_brutos_adicionais"]["texto_completo_pagina_2"].startswith("Segunda")

