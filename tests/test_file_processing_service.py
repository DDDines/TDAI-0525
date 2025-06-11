import pytest
from Backend.services import file_processing_service

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "data,encoding,esperado_nome,esperada_marca",
    [
        ("nome_base,marca\nA,B\n", "utf-8", "A", "B"),
        ("nome_base;marca\nC;D\n", "latin-1", "C", "D"),
        ("nome_base\tmarca\nE\tF\n", "cp1252", "E", "F"),
    ],
)
async def test_processar_arquivo_csv_encodings(data, encoding, esperado_nome, esperada_marca):
    bytes_data = data.encode(encoding)
    resultado = await file_processing_service.processar_arquivo_csv(bytes_data)
    assert resultado
    assert resultado[0]["nome_base"] == esperado_nome
    assert resultado[0]["marca"] == esperada_marca
