from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)


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
