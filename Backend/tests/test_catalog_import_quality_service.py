from Backend.application.services.catalog_import_quality_service import (
    CatalogRow,
    CatalogImportQualityService,
)


class _TopLevelFunctionSurface:

    def test_text_has_context_rejects_symbol_only_values():
        service = CatalogImportQualityService()
        assert service.text_has_context("---") is False
        assert service.text_has_context("|") is False

    def test_text_looks_like_part_code_detects_structured_codes():
        service = CatalogImportQualityService()
        assert service.text_looks_like_part_code("2C456840300BB") is True
        assert service.text_looks_like_part_code("Paralama Dianteiro") is False

    def test_classify_product_row_quality_discards_annotation_header():
        service = CatalogImportQualityService()
        result = service.classify_product_row_quality(
            {
                "nome_base": "Anotacoes",
                "sku_original": "",
                "descricao_original": "",
                "categoria_original": "",
                "dynamic_attributes": {},
            }
        )
        assert result["decision"] == "discard"
        assert "cabecalho de anotacoes" in (result["reason"] or "")

    def test_classify_product_row_quality_quarantines_code_without_part_context():
        service = CatalogImportQualityService()
        result = service.classify_product_row_quality(
            {
                "nome_base": "3235 E TJG809201A",
                "sku_original": "3235 E TJG809201A",
                "descricao_original": "Actros 2651 - 2016",
                "categoria_original": "",
                "dynamic_attributes": {},
            }
        )
        assert result["decision"] in {"discard", "quarantine"}
        assert result["decision"] != "accept"

    def test_evaluate_discards_sku_code_with_application_only_context():
        service = CatalogImportQualityService()
        reason = service.evaluate_product_row_quality(
            {
                "nome_base": "1663 D",
                "sku_original": "1663 D",
                "descricao_original": "Actros 2651 - 2016",
                "categoria_original": "",
                "dynamic_attributes": {"aplicacao": "Actros 2651 - 2016"},
            }
        )
        assert reason is not None
        reason_lower = reason.lower()
        assert ("codigo" in reason_lower) or ("ruido ocr" in reason_lower)

    def test_evaluate_keeps_sku_code_when_dynamic_part_context_exists():
        service = CatalogImportQualityService()
        reason = service.evaluate_product_row_quality(
            {
                "nome_base": "1663 D",
                "sku_original": "1663 D",
                "descricao_original": "Actros 2651 - 2016",
                "categoria_original": "",
                "dynamic_attributes": {
                    "aplicacao": "Actros 2651 - 2016",
                    "descricao_peca": "Paralama superior",
                },
            }
        )
        assert reason is None

    def test_evaluate_discards_short_numeric_code_without_strong_part_context():
        service = CatalogImportQualityService()
        reason = service.evaluate_product_row_quality(
            {
                "nome_base": "402",
                "sku_original": "402",
                "descricao_original": "Paralama",
                "categoria_original": "",
                "ean_original": None,
                "dynamic_attributes": {"material": "metalico"},
            }
        )
        assert reason is not None
        assert "codigo curto sem contexto forte de peca" in reason

    def test_evaluate_accepts_short_numeric_code_with_strong_part_context():
        service = CatalogImportQualityService()
        reason = service.evaluate_product_row_quality(
            {
                "nome_base": "402",
                "sku_original": "402",
                "descricao_original": "Paralama dianteiro superior em plastico injetado",
                "categoria_original": "",
                "ean_original": None,
                "dynamic_attributes": {"material": "plastico injetado"},
            }
        )
        assert reason is None

    def test_quality_service_accepts_catalog_row_domain_object():
        service = CatalogImportQualityService()
        row = CatalogRow(
            nome_base="Paralama dianteiro",
            sku_original="ABC12345",
            descricao_original="Paralama superior para linha pesada",
            categoria_original="Paralama",
            dynamic_attributes={"material": "plastico injetado"},
        )
    
        result = service.classify_product_row_quality(row)
    
        assert result["decision"] == "accept"

test_text_has_context_rejects_symbol_only_values = _TopLevelFunctionSurface.test_text_has_context_rejects_symbol_only_values
test_text_looks_like_part_code_detects_structured_codes = _TopLevelFunctionSurface.test_text_looks_like_part_code_detects_structured_codes
test_classify_product_row_quality_discards_annotation_header = _TopLevelFunctionSurface.test_classify_product_row_quality_discards_annotation_header
test_classify_product_row_quality_quarantines_code_without_part_context = _TopLevelFunctionSurface.test_classify_product_row_quality_quarantines_code_without_part_context
test_evaluate_discards_sku_code_with_application_only_context = _TopLevelFunctionSurface.test_evaluate_discards_sku_code_with_application_only_context
test_evaluate_keeps_sku_code_when_dynamic_part_context_exists = _TopLevelFunctionSurface.test_evaluate_keeps_sku_code_when_dynamic_part_context_exists
test_evaluate_discards_short_numeric_code_without_strong_part_context = _TopLevelFunctionSurface.test_evaluate_discards_short_numeric_code_without_strong_part_context
test_evaluate_accepts_short_numeric_code_with_strong_part_context = _TopLevelFunctionSurface.test_evaluate_accepts_short_numeric_code_with_strong_part_context
test_quality_service_accepts_catalog_row_domain_object = _TopLevelFunctionSurface.test_quality_service_accepts_catalog_row_domain_object
















