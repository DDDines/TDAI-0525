"""Web enrichment content quality service.

"""

from __future__ import annotations

from typing import Any, Dict
import re


class WebEnrichmentContentQualityService:
    """Heuristicas de qualidade para texto e metadados coletados na web."""

    _LOW_QUALITY_CONTENT_MARKERS = (
        "errors edgesuite net",
        "access denied",
        "attention required",
        "captcha",
        "temporarily unavailable",
        "service unavailable",
        "bad request",
    )

    def __init__(self, *, normalization_service: Any) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Content Quality Service."""
        self._normalization = normalization_service

    def is_meaningful_extracted_text(self, value: Any) -> bool:
        """Execute is meaningful extracted text as part of this module workflow."""
        text = self._normalization.fold_text(value)
        if not text:
            return False
        if re.search(r"\breference\s*#?\s*[0-9a-z.]{6,}\b", text):
            return False
        if any(marker in text for marker in self._LOW_QUALITY_CONTENT_MARKERS):
            return False
        if len(text) < 80:
            return False
        words = [word for word in text.split() if len(word) >= 3]
        if len(words) < 12:
            return False
        letters = sum(1 for char in text if char.isalpha())
        return letters >= 50

    def metadata_has_minimum_signal(self, metadata: Dict[str, Any]) -> bool:
        """Execute metadata has minimum signal as part of this module workflow."""
        if not metadata:
            return False
        nome = self._normalization.as_text(metadata.get("nome"))
        descricao = self._normalization.as_text(metadata.get("descricao_curta"))
        sku = self._normalization.as_text(metadata.get("sku"))
        marca = self._normalization.as_text(metadata.get("marca"))
        image = self._normalization.as_text(metadata.get("imagem_url"))
        if not any([nome, descricao, sku, marca, image]):
            return False
        joined = " ".join(part for part in [nome, descricao] if part)
        if joined and any(
            marker in self._normalization.fold_text(joined)
            for marker in self._LOW_QUALITY_CONTENT_MARKERS
        ):
            return False
        if nome and len(nome) >= 8:
            return True
        return bool(sku and (descricao or marca or image))
