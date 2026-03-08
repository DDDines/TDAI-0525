"""Tests for web enrichment content quality service."""

from __future__ import annotations

from types import SimpleNamespace

from Backend.application.services.web_enrichment_content_quality_service import (
    WebEnrichmentContentQualityService,
)


class _NormalizationStub:
    """Small normalization stub for quality service tests."""

    @staticmethod
    def fold_text(value):
        return " ".join(str(value or "").lower().split())

    @staticmethod
    def as_text(value):
        return " ".join(str(value or "").split())


class _TopLevelFunctionSurface:
    """Represent top level function surface and centralize responsibilities for this module."""

    def test_is_meaningful_extracted_text_covers_rejection_cases():
        """Reject empty, reference-like, low-quality and too-short content."""
        service = WebEnrichmentContentQualityService(normalization_service=_NormalizationStub())

        assert service.is_meaningful_extracted_text("") is False
        assert service.is_meaningful_extracted_text("Reference #ABC12345") is False
        assert service.is_meaningful_extracted_text("Access denied " * 20) is False
        assert service.is_meaningful_extracted_text("texto curto porem limpo") is False
        assert service.is_meaningful_extracted_text("11 22 33 " * 20) is False

    def test_is_meaningful_extracted_text_accepts_real_text():
        """Accept sufficiently rich product-oriented content."""
        service = WebEnrichmentContentQualityService(normalization_service=_NormalizationStub())
        text = (
            "Reservatorio de ar para sistema de freio pneumatico com corpo em aco carbono, "
            "solda reforcada, aplicacao em linha pesada, acabamento anticorrosivo e "
            "compatibilidade com instalacoes Volvo e Scania para manutencao profissional."
        )
        assert service.is_meaningful_extracted_text(text) is True

    def test_metadata_has_minimum_signal_covers_key_branches():
        """Validate metadata heuristics for empty, noisy, named and sku-based payloads."""
        service = WebEnrichmentContentQualityService(normalization_service=_NormalizationStub())

        assert service.metadata_has_minimum_signal({}) is False
        assert service.metadata_has_minimum_signal({"nome": "", "descricao_curta": ""}) is False
        assert service.metadata_has_minimum_signal({"nome": "access denied", "descricao_curta": "captcha"}) is False
        assert service.metadata_has_minimum_signal({"nome": "Reservatorio de Ar"}) is True
        assert service.metadata_has_minimum_signal({"sku": "SP1081", "marca": "Master"}) is True


test_is_meaningful_extracted_text_covers_rejection_cases = (
    _TopLevelFunctionSurface.test_is_meaningful_extracted_text_covers_rejection_cases
)
test_is_meaningful_extracted_text_accepts_real_text = (
    _TopLevelFunctionSurface.test_is_meaningful_extracted_text_accepts_real_text
)
test_metadata_has_minimum_signal_covers_key_branches = (
    _TopLevelFunctionSurface.test_metadata_has_minimum_signal_covers_key_branches
)
