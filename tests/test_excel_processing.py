import asyncio
import pandas as pd
import io
from Backend.services import file_processing_service

def create_excel_bytes():
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame({"nome": ["A", "B"], "sku": ["A1", "B1"]}).to_excel(writer, index=False, sheet_name="Primeira")
        pd.DataFrame({"nome": ["C"], "sku": ["C1"]}).to_excel(writer, index=False, sheet_name="Segunda")
    return output.getvalue()

async def call_process(content, sheet=None):
    return await file_processing_service.processar_arquivo_excel(content, sheet_name=sheet)

def test_processar_multiplas_abas():
    content = create_excel_bytes()
    res = asyncio.run(call_process(content))
    assert len(res) == 3


def test_processar_apenas_uma_aba():
    content = create_excel_bytes()
    res = asyncio.run(call_process(content, sheet="Segunda"))
    assert len(res) == 1
