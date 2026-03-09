"""Additional tests for catalog import quality heuristics."""

from __future__ import annotations

import pytest

from Backend.application.services.catalog_import_quality_service import CatalogImportQualityService, CatalogRow


def test_catalog_row_from_mapping_ignores_non_dict_dynamic_attributes():
    """Coerce unknown dynamic payloads into an empty mapping."""
    row = CatalogRow.from_mapping({"nome_base": "Paralama", "dynamic_attributes": ["x"]})

    assert row.dynamic_attributes == {}


def test_quality_helper_methods_cover_edge_patterns():
    """Exercise helper heuristics used by row scoring and filtering."""
    service = CatalogImportQualityService()

    assert service.text_has_context("") is False
    assert service.text_has_context("1234") is False
    assert service.text_looks_like_part_name("") is False
    assert service.text_looks_like_vehicle_application("") is False
    assert service.text_looks_like_vehicle_application("Paralama Actros 2016-2018") is False
    assert service.part_context_strength("Axor 2018") == 0
    assert service.part_context_strength("Paralama dianteiro reforcado") == 4
    assert service.text_looks_like_part_code("@@@") is False
    assert service.text_looks_like_part_code("AA BB CC DD EE FF GG") is False
    assert service.text_looks_like_part_code("ab12 cd34") is False
    assert service.text_looks_like_part_code("1234") is True
    assert service.part_context_strength("Porta curta x") == 3
    assert service.name_looks_like_annotation_header("") is False
    assert service.name_looks_like_annotation_header("---") is False
    assert service.name_looks_like_annotation_header("anota") is True
    assert service.name_looks_like_annotation_header("nota") is True
    assert service.name_looks_like_ocr_noise("") is False
    assert service.name_looks_like_ocr_noise("Paralama dianteiro") is False
    assert service.name_looks_like_ocr_noise("ab cd efgh") is False
    assert service.name_looks_like_ocr_noise("ab cd") is True
    assert service.name_looks_like_ocr_noise("1 2 3 ab") is True
    assert service.name_looks_like_ocr_noise("ab12c") is True
    assert service.name_looks_like_ocr_noise("abc def ghi") is False
    assert service.name_looks_like_marketing_or_operational_copy("Minimum Order Run") is True
    assert service.name_looks_like_marketing_or_operational_copy("Day Turnaround Time*") is True
    assert service.name_looks_like_marketing_or_operational_copy("sharperbags.com Full Color the USA") is True
    assert service.name_looks_like_marketing_or_operational_copy("Princess Frame") is False
    assert service._coerce_row(123) is None


def test_evaluate_product_row_quality_covers_low_quality_reasons_without_sku(monkeypatch):
    """Discard weak rows without SKU/EAN using explicit low-quality guards."""
    service = CatalogImportQualityService()

    assert service.evaluate_product_row_quality(object()) == "Linha descartada por baixa qualidade: formato invalido"
    assert service.evaluate_product_row_quality({"nome_base": "ab 12"}) == "Linha descartada por baixa qualidade: nome com padrao de ruido OCR"

    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)

    assert service.evaluate_product_row_quality(
        {"nome_base": "Minimum Order Run"}
    ) == "Linha descartada por baixa qualidade: nome com texto operacional/comercial"
    assert service.evaluate_product_row_quality({"nome_base": "AA"}) == "Linha descartada por baixa qualidade: nome fraco sem SKU/EAN"
    assert service.evaluate_product_row_quality({"nome_base": "ABC"}) == "Linha descartada por baixa qualidade: nome sem termo forte sem SKU/EAN"
    assert service.evaluate_product_row_quality({"nome_base": "ABCD12345"}) == "Linha descartada por baixa qualidade: nome numerico sem contexto sem SKU/EAN"
    assert service.evaluate_product_row_quality({"nome_base": "ABCD"}) == "Linha descartada por baixa qualidade: nome isolado sem contexto"
    assert service.evaluate_product_row_quality({"nome_base": "ABCD 1"}) == "Linha descartada por baixa qualidade: nome curto sem contexto"
    assert service.evaluate_product_row_quality({"nome_base": "ABCD EFGH"}) == "Linha descartada por baixa qualidade: nome em caixa alta sem contexto"
    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: True)

    assert service.evaluate_product_row_quality(
        {"nome_base": "ZX91A", "descricao_original": "Actros 2016-2018"}
    ) == "Linha descartada por baixa qualidade: codigo sem descricao de peca"


def test_evaluate_product_row_quality_covers_sku_branches_and_numeric_names(monkeypatch):
    """Discard weak rows with SKU using the specific guardrail reasons."""
    service = CatalogImportQualityService()

    assert service.evaluate_product_row_quality(
        {"nome_base": "Paralama dianteiro", "sku_original": "AB"}
    ) == "Linha descartada por baixa qualidade: SKU sem digitos"
    assert service.evaluate_product_row_quality(
        {"nome_base": "", "sku_original": "ZX99"}
    ) == "Linha descartada por baixa qualidade: SKU sem nome/descricao confiavel"
    assert service.evaluate_product_row_quality(
        {"nome_base": "--", "ean_original": "789"}
    ) == "Linha descartada por baixa qualidade: nome sem conteudo"
    assert CatalogImportQualityService().evaluate_product_row_quality(
        {"nome_base": "ab 12345", "sku_original": "ZX99"}
    ) == "Linha descartada por baixa qualidade: nome com padrao de ruido OCR"

    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)

    assert service.evaluate_product_row_quality(
        {"nome_base": "ABCD1", "sku_original": "ABC123"}
    ) == "Linha descartada por baixa qualidade: nome curto com SKU sem contexto de peca"
    assert service.evaluate_product_row_quality(
        {"nome_base": "ABCDEF", "sku_original": "ABCDEF"}
    ) == "Linha descartada por baixa qualidade: SKU duplicado em nome sem descricao"
    assert service.evaluate_product_row_quality(
        {"nome_base": "ABC12345", "sku_original": "ABC12345"}
    ) == "Linha descartada por baixa qualidade: SKU duplicado em nome sem descricao"
    assert service.evaluate_product_row_quality(
        {"nome_base": "Produto X", "sku_original": "ABC123", "descricao_original": "Actros 2016-2018"}
    ) == "Linha descartada por baixa qualidade: SKU com contexto apenas de aplicacao"
    assert service.evaluate_product_row_quality(
        {"nome_base": "Produto interno", "sku_original": "ABC123", "descricao_original": "Actros 2016-2018"}
    ) == "Linha descartada por baixa qualidade: SKU com contexto apenas de aplicacao"
    assert service.evaluate_product_row_quality(
        {"nome_base": "123456", "sku_original": "ZX99"}
    ) == "Linha descartada por baixa qualidade: nome numerico sem contexto"

    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: True)
    assert service.evaluate_product_row_quality(
        {"nome_base": "ZX91AB", "sku_original": "ZX99"}
    ) == "Linha descartada por baixa qualidade: SKU com codigo sem descricao confiavel"
    assert service.evaluate_product_row_quality(
        {"nome_base": "1234567", "ean_original": "789", "descricao_original": ""}
    ) == "Linha descartada por baixa qualidade: nome numerico sem contexto"
    assert service.evaluate_product_row_quality(
        {"nome_base": "ZX9112AB", "ean_original": "789", "descricao_original": "Actros 2016-2018"}
    ) == "Linha descartada por baixa qualidade: nome em formato de codigo sem contexto"


def test_score_product_row_quality_covers_fallback_and_dynamic_hits():
    """Score rows from invalid input through dynamic-context bonuses and penalties."""
    service = CatalogImportQualityService()

    assert service.score_product_row_quality(object()) == 0

    score = service.score_product_row_quality(
        {
            "nome_base": "Paralama dianteiro",
            "sku_original": "ABC12345",
            "descricao_original": "Paralama dianteiro reforcado",
            "categoria_original": "Paralama",
            "dynamic_attributes": {
                "material": "plastico injetado",
                "aplicacao": "linha pesada",
                "cor": "preto fosco",
                "extra": "acabamento premium",
            },
        }
    )

    assert score == 100
    weak_name_score = service.score_product_row_quality(
        {
            "nome_base": "AB12",
            "sku_original": "ABC12345",
            "descricao_original": "",
            "categoria_original": "",
        }
    )
    marketing_score = service.score_product_row_quality(
        {
            "nome_base": "Minimum Order Run",
            "descricao_original": "",
            "categoria_original": "",
        }
    )
    assert weak_name_score < 70
    assert marketing_score < weak_name_score


def test_classify_product_row_quality_covers_direct_discard_and_accept_paths():
    """Classify rows that still trip the strict discard heuristics."""
    service = CatalogImportQualityService()

    ocr_application = service.classify_product_row_quality(
        {"nome_base": "ab 12", "descricao_original": "Actros 2016-2018"}
    )
    code_application = service.classify_product_row_quality(
        {"nome_base": "ABC123", "descricao_original": "Actros 2016-2018"}
    )
    short_code = service.classify_product_row_quality(
        {"nome_base": "1234", "sku_original": "1234", "descricao_original": "Paralama"}
    )
    numeric_name = service.classify_product_row_quality(
        {"nome_base": "123456", "ean_original": "789", "descricao_original": "Freio"}
    )
    code_without_part = service.classify_product_row_quality(
        {"nome_base": "ABC123", "ean_original": "789", "descricao_original": "Actros 2016-2018"}
    )
    accepted = service.classify_product_row_quality(
        {
            "nome_base": "Paralama dianteiro",
            "sku_original": "ABC12345",
            "descricao_original": "Paralama dianteiro reforcado para linha pesada",
            "categoria_original": "Paralama",
            "dynamic_attributes": {"material": "plastico injetado"},
        }
    )

    assert ocr_application["decision"] == "discard"
    assert code_application["decision"] == "discard"
    assert short_code["decision"] == "discard"
    assert numeric_name["decision"] == "quarantine"
    assert code_without_part["decision"] == "discard"
    assert accepted == {"decision": "accept", "score": accepted["score"], "reason": None}
    assert accepted["score"] >= 58


def test_classify_product_row_quality_covers_low_score_and_weak_context_quarantine(monkeypatch):
    """Cover quarantine branches that require bypassing strict discard reasons."""
    service = CatalogImportQualityService()

    monkeypatch.setattr(service, "evaluate_product_row_quality", lambda _data: None)
    monkeypatch.setattr(service, "score_product_row_quality", lambda _data: 40)

    low_score = service.classify_product_row_quality(
        {"nome_base": "Produto", "descricao_original": "", "categoria_original": ""}
    )
    assert low_score["decision"] == "quarantine"
    assert low_score["reason"] == "Linha em quarentena: score de qualidade muito baixo"

    monkeypatch.setattr(service, "score_product_row_quality", lambda _data: 57)
    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_part_name", lambda _value: False)
    monkeypatch.setattr(service, "text_has_context", lambda value: bool(value) and str(value) != "fraco")

    weak_context = service.classify_product_row_quality(
        {"nome_base": "fraco", "descricao_original": "", "categoria_original": ""}
    )
    assert weak_context["decision"] == "quarantine"
    assert weak_context["reason"] == "Linha em quarentena: contexto fraco para nome do produto"


@pytest.mark.parametrize(
    ("row", "patches", "expected_reason"),
    [
        (
            {"nome_base": "ab 12", "descricao_original": "", "categoria_original": ""},
            {"name_looks_like_ocr_noise": lambda _value: True},
            "Linha em quarentena: nome com padrao de ruido OCR",
        ),
        (
            {"nome_base": "123456", "descricao_original": "Freio", "categoria_original": ""},
            {"name_looks_like_ocr_noise": lambda _value: False},
            "Linha em quarentena: nome parece apenas codigo sem contexto de peca",
        ),
    ],
)
def test_classify_product_row_quality_quarantine_branches_with_patched_strict_reason(
    monkeypatch,
    row,
    patches,
    expected_reason,
):
    """Cover quarantine-only branches by bypassing the strict discard phase."""
    service = CatalogImportQualityService()

    monkeypatch.setattr(service, "evaluate_product_row_quality", lambda _data: None)
    monkeypatch.setattr(service, "score_product_row_quality", lambda _data: 70)
    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_part_name", lambda _value: False)
    for attr_name, value in patches.items():
        monkeypatch.setattr(service, attr_name, value)

    result = service.classify_product_row_quality(row)

    assert result["decision"] == "quarantine"
    assert result["reason"] == expected_reason


def test_quality_service_covers_remaining_score_and_quarantine_branches(monkeypatch):
    """Exercise remaining quarantine reasons and category application penalties."""
    service = CatalogImportQualityService()

    assert service.score_product_row_quality(
        {
            "nome_base": "Paralama dianteiro",
            "descricao_original": "Paralama reforcado",
            "categoria_original": "Actros 2016-2018",
        }
    ) < service.score_product_row_quality(
        {
            "nome_base": "Paralama dianteiro",
            "descricao_original": "Paralama reforcado",
            "categoria_original": "Paralama",
        }
    )

    monkeypatch.setattr(service, "evaluate_product_row_quality", lambda _data: None)
    monkeypatch.setattr(service, "score_product_row_quality", lambda _data: 70)
    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: True)
    monkeypatch.setattr(service, "text_looks_like_part_name", lambda _value: False)
    monkeypatch.setattr(
        service,
        "text_looks_like_vehicle_application",
        lambda value: "Actros" in str(value or ""),
    )

    ocr_application = service.classify_product_row_quality(
        {"nome_base": "ab 12", "descricao_original": "Actros 2016-2018"}
    )
    assert ocr_application["reason"] == "Linha em quarentena: nome fraco e contexto apenas de aplicacao"

    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: True)

    code_application = service.classify_product_row_quality(
        {"nome_base": "ABC123", "descricao_original": "Actros 2016-2018"}
    )
    assert (
        code_application["reason"]
        == "Linha em quarentena: nome parece codigo e contexto indica apenas aplicacao"
    )

    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: False)
    monkeypatch.setattr(
        service,
        "text_looks_like_part_name",
        lambda value: "Paralama" in str(value or ""),
    )
    short_code = service.classify_product_row_quality(
        {"nome_base": "1234", "sku_original": "1234", "descricao_original": "Paralama"}
    )
    assert short_code["reason"] == "Linha em quarentena: codigo curto requer contexto forte de peca"


def test_evaluate_product_row_quality_covers_remaining_contextual_and_numeric_branches(monkeypatch):
    """Hit the remaining discard branches that require non-application context or patched OCR heuristics."""
    service = CatalogImportQualityService()

    assert service.evaluate_product_row_quality(
        {"nome_base": "ab 12345", "categoria_original": "Premium"}
    ) == "Linha descartada por baixa qualidade: nome com padrao de ruido OCR"

    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)
    assert service.evaluate_product_row_quality(
        {"nome_base": "123456", "categoria_original": "Premium"}
    ) == "Linha descartada por baixa qualidade: nome apenas numerico sem descricao"


def test_score_and_classify_cover_remaining_nome_fallbacks(monkeypatch):
    """Cover weak-name scoring without dynamic dicts and code quarantine without vehicle-application context."""
    service = CatalogImportQualityService()

    score = service.score_product_row_quality(
        {
            "nome_base": "AB12",
            "sku_original": "ZX99",
            "descricao_original": "Paralama",
            "dynamic_attributes": [],
        }
    )
    assert score > 0

    monkeypatch.setattr(service, "evaluate_product_row_quality", lambda _data: None)
    monkeypatch.setattr(service, "score_product_row_quality", lambda _data: 70)
    monkeypatch.setattr(service, "name_looks_like_ocr_noise", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_part_code", lambda _value: True)
    monkeypatch.setattr(service, "text_looks_like_part_name", lambda _value: False)
    monkeypatch.setattr(service, "text_looks_like_vehicle_application", lambda _value: False)

    result = service.classify_product_row_quality(
        {"nome_base": "ABC123", "descricao_original": "sem contexto de aplicacao"}
    )

    assert result["decision"] == "quarantine"
    assert result["reason"] == "Linha em quarentena: nome parece codigo sem descricao confiavel"


def test_quality_service_covers_remaining_none_and_score_fallback_paths():
    """Cover remaining non-discard exits and score branches without nome or dynamic dicts."""
    service = CatalogImportQualityService()

    assert service.evaluate_product_row_quality(
        {"nome_base": "", "sku_original": "ZX99", "descricao_original": "Paralama reforcado"}
    ) is None
    assert service.evaluate_product_row_quality(
        {"nome_base": "AB1234", "sku_original": "ZX99", "categoria_original": "Premium"}
    ) is None

    score = service.score_product_row_quality(
        CatalogRow(
            nome_base="",
            sku_original="ZX99",
            descricao_original="Paralama reforcado",
            categoria_original="",
            dynamic_attributes=["material"],
        )
    )
    assert score > 0
