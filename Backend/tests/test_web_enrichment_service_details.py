"""Additional detail tests for web enrichment helper services."""

from __future__ import annotations

from types import SimpleNamespace

from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)


def test_normalization_service_covers_marker_helpers_and_text_accessors():
    """Exercise helper branches across normalization primitives."""
    service = WebEnrichmentNormalizationService()
    assert service._encoding_marker_count("") == 0
    assert service._has_markers("texto??") is True
    assert service._has_markers("texto limpo") is False
    assert service.normalize_human_text("") == ""
    assert service.normalize_human_text("texto limpo") == "texto limpo"
    assert service.normalize_human_text("texto??") == "texto??"
    assert service.fold_text("Fixação Çã") == "fixacao ca"

    assert service.is_empty(None) is True
    assert service.is_empty("  ") is True
    assert service.is_empty("N/A") is True
    assert service.is_empty([]) is True
    assert service.is_empty({"a": 1}) is False
    assert service.is_empty(1) is False

    assert service.as_text([" A ", "", "B "]) == "A | B"
    assert service.as_text("x" * 20, max_len=5) == "xxxxx"
    assert service.as_text([], max_len=5) is None
    assert service.as_text([None, " "], max_len=5) is None
    assert service.first_non_empty([None, " ", "valor", "outro"]) == "valor"
    assert service.first_non_empty([None, "", []]) is None


def test_normalization_service_covers_price_code_signal_and_placeholder_logic():
    """Cover remaining normalization helper branches with deterministic assertions."""
    service = WebEnrichmentNormalizationService()
    assert service.parse_price(None) is None
    assert service.parse_price(10) == 10.0
    assert service.parse_price("12.50") == 12.5
    assert service.parse_price("") is None
    assert service.parse_price("1,234.56") == 1234.56
    assert service.parse_price("abc") is None

    assert service.sanitize_code_value(None) is None
    assert service.sanitize_code_value(" /abc-123./ ") == "ABC-123"
    assert service.is_suspicious_code(None) is False
    assert service.is_suspicious_code("ABC123MATERIAL") is True
    assert service.is_suspicious_code("ABC123") is False

    signals = service.extract_signals_from_description(
        "Codigo original: ab-123. Material: aco galvanizado. Peso: 10kg."
    )
    assert signals["codigo_original"] == "AB-123"
    assert signals["material"] == "aco galvanizado"
    assert service.extract_signals_from_description("Material: ;") == {}
    assert service.extract_signals_from_description("Descricao sem codigo") == {}
    assert service.extract_signals_from_description(None) == {}

    assert service.is_placeholder_value(None) is True
    assert service.is_placeholder_value("todos") is True
    assert service.is_placeholder_value("Reservatorio de Ar") is False


def test_relevance_service_covers_token_code_and_supplier_domain_edges():
    """Cover empty/short token branches and supplier-domain extraction fallbacks."""
    service = WebEnrichmentRelevanceService()
    assert service.tokens_for_relevance(None) == []
    assert service.tokens_for_relevance("de do em aa bb") == []
    assert WebEnrichmentRelevanceService.extract_code_tokens(
        ["ABCD", "AAAA", "AB-12", "ZXCV1234", "A1", "A---"]
    ) == ["AB-12", "ZXCV1234"]
    assert service.extract_supplier_domain("https://site.exemplo.com/path") == "site.exemplo.com"
    assert service.extract_supplier_domain("www.exemplo.com/produto") == "www.exemplo.com"

    class _BrokenStr:
        def __str__(self):
            raise ValueError("boom")

    assert service.extract_supplier_domain(_BrokenStr()) == ""


def test_relevance_service_covers_relevance_scoring_and_prioritization_branches():
    """Exercise the remaining relevance branches with compact fixtures."""
    service = WebEnrichmentRelevanceService()

    produto_sem_refs = SimpleNamespace(nome_base="", marca="", sku="", ean="", dados_brutos_web={})
    assert (
        service.is_source_relevant_for_product(
            produto_sem_refs,
            source_name="qualquer",
            source_desc="texto",
            source_url="https://example.com",
        )
        is True
    )

    produto_curto = SimpleNamespace(
        nome_base="Paralama",
        marca="Randon",
        sku="AB-1234",
        ean=None,
        dados_brutos_web=None,
    )
    assert (
        service.is_source_relevant_for_product(
            produto_curto,
            source_name="Paralama Randon",
            source_desc="Aplicacao AB-1234",
            source_url="https://example.com/paralama",
        )
        is True
    )

    produto_longo = SimpleNamespace(
        nome_base="Reservatorio de Ar Caminhao Pesado",
        marca="Randon",
        sku="ZX-9999",
        ean="7890001112223",
        dados_brutos_web={"codigo_original": "ORIG-55"},
    )
    assert (
        service.is_source_relevant_for_product(
            produto_longo,
            source_name="Reservatorio ar pesado",
            source_desc="Randon ORIG-55 para freio",
            source_url="https://supplier.com/reservatorio",
        )
        is True
    )

    assert service.score_url_for_product(produto_curto, "sem-host") == -999
    high_score = service.score_url_for_product(
        produto_curto,
        "https://catalogo.randon.com.br/produto/paralama-randon-ab-1234",
        fornecedor_domain="randon.com.br",
    )
    low_score = service.score_url_for_product(
        produto_curto,
        "https://duckduckgo.com/manual.pdf?q=abc&utm_source=x&" + ("a" * 300),
        fornecedor_domain="randon.com.br",
    )
    assert high_score > low_score

    urls, scored = service.prioritize_urls_for_enrichment(
        produto_curto,
        [
            "https://www.jocar.com.br/produto/paralama-randon-ab-1234",
            "https://www.jocar.com.br/produto/paralama-randon-ab-1234",
            "https://duckduckgo.com/search?q=abc&utm_source=x",
        ],
        fornecedor_domain="randon.com.br",
        max_urls=1,
    )
    assert urls == ["https://www.jocar.com.br/produto/paralama-randon-ab-1234"]
    assert scored[0][0] == urls[0]
