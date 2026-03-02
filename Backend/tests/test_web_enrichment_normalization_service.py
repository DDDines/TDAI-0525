"""Module test web enrichment normalization service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_parse_price_handles_brazilian_format():
        """Execute test_parse_price_handles_brazilian_format.

        This callable is documented to make behavior explicit for readers.
        """
        service = WebEnrichmentNormalizationService()
        assert service.parse_price("R$ 1.234,56") == 1234.56

    def test_sanitize_code_value_removes_noise_suffix():
        """Execute test_sanitize_code_value_removes_noise_suffix.

        This callable is documented to make behavior explicit for readers.
        """
        service = WebEnrichmentNormalizationService()
        assert service.sanitize_code_value("abc-123 material") == "ABC-123"

    def test_normalize_human_text_decodes_double_encoded_mojibake():
        """Execute test_normalize_human_text_decodes_double_encoded_mojibake.

        This callable is documented to make behavior explicit for readers.
        """
        service = WebEnrichmentNormalizationService()
        raw = "Nenhum dado pÃƒÂ´de ser extraÃƒÂ­do da pÃƒÂ¡gina."
        normalized = service.normalize_human_text(raw)
        assert "pôde" in normalized
        assert "extraído" in normalized
        assert "página" in normalized

test_parse_price_handles_brazilian_format = _TopLevelFunctionSurface.test_parse_price_handles_brazilian_format
test_sanitize_code_value_removes_noise_suffix = _TopLevelFunctionSurface.test_sanitize_code_value_removes_noise_suffix
test_normalize_human_text_decodes_double_encoded_mojibake = _TopLevelFunctionSurface.test_normalize_human_text_decodes_double_encoded_mojibake




