import Backend.services.file_processing_service as file_processing


def test_line_runtime_normaliza_mapeamento_invertido():
    runtime = file_processing._LineNormalizationRuntime()

    result = runtime.normalizar_mapeamento_usuario(
        {
            "nome_base": "col_0",
            "sku_original": "col_1",
            "attr:material": "col_2",
        },
        {"col_0": "Nome", "col_1": "SKU", "col_2": "SMC"},
    )

    assert result == {
        "col_0": "nome_base",
        "col_1": "sku_original",
        "col_2": "attr:material",
    }


def test_line_runtime_coerce_region_bbox_normalizado():
    runtime = file_processing._LineNormalizationRuntime()

    bbox, mode = runtime.coerce_region_bbox([0.1, 0.2, 0.9, 0.8], 1000.0, 500.0)

    assert mode == "normalized"
    assert bbox == (100.0, 100.0, 900.0, 400.0)


def test_line_runtime_split_sku_nome_auto_coluna_combinada():
    runtime = file_processing._LineNormalizationRuntime()

    sku, nome = runtime.split_sku_nome_auto("1816D 943 666 39 01 Paralama/Estribo")

    assert sku == "1816D 943 666 39 01"
    assert nome == "Paralama/Estribo"


def test_line_runtime_limpeza_e_conteudo_util():
    runtime = file_processing._LineNormalizationRuntime()

    assert runtime.limpar_valor_extraido("  #N/A  ") is None
    assert runtime.limpar_valor_extraido("  Valor X  ") == "Valor X"
    assert not runtime.valor_tem_conteudo_util("-")
    assert runtime.valor_tem_conteudo_util("SMC")
