from __future__ import annotations

import pytest

from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)


def test_web_enrichment_require_positive_int_rejects_non_numeric_values():
    with pytest.raises(ValueError, match="produto_id"):
        WebEnrichmentProcessingUseCase._require_positive_int("abc", "produto_id")

    with pytest.raises(ValueError, match="user_id"):
        WebEnrichmentProcessingUseCase._require_positive_int(None, "user_id")


def test_web_enrichment_normalize_search_terms_handles_none_blank_and_truncation():
    assert WebEnrichmentProcessingUseCase._normalize_search_terms(None) is None
    assert WebEnrichmentProcessingUseCase._normalize_search_terms("   ") is None

    long_text = "a" * 700
    normalized = WebEnrichmentProcessingUseCase._normalize_search_terms(long_text)
    assert len(normalized) == 500
    assert normalized == "a" * 500
