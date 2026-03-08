"""Module test web enrichment normalization service.

Contains backend logic related to test web enrichment normalization service and documents its role in the OOP architecture.
"""

import pytest

from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""

    def test_parse_price_handles_brazilian_format():
        """Run test parse price handles brazilian format in this workflow."""
        service = WebEnrichmentNormalizationService()
        assert service.parse_price("R$ 1.234,56") == 1234.56

    def test_sanitize_code_value_removes_noise_suffix():
        """Run test sanitize code value removes noise suffix in this workflow."""
        service = WebEnrichmentNormalizationService()
        assert service.sanitize_code_value("abc-123 material") == "ABC-123"

    def test_normalize_human_text_decodes_double_encoded_mojibake():
        """Run test normalize human text decodes double encoded mojibake in this workflow."""
        service = WebEnrichmentNormalizationService()
        raw = "Nenhum dado pÃƒÆ’Ã‚Â´de ser extraÃƒÆ’Ã‚Â­do da pÃƒÆ’Ã‚Â¡gina."
        normalized = service.normalize_human_text(raw)
        assert "pôde" in normalized
        assert "extraído" in normalized
        assert "página" in normalized

    def test_normalize_human_text_can_exhaust_marker_loop(monkeypatch):
        """Force the decode loop to stop only after all six iterations."""
        service = WebEnrichmentNormalizationService()

        monkeypatch.setattr(service, "_has_markers", lambda text: True)
        monkeypatch.setattr(
            service,
            "_encoding_marker_count",
            lambda text: max(0, 20 - len(text)),
        )
        monkeypatch.setattr(
            service,
            "_decode_maybe",
            lambda text, source_encoding: f"{text}x",
        )

        normalized = service.normalize_human_text("a")

        assert normalized == "axxxxxx"


test_parse_price_handles_brazilian_format = _TopLevelFunctionSurface.test_parse_price_handles_brazilian_format
test_sanitize_code_value_removes_noise_suffix = _TopLevelFunctionSurface.test_sanitize_code_value_removes_noise_suffix
test_normalize_human_text_decodes_double_encoded_mojibake = _TopLevelFunctionSurface.test_normalize_human_text_decodes_double_encoded_mojibake
test_normalize_human_text_can_exhaust_marker_loop = _TopLevelFunctionSurface.test_normalize_human_text_can_exhaust_marker_loop
