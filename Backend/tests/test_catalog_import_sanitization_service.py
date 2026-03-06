"""Module test catalog import sanitization service.

Contains backend logic related to test catalog import sanitization service and documents its role in the OOP architecture.
"""

from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""

    def test_normalize_validated_data_parses_json_string():
        """Run test normalize validated data parses json string in this workflow."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        parsed = service.normalize_validated_data(
            '{"nome_base":"ABC"}',
            {"nome_base": "fallback"},
        )
        assert parsed["nome_base"] == "ABC"

    def test_sanitize_extracted_product_discards_invalid_ean_text():
        """Run test sanitize extracted product discards invalid ean text in this workflow."""
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
        """Run test normalize import text decodes mojibake reason in this workflow."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        raw = "Nenhum dado de produto p\u00c3\u0192\u00c6\u2019\u00c3\u201a\u00c2\u00b4de ser extra\u00c3\u0192\u00c6\u2019\u00c3\u201a\u00c2\u00addo do PDF."
        normalized = service.normalize_import_text(raw)
        assert "p\u00f4de" in normalized
        assert "extra\u00eddo" in normalized

    def test_sanitize_extracted_product_applies_conservative_ocr_corrections():
        """Run test sanitize extracted product applies conservative ocr corrections in this workflow."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        sanitized = service.sanitize_extracted_product(
            {
                "nome_base": "Suporte de Fixagdo",
                "descricao_original": "Reservatdrio de AR",
                "dynamic_attributes": {"material": "Reforgo Metalico"},
            }
        )
        assert sanitized["nome_base"] == "Suporte de Fixa\u00e7\u00e3o"
        assert sanitized["descricao_original"] == "Reservat\u00f3rio de AR"
        assert sanitized["dynamic_attributes"]["material"] == "Refor\u00e7o Met\u00e1lico"

    def test_sanitize_extracted_product_uses_name_as_description_when_missing():
        """Run test sanitize extracted product uses name as description when missing in this workflow."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        sanitized = service.sanitize_extracted_product(
            {
                "nome_base": "Paralama Traseiro Esquerdo",
                "descricao_original": "",
            }
        )
        assert sanitized["descricao_original"] == "Paralama Traseiro Esquerdo"
        extras = sanitized.get("dados_brutos_adicionais") or {}
        assert extras.get("descricao_substituida_por_nome_base") is True

    def test_sanitize_extracted_product_promotes_part_name_from_dynamic_attributes():
        """Run test sanitize extracted product promotes part name from dynamic attributes in this workflow."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        sanitized = service.sanitize_extracted_product(
            {
                "nome_base": "1724E 944 880 00 06",
                "sku_original": "1724E 944 880 00 06",
                "descricao_original": "",
                "dynamic_attributes": {
                    "aplicacao": "Paralama Traseiro da Cabine",
                    "material": "SMC",
                },
            }
        )
        assert sanitized["descricao_original"] == "Paralama Traseiro da Cabine"
        assert sanitized["nome_base"] == "Paralama Traseiro da Cabine"
        extras = sanitized.get("dados_brutos_adicionais") or {}
        assert extras.get("descricao_substituida_por_atributo_dinamico") is True

    def test_sanitize_extracted_product_removes_company_contact_noise():
        """Ensure import sanitization strips company/contact snippets from product text fields."""
        service = CatalogImportSanitizationService(CatalogImportQualityService())
        sanitized = service.sanitize_extracted_product(
            {
                "nome_base": "de AR 60 Litros Uouu Comercio Eletronico 986 345 430 8205",
                "descricao_original": (
                    "Reservatorio de ar para linha pesada. "
                    "Contato via whatsapp 11 99888 7766 ou www.lojaexemplo.com."
                ),
                "marca": "Uouu Comercio Eletronico",
                "dynamic_attributes": {
                    "aplicacao": "Scania R450",
                    "obs": "Telefone 11 99888 7766",
                },
            }
        )

        assert sanitized["nome_base"] == "de AR 60 Litros Uouu"
        assert sanitized["descricao_original"] == "Reservatório de ar para linha pesada."
        assert sanitized["marca"] == "Uouu"
        assert sanitized["dynamic_attributes"]["aplicacao"] == "Scania R450"
        assert sanitized["dynamic_attributes"]["obs"] is None


test_normalize_validated_data_parses_json_string = _TopLevelFunctionSurface.test_normalize_validated_data_parses_json_string
test_sanitize_extracted_product_discards_invalid_ean_text = _TopLevelFunctionSurface.test_sanitize_extracted_product_discards_invalid_ean_text
test_normalize_import_text_decodes_mojibake_reason = _TopLevelFunctionSurface.test_normalize_import_text_decodes_mojibake_reason
test_sanitize_extracted_product_applies_conservative_ocr_corrections = _TopLevelFunctionSurface.test_sanitize_extracted_product_applies_conservative_ocr_corrections
test_sanitize_extracted_product_uses_name_as_description_when_missing = _TopLevelFunctionSurface.test_sanitize_extracted_product_uses_name_as_description_when_missing
test_sanitize_extracted_product_promotes_part_name_from_dynamic_attributes = _TopLevelFunctionSurface.test_sanitize_extracted_product_promotes_part_name_from_dynamic_attributes
test_sanitize_extracted_product_removes_company_contact_noise = _TopLevelFunctionSurface.test_sanitize_extracted_product_removes_company_contact_noise
