from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)


class _TopLevelFunctionSurface:

    def test_normalize_validated_data_parses_json_string():
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        parsed = service.normalize_validated_data('{"nome_base":"ABC"}', {"nome_base": "fallback"})
        assert parsed["nome_base"] == "ABC"

    def test_sanitize_extracted_product_discards_invalid_ean_text():
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        sanitized = service.sanitize_extracted_product(
            {
                "nome_base": "Suporte do Apara-barro",
                "ean_original": "Actros 2651 - 2016",
                "descricao_original": "Suporte do Apara-barro",
            }
        )
        assert sanitized["ean_original"] is None

    def test_normalize_import_text_decodes_mojibake_reason():
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        raw = "Nenhum dado de produto pÃƒÂ´de ser extraÃƒÂ­do do PDF."
        normalized = service.normalize_import_text(raw)
        assert "pôde" in normalized
        assert "extraído" in normalized

test_normalize_validated_data_parses_json_string = _TopLevelFunctionSurface.test_normalize_validated_data_parses_json_string
test_sanitize_extracted_product_discards_invalid_ean_text = _TopLevelFunctionSurface.test_sanitize_extracted_product_discards_invalid_ean_text
test_normalize_import_text_decodes_mojibake_reason = _TopLevelFunctionSurface.test_normalize_import_text_decodes_mojibake_reason




