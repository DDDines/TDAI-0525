from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)


def test_parse_price_handles_brazilian_format():
    service = WebEnrichmentNormalizationService()
    assert service.parse_price("R$ 1.234,56") == 1234.56


def test_sanitize_code_value_removes_noise_suffix():
    service = WebEnrichmentNormalizationService()
    assert service.sanitize_code_value("abc-123 material") == "ABC-123"


def test_normalize_human_text_decodes_double_encoded_mojibake():
    service = WebEnrichmentNormalizationService()
    raw = "Nenhum dado pÃƒÂ´de ser extraÃƒÂ­do da pÃƒÂ¡gina."
    normalized = service.normalize_human_text(raw)
    assert "pôde" in normalized
    assert "extraído" in normalized
    assert "página" in normalized
