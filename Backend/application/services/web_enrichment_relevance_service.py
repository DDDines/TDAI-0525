"""Module web enrichment relevance service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, List, Tuple
from urllib.parse import urlparse


class WebEnrichmentRelevanceService:
    """Class WebEnrichmentRelevanceService.

    Encapsulates one responsibility in the backend architecture.
    """
    _RELEVANCE_STOPWORDS = {
        "de",
        "da",
        "do",
        "das",
        "dos",
        "para",
        "com",
        "sem",
        "em",
        "ate",
        "todos",
        "todas",
        "lado",
        "peca",
        "pecas",
    }

    _URL_TRACKING_HINTS = (
        "ad_domain=",
        "ad_provider=",
        "click_metadata=",
        "msclkid=",
        "utm_",
        "vqd=",
    )
    _URL_HOST_LOW_SIGNAL = (
        "duckduckgo.com",
        "bing.com",
        "google.com",
        "facebook.com",
        "instagram.com",
        "linkedin.com",
        "youtube.com",
        "tiktok.com",
    )
    _URL_HOST_HIGH_SIGNAL = (
        "mercadolivre.",
        "amazon.",
        "shopee.",
        "magazineluiza.",
        "casasbahia.",
        "jocar.",
        "dipecarr.",
        "dana.",
        "jacto",
        "minner.",
        "mundodocaminhao.",
        "essentra",
    )

    @staticmethod
    def _fold_text(value: Any) -> str:
        """Execute _fold_text.

        This callable is documented to make behavior explicit for readers.
        """
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
        return re.sub(r"\s+", " ", text).strip()

    def tokens_for_relevance(self, value: Any) -> List[str]:
        """Execute tokens_for_relevance.

        This callable is documented to make behavior explicit for readers.
        """
        base = self._fold_text(value)
        if not base:
            return []
        return [t for t in base.split(" ") if len(t) >= 3 and t not in self._RELEVANCE_STOPWORDS]

    @staticmethod
    def extract_code_tokens(*values: Any) -> List[str]:
        """Execute extract_code_tokens.

        This callable is documented to make behavior explicit for readers.
        """
        combined = " ".join(str(v or "") for v in values)
        upper = (
            unicodedata.normalize("NFKD", combined)
            .encode("ascii", "ignore")
            .decode("ascii")
            .upper()
        )
        tokens = re.findall(r"[A-Z0-9][A-Z0-9./-]{3,}", upper)
        cleaned: List[str] = []
        for token in tokens:
            tok = token.strip("./-")
            if len(tok) < 4:
                continue
            if re.fullmatch(r"[A-Z]+", tok):
                continue
            cleaned.append(tok)
        return list(dict.fromkeys(cleaned))

    def is_source_relevant_for_product(
        self,
        db_produto_obj: Any,
        *,
        source_name: Any,
        source_desc: Any,
        source_url: str,
    ) -> bool:
        """Execute is_source_relevant_for_product.

        This callable is documented to make behavior explicit for readers.
        """
        ref_parts = [
            getattr(db_produto_obj, "nome_base", None),
            getattr(db_produto_obj, "marca", None),
            getattr(db_produto_obj, "sku", None),
            getattr(db_produto_obj, "ean", None),
        ]
        dados_brutos_web = getattr(db_produto_obj, "dados_brutos_web", None)
        if isinstance(dados_brutos_web, dict):
            ref_parts.append(dados_brutos_web.get("codigo_original"))
            ref_parts.append(dados_brutos_web.get("sku_original"))

        ref_tokens = self.tokens_for_relevance(" ".join(str(x or "") for x in ref_parts))
        if not ref_tokens:
            return True

        source_text = " ".join(str(x or "") for x in [source_name, source_desc, source_url])
        src_tokens = set(self.tokens_for_relevance(source_text))
        overlap = [t for t in ref_tokens if t in src_tokens]

        code_tokens = self.extract_code_tokens(*ref_parts)
        src_compact = re.sub(r"[^A-Z0-9]", "", str(source_text).upper())
        code_hit = any(re.sub(r"[^A-Z0-9]", "", token) in src_compact for token in code_tokens)

        if code_tokens and not code_hit and len(overlap) < 3:
            return False

        if len(ref_tokens) <= 4:
            return bool(overlap) or code_hit

        return len(overlap) >= 2 or code_hit

    @staticmethod
    def extract_supplier_domain(site_url: Any) -> str:
        """Execute extract_supplier_domain.

        This callable is documented to make behavior explicit for readers.
        """
        try:
            parsed = urlparse(str(site_url or "").strip())
            if parsed.netloc:
                return parsed.netloc.lower()
            raw = str(site_url or "").strip().lower()
            return raw.split("//")[-1].split("/")[0]
        except Exception:
            return ""

    def score_url_for_product(
        self,
        db_produto_obj: Any,
        candidate_url: str,
        fornecedor_domain: str = "",
    ) -> int:
        """Execute score_url_for_product.

        This callable is documented to make behavior explicit for readers.
        """
        parsed = urlparse(str(candidate_url or "").strip())
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        if not host:
            return -999

        score = 0
        if fornecedor_domain and fornecedor_domain in host:
            score += 45
        if any(h in host for h in self._URL_HOST_HIGH_SIGNAL):
            score += 18
        if any(h in host for h in self._URL_HOST_LOW_SIGNAL):
            score -= 20
        if path.endswith(".pdf"):
            score -= 10
        if path in {"/y.js", "/redirect", "/search"}:
            score -= 40
        if any(h in query for h in self._URL_TRACKING_HINTS):
            score -= 35
        if len(query) > 280:
            score -= 10

        ref_text = " ".join(
            str(x or "")
            for x in [
                getattr(db_produto_obj, "nome_base", None),
                getattr(db_produto_obj, "sku", None),
                getattr(db_produto_obj, "ean", None),
                getattr(db_produto_obj, "marca", None),
            ]
        )
        ref_tokens = set(self.tokens_for_relevance(ref_text))
        src_tokens = set(self.tokens_for_relevance(f"{host} {path} {query}"))
        overlap = len(ref_tokens.intersection(src_tokens))
        score += min(overlap * 6, 24)
        return score

    def prioritize_urls_for_enrichment(
        self,
        db_produto_obj: Any,
        urls_candidatas: List[str],
        fornecedor_domain: str = "",
        max_urls: int = 4,
    ) -> Tuple[List[str], List[Tuple[str, int]]]:
        """Execute prioritize_urls_for_enrichment.

        This callable is documented to make behavior explicit for readers.
        """
        deduped = [u for u in dict.fromkeys(urls_candidatas or []) if u]
        scored: List[Tuple[str, int]] = []
        for url in deduped:
            score = self.score_url_for_product(
                db_produto_obj,
                url,
                fornecedor_domain=fornecedor_domain,
            )
            if score <= -25:
                continue
            scored.append((url, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        return [url for url, _ in scored[: max(1, max_urls)]], scored
