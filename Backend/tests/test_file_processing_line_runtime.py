from Backend.testing.runtime_apis import file_processing


class _TopLevelFunctionSurface:

    def test_line_runtime_normaliza_mapeamento_invertido():
        runtime = file_processing.LineNormalizationRuntime()
    
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
        runtime = file_processing.LineNormalizationRuntime()
    
        bbox, mode = runtime.coerce_region_bbox([0.1, 0.2, 0.9, 0.8], 1000.0, 500.0)
    
        assert mode == "normalized"
        assert bbox == (100.0, 100.0, 900.0, 400.0)

    def test_line_runtime_split_sku_nome_auto_coluna_combinada():
        runtime = file_processing.LineNormalizationRuntime()
    
        sku, nome = runtime.split_sku_nome_auto("1816D 943 666 39 01 Paralama/Estribo")
    
        assert sku == "1816D 943 666 39 01"
        assert nome == "Paralama/Estribo"

    def test_line_runtime_limpeza_e_conteudo_util():
        runtime = file_processing.LineNormalizationRuntime()
    
        assert runtime.limpar_valor_extraido("  #N/A  ") is None
        assert runtime.limpar_valor_extraido("  Valor X  ") == "Valor X"
        assert not runtime.valor_tem_conteudo_util("-")
        assert runtime.valor_tem_conteudo_util("SMC")

    def test_line_mapping_workflow_processa_coluna_auto_sku_nome():
        workflow = file_processing.LineMappingWorkflow()
    
        result = workflow.processar_linha_padronizada(
            {"col_0": "1816D 943 666 39 01 Paralama/Estribo", "col_1": "SMC"},
            {"col_0": "auto:sku_nome", "col_1": "attr:material"},
        )
    
        assert result is not None
        assert result.get("sku_original") == "1816D 943 666 39 01"
        assert result.get("nome_base") == "Paralama/Estribo"
        assert result.get("dynamic_attributes", {}).get("material") == "SMC"

    def test_line_mapping_workflow_descarta_linha_sem_nome_e_sku_com_mapping_explicito():
        workflow = file_processing.LineMappingWorkflow()
    
        result = workflow.processar_linha_padronizada(
            {"col_0": "", "col_1": None},
            {"col_0": "descricao_original"},
        )
    
        assert result is not None
        assert result.get("motivo_descarte") == "Faltam nome_base e sku_original"

test_line_runtime_normaliza_mapeamento_invertido = _TopLevelFunctionSurface.test_line_runtime_normaliza_mapeamento_invertido
test_line_runtime_coerce_region_bbox_normalizado = _TopLevelFunctionSurface.test_line_runtime_coerce_region_bbox_normalizado
test_line_runtime_split_sku_nome_auto_coluna_combinada = _TopLevelFunctionSurface.test_line_runtime_split_sku_nome_auto_coluna_combinada
test_line_runtime_limpeza_e_conteudo_util = _TopLevelFunctionSurface.test_line_runtime_limpeza_e_conteudo_util
test_line_mapping_workflow_processa_coluna_auto_sku_nome = _TopLevelFunctionSurface.test_line_mapping_workflow_processa_coluna_auto_sku_nome
test_line_mapping_workflow_descarta_linha_sem_nome_e_sku_com_mapping_explicito = _TopLevelFunctionSurface.test_line_mapping_workflow_descarta_linha_sem_nome_e_sku_com_mapping_explicito










