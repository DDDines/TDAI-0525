from Backend.services.file_processing_service import _processar_linha_padronizada


def test_split_sku_nome_auto_when_combined_column():
    row = {"col_0": "1816D 943 666 39 01 Paralama/Estribo", "col_1": "SMC"}
    mapping = {"col_0": "auto:sku_nome", "col_1": "attr:material"}

    result = _processar_linha_padronizada(row, mapping)

    assert result is not None
    assert result.get("sku_original") == "1816D 943 666 39 01"
    assert result.get("nome_base") == "Paralama/Estribo"
    assert result.get("dynamic_attributes", {}).get("material") == "SMC"


def test_split_sku_nome_auto_when_only_sku():
    row = {"col_0": "1816E 943 666 38 01", "col_1": "Paralama/Estribo"}
    mapping = {"col_0": "auto:sku_nome", "col_1": "descricao_original"}

    result = _processar_linha_padronizada(row, mapping)

    assert result is not None
    assert result.get("sku_original") == "1816E 943 666 38 01"
    assert result.get("descricao_original") == "Paralama/Estribo"
