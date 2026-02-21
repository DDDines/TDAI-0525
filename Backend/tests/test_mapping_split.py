from Backend.services.file_processing_service import _processar_linha_padronizada
from Backend.routers.produtos import (
    _avaliar_qualidade_linha_produto,
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
