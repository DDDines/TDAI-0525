"""Module test web enrichment relevance service.

Contains backend logic related to test web enrichment relevance service and documents its role in the OOP architecture.
"""

from types import SimpleNamespace

from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_tokens_for_relevance_normalizes_and_removes_stopwords():
        """Run test tokens for relevance normalizes and removes stopwords in this workflow."""
        service = WebEnrichmentRelevanceService()
    
        tokens = service.tokens_for_relevance("Suporte de Fixacao do Apara Barro em metal")
    
        assert "suporte" in tokens
        assert "fixacao" in tokens
        assert "apara" in tokens
        assert "barro" in tokens
        assert "metal" in tokens
        assert "de" not in tokens
        assert "do" not in tokens
        assert "em" not in tokens

    def test_extract_code_tokens_returns_structured_codes():
        """Run test extract code tokens returns structured codes in this workflow."""
        tokens = WebEnrichmentRelevanceService.extract_code_tokens(
            [
                "SKU TJG809201A",
                "codigo 2C456840300BB",
                "texto generico",
            ]
        )
    
        assert "TJG809201A" in tokens
        assert "2C456840300BB" in tokens

    def test_is_source_relevant_for_product_rejects_unrelated_source():
        """Run test is source relevant for product rejects unrelated source in this workflow."""
        service = WebEnrichmentRelevanceService()
        produto = SimpleNamespace(
            nome_base="Parede Traseira Fechada",
            marca=None,
            sku="3192 2C456840300BB",
            ean=None,
            dados_brutos_web={},
        )
    
        is_relevant = service.is_source_relevant_for_product(
            produto,
            source_name="Estribo Menor Cromado Scania",
            source_desc="Peca de acabamento para estribo",
            source_url="https://example.com/estribo",
        )
    
        assert is_relevant is False

    def test_score_url_for_product_prefers_supplier_and_marketplace_domains():
        """Run test score url for product prefers supplier and marketplace domains in this workflow."""
        service = WebEnrichmentRelevanceService()
        produto = SimpleNamespace(
            nome_base="Suporte Fixacao Apara Barro",
            sku="SP1081",
            ean=None,
            marca="Amalcaburio",
        )
    
        strong_score = service.score_url_for_product(
            produto,
            "https://www.jocar.com.br/produto/suporte-fixacao-sp1081",
            fornecedor_domain="amalcaburio.com.br",
        )
        weak_score = service.score_url_for_product(
            produto,
            "https://duckduckgo.com/y.js?ad_domain=test&utm_source=x",
            fornecedor_domain="amalcaburio.com.br",
        )
    
        assert strong_score > weak_score

    def test_prioritize_urls_for_enrichment_orders_best_first_and_filters_low_quality():
        """Run test prioritize urls for enrichment orders best first and filters low quality in this workflow."""
        service = WebEnrichmentRelevanceService()
        produto = SimpleNamespace(
            nome_base="Suporte Fixacao Apara Barro",
            sku="SP1081",
            ean=None,
            marca="Amalcaburio",
        )
    
        urls, scored = service.prioritize_urls_for_enrichment(
            produto,
            [
                "https://duckduckgo.com/y.js?ad_domain=test&utm_source=x",
                "https://www.jocar.com.br/produto/suporte-fixacao-sp1081",
                "https://www.mercadolivre.com.br/p/suporte-fixacao-sp1081",
            ],
            fornecedor_domain="amalcaburio.com.br",
            max_urls=2,
        )
    
        assert len(urls) == 2
        assert urls[0].startswith("https://www.jocar.com.br/")
        assert all(item[1] > -25 for item in scored)

test_tokens_for_relevance_normalizes_and_removes_stopwords = _TopLevelFunctionSurface.test_tokens_for_relevance_normalizes_and_removes_stopwords
test_extract_code_tokens_returns_structured_codes = _TopLevelFunctionSurface.test_extract_code_tokens_returns_structured_codes
test_is_source_relevant_for_product_rejects_unrelated_source = _TopLevelFunctionSurface.test_is_source_relevant_for_product_rejects_unrelated_source
test_score_url_for_product_prefers_supplier_and_marketplace_domains = _TopLevelFunctionSurface.test_score_url_for_product_prefers_supplier_and_marketplace_domains
test_prioritize_urls_for_enrichment_orders_best_first_and_filters_low_quality = _TopLevelFunctionSurface.test_prioritize_urls_for_enrichment_orders_best_first_and_filters_low_quality








