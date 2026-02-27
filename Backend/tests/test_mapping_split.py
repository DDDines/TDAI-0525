from Backend.testing.runtime_apis import _processar_linha_padronizada
from Backend.routers.produtos import (
    _avaliar_qualidade_linha_produto,
    _classificar_qualidade_linha_produto,
    _is_non_critical_import_reason,
    _sanitize_produto_extraido,
)


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


def test_merge_multiple_columns_into_description():
    row = {
        "col_0": "1816D 943 666 39 01 Paralama/Estribo",
        "col_1": "Actros 2651 - 2016",
        "col_2": "SMC",
    }
    mapping = {
        "col_0": "auto:sku_nome",
        "col_1": "descricao_original",
        "col_2": "descricao_original",
    }

    result = _processar_linha_padronizada(row, mapping)

    assert result is not None
    assert result.get("sku_original") == "1816D 943 666 39 01"
    assert result.get("nome_base") == "Paralama/Estribo"
    assert result.get("descricao_original") == "Actros 2651 - 2016 | SMC"


def test_split_sku_nome_auto_with_alphanumeric_original_code():
    row = {
        "col_0": "3035D BC4517C831BBXWA Ponteira para-choque Cargo 2428",
        "col_1": "Plastico",
    }
    mapping = {"col_0": "auto:sku_nome", "col_1": "attr:material"}

    result = _processar_linha_padronizada(row, mapping)

    assert result is not None
    assert result.get("sku_original") == "3035D BC4517C831BBXWA"
    assert result.get("nome_base") == "Ponteira para-choque Cargo 2428"
    assert result.get("dynamic_attributes", {}).get("material") == "Plastico"


def test_default_header_aliases_feed_dynamic_attributes():
    row = {
        "n_fab": "1816D",
        "n_original": "943 666 39 01",
        "descricao": "Paralama/Estribo",
        "aplicacao": "Actros 2651 - 2016",
        "material": "SMC",
    }

    result = _processar_linha_padronizada(row, None)

    assert result is not None
    assert result.get("sku_original") == "1816D"
    assert result.get("descricao_original") == "Paralama/Estribo"
    assert result.get("dynamic_attributes", {}).get("codigo_original") == "943 666 39 01"
    assert result.get("dynamic_attributes", {}).get("aplicacao") == "Actros 2651 - 2016"
    assert result.get("dynamic_attributes", {}).get("material") == "SMC"


def test_split_sku_nome_auto_handles_directional_token():
    row = {"n_fab": "3035 E BC4517K903BBXWA Ponteira para-choque"}

    result = _processar_linha_padronizada(row, None)

    assert result is not None
    assert result.get("sku_original") == "3035 E BC4517K903BBXWA"
    assert result.get("nome_base") == "Ponteira para-choque"


def test_quality_filter_rejects_noise_row():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "i",
            "sku_original": None,
            "ean_original": None,
        }
    )
    assert reason is not None
    assert reason.startswith("Linha descartada por baixa qualidade")


def test_quality_filter_accepts_real_catalog_row():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "Paralama/Estribo",
            "sku_original": "1816D 943 666 39 01",
            "ean_original": None,
        }
    )
    assert reason is None


def test_quality_filter_rejects_annotation_header_even_with_context():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "Anotacoes:",
            "sku_original": None,
            "ean_original": None,
            "dynamic_attributes": {"material": "SMC"},
        }
    )
    assert reason is not None
    assert "cabecalho de anotacoes" in reason


def test_quality_filter_rejects_annotation_header_variant():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "Anotages:",
            "sku_original": None,
            "ean_original": None,
        }
    )
    assert reason is not None
    assert "cabecalho de anotacoes" in reason


def test_quality_filter_rejects_numeric_name_with_sku_without_description():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "8212",
            "sku_original": "8212",
            "ean_original": None,
            "dynamic_attributes": {"material": "Metalico"},
        }
    )
    assert reason is not None
    assert (
        "sem descricao" in reason
        or "nome curto com SKU" in reason
        or "codigo curto sem contexto forte de peca" in reason
    )


def test_quality_filter_rejects_sku_duplicated_in_name_without_description():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "1663 E",
            "sku_original": "1663 E",
            "ean_original": None,
            "dynamic_attributes": {"aplicacao": "Actros 2651 - 2016"},
        }
    )
    assert reason is not None
    assert (
        "SKU duplicado em nome sem descricao" in reason
        or "nome curto com SKU" in reason
    )


def test_quality_classifier_quarantines_code_like_name_with_application_context_only():
    result = _classificar_qualidade_linha_produto(
        {
            "nome_base": "1663 E",
            "sku_original": "1663 E",
            "descricao_original": "Axor 2012",
            "categoria_original": "",
        }
    )
    assert result["decision"] in {"quarantine", "discard"}
    assert any(
        token in (result["reason"] or "").lower()
        for token in ["codigo", "sem descricao", "ruido ocr"]
    )


def test_quality_filter_accepts_numeric_name_when_description_is_good():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "8212",
            "sku_original": "8212",
            "ean_original": None,
            "descricao_original": "Paralama dianteiro superior",
        }
    )
    assert reason is None


def test_non_critical_reason_classifier():
    assert _is_non_critical_import_reason("Faltam nome_base e sku_original")
    assert _is_non_critical_import_reason(
        "Nenhum dado de produto pode ser extraido do PDF (pode estar protegido, vazio ou somente imagem sem OCR)."
    )
    assert not _is_non_critical_import_reason("Erro ao converter linha: valor invalido")


def test_sanitize_discards_textual_ean():
    payload = {
        "nome_base": "Paralama",
        "ean_original": "Actros 2651 - 2016",
        "dados_brutos_adicionais": {},
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("ean_original") is None
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert extras.get("ean_original_descartado") == "Actros 2651 - 2016"


def test_sanitize_truncates_fields_with_limits():
    payload = {
        "nome_base": "Produto Teste",
        "sku_original": "S" * 120,
        "marca": "M" * 130,
        "modelo": "X" * 180,
        "categoria_original": "C" * 200,
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert len(sanitized.get("sku_original")) == 100
    assert len(sanitized.get("marca")) == 100
    assert len(sanitized.get("modelo")) == 100
    assert len(sanitized.get("categoria_original")) == 150


def test_quality_classifier_quarantines_numeric_name_with_application_only():
    result = _classificar_qualidade_linha_produto(
        {
            "nome_base": "8212",
            "sku_original": "8212",
            "descricao_original": "Actros 2651 - 2016",
            "categoria_original": "",
        }
    )
    assert result["decision"] in {"quarantine", "discard"}
    assert any(
        token in (result["reason"] or "").lower()
        for token in ["codigo", "sem descricao", "ruido ocr"]
    )


def test_sanitize_promotes_part_name_from_raw_fields():
    payload = {
        "nome_base": "8212",
        "sku_original": "8212",
        "dados_brutos_adicionais": {"col_2": "Paralama Duplo"},
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("descricao_original") == "Paralama Duplo"
    assert sanitized.get("nome_base") == "Paralama Duplo"
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert extras.get("descricao_substituida_por_dados_brutos") == "col_2"


def test_sanitize_promotes_category_part_name_when_name_is_code():
    payload = {
        "nome_base": "7092E 3175158",
        "sku_original": "7092E 3175158",
        "categoria_original": "Estribo Superior",
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("descricao_original") == "Estribo Superior"
    assert sanitized.get("nome_base") == "Estribo Superior"


def test_sanitize_drops_placeholder_sku_values():
    payload = {
        "nome_base": "Paralama Dianteiro",
        "sku_original": "None",
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("sku_original") is None
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert extras.get("sku_original_descartado") == "None"


def test_sanitize_merges_raw_payloads_and_promotes_part_description():
    payload = {
        "nome_base": "1663 E",
        "sku_original": "1663 E",
        "categoria_original": "Axor",
        "dados_brutos_adicionais": {"col_1": "930 520 00 19"},
        "dados_brutos_web": {"col_2": "Paralama Dianteiro"},
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("descricao_original") == "Paralama Dianteiro"
    assert sanitized.get("nome_base") == "Paralama Dianteiro"
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert extras.get("col_1") == "930 520 00 19"
    assert extras.get("col_2") == "Paralama Dianteiro"


def test_quality_filter_rejects_sku_duplicated_name_with_application_only_context():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "1663 E",
            "sku_original": "1663 E",
            "descricao_original": "Actros 2651 - 2016",
            "categoria_original": "Axor",
        }
    )
    assert reason is not None
    assert (
        "SKU duplicado em nome sem descricao" in reason
        or "ruido OCR" in reason
    )


def test_quality_filter_rejects_ocr_noise_name_with_application_only():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "as 927",
            "sku_original": "8199",
            "descricao_original": "Actros 2651 - 2016",
            "categoria_original": "",
        }
    )
    assert reason is not None
    assert "ruido OCR" in reason


def test_quality_filter_rejects_short_name_with_sku_without_part_context():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "8212",
            "sku_original": "8212",
            "descricao_original": "",
            "categoria_original": "",
            "dynamic_attributes": {"material": "Metalico"},
        }
    )
    assert reason is not None
    assert (
        "nome curto com SKU" in reason
        or "codigo curto sem contexto forte de peca" in reason
    )


def test_quality_filter_rejects_short_numeric_code_with_weak_part_context():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "8199",
            "sku_original": "8199",
            "descricao_original": "Paralama",
            "categoria_original": "",
            "ean_original": None,
        }
    )
    assert reason is not None
    assert "codigo curto sem contexto forte de peca" in reason


def test_quality_filter_rejects_sku_with_only_vehicle_application_context():
    reason = _avaliar_qualidade_linha_produto(
        {
            "nome_base": "1663 E",
            "sku_original": "1663 E",
            "descricao_original": "Actros 2651 - 2016",
            "categoria_original": "",
            "dynamic_attributes": {"aplicacao": "Axor 2014"},
        }
    )
    assert reason is not None
    assert (
        "apenas de aplicacao" in reason
        or "ruido OCR" in reason
        or "nome curto com SKU" in reason
    )


def test_sanitize_promotes_part_name_from_raw_when_description_is_application():
    payload = {
        "nome_base": "oof D",
        "sku_original": "8199",
        "descricao_original": "Actros 2651 - 2016",
        "dados_brutos_adicionais": {
            "col_1": "Paralama Duplo",
            "col_2": "Actros 2651 - 2016",
        },
    }

    sanitized = _sanitize_produto_extraido(payload)

    assert sanitized.get("descricao_original") == "Paralama Duplo"
    assert sanitized.get("nome_base") == "Paralama Duplo"
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert extras.get("descricao_substituida_por_dados_brutos") == "col_1"

