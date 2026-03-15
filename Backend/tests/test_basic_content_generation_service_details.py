"""Additional helper-level tests for basic non-AI content generation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)


class _MissingProductRepository:
    """Repository stub returning no product."""

    def __init__(self, _session):
        pass

    def get_produto(self, *, produto_id):
        _ = produto_id
        return None


def _service() -> BasicContentGenerationService:
    """Return a basic service instance with no repository dependency."""
    return BasicContentGenerationService(product_repository_factory=_MissingProductRepository)


def _produto(**overrides):
    """Build a compact product namespace for direct helper tests."""
    base = {
        "id": 99,
        "nome_base": "Paralama Dianteiro",
        "nome_chat_api": None,
        "marca": "MarcaBase",
        "modelo": "MD-1",
        "sku": "SKU-1",
        "ean": "7891234567890",
        "categoria_original": "Lataria",
        "categoria_mapeada": None,
        "fornecedor": None,
        "dynamic_attributes": {},
        "dados_brutos_web": {},
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_sanitize_title_fragment_handles_empty_cut_marker_and_numeric_noise():
    """Cover empty/default/contact-cut/numeric-heavy title sanitation branches."""
    cls = BasicContentGenerationService
    assert cls._sanitize_title_fragment("") == ""
    assert cls._sanitize_title_fragment("Filtro de Ar") == "Filtro de Ar"
    assert (
        cls._sanitize_title_fragment(
            "Fone Bluetooth JBL Tune 510BT Preto",
            cut_on_contact_marker=True,
        )
        == "Fone Bluetooth JBL Tune 510BT Preto"
    )
    assert cls._sanitize_title_fragment("AB1234CD5678EF") == ""
    assert (
        cls._sanitize_title_fragment(
            "Filtro de Ar Loja Exemplo", cut_on_contact_marker=True
        )
        == "Filtro de Ar"
    )
    assert cls._sanitize_title_fragment("123 456 789 012") == ""


def test_is_noisy_title_fragment_detects_url_email_contact_phone_and_clean_text():
    """Cover all noisy title detectors and the clean fallback."""
    cls = BasicContentGenerationService
    assert cls._is_noisy_title_fragment("") is True
    assert cls._is_noisy_title_fragment("https://example.com/produto") is True
    assert cls._is_noisy_title_fragment("contato@empresa.com") is True
    assert cls._is_noisy_title_fragment("Loja Oficial") is True
    assert cls._is_noisy_title_fragment("11 99888 7766") is True
    assert cls._is_noisy_title_fragment("Amortecedor Traseiro") is False


def test_is_weak_keyword_rejects_empty_noise_punctuation_stopwords_and_accepts_useful():
    """Cover weak keyword heuristics across early returns and a useful token."""
    cls = BasicContentGenerationService
    assert cls._is_weak_keyword("") is True
    assert cls._is_weak_keyword("https://example.com") is True
    assert cls._is_weak_keyword("!!!") is True
    assert cls._is_weak_keyword("produto") is True
    assert cls._is_weak_keyword("seguranca") is True
    assert cls._is_weak_keyword("suspensao pesada") is False


def test_extract_brand_hint_skips_short_digit_identity_stopword_and_weak_tokens():
    """Return the first strong manufacturer token after skipping weak candidates."""
    hint = BasicContentGenerationService._extract_brand_hint_from_generated_name(
        "ABC X123 Produto seguranca Bosch",
        identity_parts=["Paralama dianteiro", "Lataria"],
    )
    assert hint == "Bosch"


def test_resolve_generation_brand_prefers_hint_for_missing_brand_and_store_noise():
    """Cover the three main resolution outcomes for generation brand."""
    service = _service()
    produto_missing_brand = _produto(
        nome_base="Filtro de Ar",
        marca="",
        nome_chat_api="Filtro de Ar Bosch",
        dynamic_attributes={},
    )
    assert (
        service._resolve_generation_brand(
            produto=produto_missing_brand,
            web_context={"nome": ""},
        )
        == "Bosch"
    )

    produto_same_brand = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        nome_chat_api="Bosch",
        dynamic_attributes={},
    )
    assert (
        service._resolve_generation_brand(
            produto=produto_same_brand,
            web_context={"nome": ""},
        )
        == "Bosch"
    )

    produto_store_noise = _produto(
        nome_base="Filtro de Ar",
        marca="Loja Centro",
        nome_chat_api="Filtro de Ar Bosch",
        dynamic_attributes={"Titulo_Auto": "Filtro de Ar Bosch"},
    )
    assert (
        service._resolve_generation_brand(
            produto=produto_store_noise,
            web_context={"nome": "Filtro de Ar Bosch"},
        )
        == "Bosch"
    )


def test_resolve_generation_brand_preserves_existing_brand_when_hint_matches_or_candidate_contains_it(monkeypatch):
    """Cover the branches that keep the stored brand instead of swapping it."""
    service = _service()
    produto_same_brand = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        nome_chat_api="Bosch Premium",
        dynamic_attributes={},
    )
    monkeypatch.setattr(
        BasicContentGenerationService,
        "_extract_brand_hint_from_generated_name",
        classmethod(lambda cls, value, *, identity_parts: "Bosch"),
    )
    assert service._resolve_generation_brand(produto=produto_same_brand, web_context={}) == "Bosch"

    produto_brand_inside_candidate = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        nome_chat_api="Bosch Marelli",
        dynamic_attributes={},
    )
    monkeypatch.setattr(
        BasicContentGenerationService,
        "_extract_brand_hint_from_generated_name",
        classmethod(lambda cls, value, *, identity_parts: "Marelli"),
    )
    assert (
        service._resolve_generation_brand(
            produto=produto_brand_inside_candidate,
            web_context={},
        )
        == "Bosch"
    )


def test_sanitize_spec_pair_and_redundant_keyword_rules():
    """Cover blocked spec keys and redundant keyword decisions."""
    cls = BasicContentGenerationService
    assert cls._sanitize_spec_pair("titulo_auto", "Valor") is None
    assert cls._sanitize_spec_pair("Descricao", "This collection includes assorted ornaments.") is None
    assert cls._sanitize_spec_pair("Nome", "Lit Snowman Scene Glass Ornaments - 2 Assorted URL da fonte") is None
    assert cls._sanitize_spec_pair("Aplicacao", "seguranca") is None
    assert cls._sanitize_spec_pair("temperatura_cor", "6500K") == (
        "Temperatura Cor",
        "6500K",
    )
    assert cls._sanitize_spec_pair("Aplicacao", "Mercedes Benz") == (
        "Aplicacao",
        "Mercedes Benz",
    )

    identity = ["Reservatorio de Ar 20 Litros", "Rochepecas", "Freio a Ar"]
    assert cls._is_redundant_keyword("seguranca", identity_parts=identity) is True
    assert cls._is_redundant_keyword("!!!", identity_parts=identity) is True
    assert cls._is_redundant_keyword("ab.", identity_parts=identity) is True
    assert cls._is_redundant_keyword("reservatorio litros", identity_parts=identity) is True
    assert cls._is_redundant_keyword("mercedes benz", identity_parts=identity) is False


def test_primary_title_identity_filter_rejects_drifted_variants():
    cls = BasicContentGenerationService
    assert (
        cls._preserves_primary_title_identity(
            "Tela Central do Painel Superior Scania",
            primary_title="Tela Central do Painel Superior",
        )
        is True
    )
    assert (
        cls._preserves_primary_title_identity(
            "Vidro Porta 111 Scania",
            primary_title="Tela Central do Painel Superior",
        )
        is False
    )


def test_extract_technical_facts_prefers_direct_reference_value_over_label_text():
    service = _service()
    produto = _produto(
        nome_base="Reservatório de Ar 20 Litros",
        nome_chat_api="Reservatório de Ar 20 Litros - ROCHEPECAS",
        sku="987 308 430 7005",
        dados_brutos_web={
            "codigo_original": "308 430 70 05 (MERCEDES BENZ)",
            "especificacoes_tecnicas_dict": {
                "Referencia original/similar": "308 430 70 05 (MERCEDES BENZ)",
                "Aplicacao": "MERCEDES BENZ LN 608/708",
            },
        },
    )

    facts = service._extract_technical_facts(produto=produto, web_context={})

    assert facts["reference"] == "308 430 70 05 (MERCEDES BENZ)"
    assert facts["application"] == "MERCEDES BENZ LN 608/708"
    assert service._build_reference_title_fragment(facts["reference"]) == "Ref 3084307005"


def test_extract_technical_facts_prefers_model_code_over_internal_test_sku():
    service = _service()
    produto = _produto(
        nome_base="Bomba de combustivel Bosch 12V flex",
        modelo="0580454094",
        sku="LLM-SMOKE-PUMP-1773230084",
        descricao_original="Bomba de combustivel eletrica 12V com aplicacao em motores flex.",
        dynamic_attributes={"aplicacao": "motores flex"},
    )

    facts = service._extract_technical_facts(produto=produto, web_context={})

    assert facts["reference"] == "0580454094"
    assert service._build_reference_title_fragment(facts["reference"]) == "Ref 0580454094"


def test_extract_technical_facts_prefers_richer_direct_material_and_content_values():
    service = _service()
    produto = _produto(
        nome_base="Kit de Embreagem Luk",
        descricao_original="Kit de embreagem para linha leve com encaixe preciso.",
        dynamic_attributes={
            "material": "aco temperado",
            "conteudo da embalagem": "disco, plato e rolamento",
        },
        dados_brutos_web={
            "especificacoes_tecnicas_dict": {
                "Material": "Aco",
                "Conteudo": "disco",
            }
        },
    )

    facts = service._extract_technical_facts(produto=produto, web_context={})

    assert facts["material"] == "aco temperado"
    assert facts["content"] == "disco, plato e rolamento"


def test_detect_vehicle_make_uses_token_boundaries_and_prefers_specific_match():
    cls = BasicContentGenerationService

    assert cls._detect_vehicle_make("Kit cambio manual com acionamento leve") == ""
    assert cls._detect_vehicle_make("Filtro de ar Mann para linha leve") == ""
    assert cls._detect_vehicle_make("Reservatorio Mercedes-Benz Actros") == "Mercedes-Benz"
    assert cls._detect_vehicle_make("Aplicacao VW Constellation 24.250") == "VW"


def test_extract_technical_facts_does_not_infer_man_from_manual_or_mann():
    service = _service()
    produto = _produto(
        nome_base="Kit de Embreagem Luk cambio manual",
        descricao_original="Kit completo para cambio manual com disco, plato e rolamento.",
        modelo="620308400",
        dynamic_attributes={"conteudo": "kit com 3 pecas"},
        dados_brutos_web={
            "descricao_curta": "Aplicacao em cambio manual de linha leve com sistema Luk.",
            "especificacoes_tecnicas_dict": {"Material": "aco", "Marca complementar": "Mann"},
        },
    )

    facts = service._extract_technical_facts(produto=produto, web_context={})

    assert facts["vehicle_make"] == ""
    assert facts["material"] == "Aco"


def test_render_template_normalizes_none_dict_list_and_strips_blank_lines():
    """Exercise template rendering for all supported value types."""
    service = _service()
    rendered = service._render_template(
        template="A:{none}\n\nB:{mapping}\nC:{items}\nD:{text}",
        context={
            "none": None,
            "mapping": {" Material ": "  Aco  ", "": "ignorar", "Obs": ""},
            "items": ["  um  ", "", "dois"],
            "text": "  valor final  ",
        },
    )
    assert rendered == "A:\nB:Material: Aco\nC:um, dois\nD:valor final"


def test_coerce_list_and_dict_cover_scalar_and_blank_entries():
    """Cover scalar fallback and blank-entry skips for coercion helpers."""
    assert BasicContentGenerationService._coerce_list("valor unico") == ["valor unico"]
    assert BasicContentGenerationService._coerce_list(None) == []
    assert BasicContentGenerationService._coerce_list(["", "ok"]) == ["ok"]
    assert BasicContentGenerationService._coerce_dict({" A ": " 1 ", "": "2", "B": ""}) == {
        "A": "1"
    }


def test_extract_keywords_from_texts_skips_noise_and_keeps_compound_terms():
    """Cover keyword extraction skips and bigram generation."""
    service = _service()
    keywords = service._extract_keywords_from_texts(
        texts=[
            "http://example.com ab. 123 produto seguranca freio suspensao mercedes benz",
            "Freio suspensao linha pesada",
        ],
        limit=8,
    )
    assert "http" not in keywords
    assert "ab" not in keywords
    assert "seguranca" not in keywords
    assert "123" not in keywords
    assert "freio" in keywords
    assert "suspensao" in keywords
    assert "freio suspensao" in keywords


def test_extract_keywords_from_texts_can_skip_phrase_marked_weak(monkeypatch):
    """Cover the branch that rejects a bigram after token extraction."""
    service = _service()
    original = service._is_weak_keyword

    def _fake_is_weak(value):
        if value == "freio suspensao":
            return True
        return original(value)

    monkeypatch.setattr(service, "_is_weak_keyword", _fake_is_weak)
    keywords = service._extract_keywords_from_texts(
        texts=["freio suspensao mercedes benz"],
        limit=8,
    )
    assert "freio" in keywords
    assert "freio suspensao" not in keywords


def test_company_timeline_and_promotional_detectors_cover_false_and_true_paths():
    """Exercise timeline/promotional filters including neutral fallbacks."""
    cls = BasicContentGenerationService
    assert cls._looks_like_company_timeline_claim("") is False
    assert cls._looks_like_company_timeline_claim(
        "Empresa fundada em 2010 com tradicao no mercado."
    ) is True
    assert cls._looks_like_company_timeline_claim(
        "Desde 2010 produzimos pecas de reposicao."
    ) is False

    assert cls._looks_like_promotional_boilerplate("") is False
    assert cls._looks_like_promotional_boilerplate("www.exemplo.com/catalogo") is True
    assert cls._looks_like_promotional_boilerplate("11 99888 7766") is True
    assert (
        cls._looks_like_promotional_boilerplate(
            "Parcelamento em ate 10x sem juros para sua compra."
        )
        is True
    )
    assert cls._looks_like_promotional_boilerplate("Paralama em chapa reforcada.") is False


def test_sanitize_description_context_drops_empty_timeline_and_promotional_chunks():
    """Return only useful description fragments after filtering unsupported chunks."""
    cls = BasicContentGenerationService
    sanitized = cls._sanitize_description_context(
        "Destaques: . ; Empresa fundada em 2010 no mercado. "
        "Paralama reforcado para linha pesada. "
        "Entre em contato pelo telefone 11 99888 7766."
    )
    assert sanitized == "Paralama reforcado para linha pesada."
    assert cls._sanitize_description_context("Destaques: ; ; !!!") == ""


def test_extract_web_context_handles_non_dict_sources_and_keyword_fallback_deduplication():
    """Cover default context, source-description fallback and keyword deduplication."""
    service = _service()
    assert service._extract_web_context(produto=_produto(dados_brutos_web=[])) == {
        "nome": "",
        "descricao": "",
        "bullets": [],
        "keywords": [],
        "specs": {},
    }

    produto = _produto(
        dados_brutos_web={
            "nome": "Reservatorio de Ar Loja Exemplo",
            "descricao_curta": "",
            "lista_caracteristicas_beneficios_bullets": [
                "Aplicacao em freios",
                "Parcelamento em ate 10x",
            ],
            "fontes_web_coletadas": [
                {"descricao_curta": "Empresa fundada em 2010."},
                {"descricao_curta": "Reservatorio para freios e suspensao."},
                "ignorar",
            ],
            "palavras_chave_seo_relevantes_lista": ["seguranca", "freios"],
            "especificacoes_tecnicas_dict": {
                "titulo_auto": "interno",
                "Aplicacao": "Mercedes Benz",
            },
        }
    )

    context = service._extract_web_context(produto=produto)
    assert context["nome"] == "Reservatorio de Ar"
    assert context["descricao"] == "Reservatorio para freios e suspensao."
    assert context["bullets"] == ["Aplicacao em freios"]
    assert context["specs"] == {"Aplicacao": "Mercedes Benz"}
    assert "seguranca" not in context["keywords"]
    assert len(context["keywords"]) >= 2
    assert len({item.lower() for item in context["keywords"]}) == len(context["keywords"])


def test_extract_web_context_skips_duplicate_and_weak_fallback_keywords(monkeypatch):
    """Cover duplicate and weak fallback filtering during web-context completion."""
    service = _service()
    produto = _produto(
        dados_brutos_web={
            "nome": "Filtro de Ar",
            "descricao_curta": "Descricao limpa",
            "palavras_chave_seo_relevantes_lista": ["freios"],
        }
    )

    def _fake_extract_keywords_from_texts(*, texts, limit=8):
        _ = texts, limit
        return ["freios", "seguranca", "suspensao"]

    monkeypatch.setattr(service, "_extract_keywords_from_texts", _fake_extract_keywords_from_texts)
    context = service._extract_web_context(produto=produto)
    assert context["keywords"] == ["freios", "suspensao"]


def test_ensure_minimum_title_candidates_adds_option_fallbacks():
    """Cover fallback option generation when deterministic candidates are insufficient."""
    service = _service()
    produto = _produto(
        nome_base="Produto Especial",
        marca="",
        modelo="",
        sku="",
        categoria_original="",
    )
    candidates = service._ensure_minimum_title_candidates(
        candidates=[],
        produto=produto,
        minimum_count=3,
        web_context={"nome": "", "keywords": []},
    )
    assert len(candidates) == 3
    assert candidates[-1].endswith("variante 3")


def test_load_produto_raises_404_when_repository_returns_none():
    """Exercise the explicit not-found branch."""
    service = _service()
    with pytest.raises(Exception) as exc_info:
        service._load_produto(session=object(), produto_id=123)
    assert getattr(exc_info.value, "status_code", None) == 404


def test_build_title_candidates_uses_explicit_fallback_when_internal_builder_returns_empty(monkeypatch):
    """Cover the final hard fallback branch of title candidate generation."""
    service = _service()
    monkeypatch.setattr(
        service,
        "_ensure_minimum_title_candidates",
        lambda **kwargs: [],
    )
    produto = _produto(nome_base="", id=777)
    candidates = service._build_title_candidates(produto=produto, web_context={})
    assert candidates == ["Produto 777"]


def test_build_title_candidates_skips_invalid_spec_pairs():
    """Cover the continue branch when a web spec is rejected by sanitization."""
    service = _service()
    produto = _produto(
        nome_base="Filtro de Ar",
        dados_brutos_web={
            "especificacoes_tecnicas_dict": {
                "Contato": "11 99888 7766",
                "Aplicacao": "Mercedes Benz",
            }
        },
    )
    candidates = service._build_title_candidates(
        produto=produto,
        web_context=service._extract_web_context(produto=produto),
    )
    assert not any("99888" in candidate for candidate in candidates)
    assert any("Filtro de Ar" in candidate for candidate in candidates)


def test_build_title_candidates_and_description_skip_invalid_specs_only():
    """Cover continue branches when every spec candidate is sanitized out."""
    service = _service()
    produto = _produto(
        nome_base="Filtro de Ar",
        dados_brutos_web={
            "especificacoes_tecnicas_dict": {
                "Contato": "11 99888 7766",
                "Politica": "Sem juros",
            }
        },
    )
    web_context = service._extract_web_context(produto=produto)
    candidates = service._build_title_candidates(produto=produto, web_context=web_context)
    assert candidates
    assert not any("99888" in candidate or "Sem juros" in candidate for candidate in candidates)

    descricao = service._build_basic_description(
        produto=produto,
        tamanho_palavras=100,
        template_descricao="{specs}",
    )
    assert "99888" not in descricao
    assert "Sem juros" not in descricao


def test_build_title_candidates_and_description_cover_continue_when_spec_pair_is_none(monkeypatch):
    """Force the explicit continue branches for rejected spec pairs."""
    service = _service()
    produto = _produto(
        nome_base="Filtro de Ar",
        dados_brutos_web={"especificacoes_tecnicas_dict": {"Cor": "Azul"}},
    )
    monkeypatch.setattr(BasicContentGenerationService, "_sanitize_spec_pair", classmethod(lambda cls, key, value: None))
    candidates = service._build_title_candidates(
        produto=produto,
        web_context=service._extract_web_context(produto=produto),
    )
    assert candidates
    descricao = service._build_basic_description(
        produto=produto,
        tamanho_palavras=100,
        template_descricao="{specs}",
    )
    assert "Azul" not in descricao


def test_build_titles_with_template_skips_noisy_render_and_build_description_fallback_and_truncation():
    """Cover noisy rendered titles, intro fallback, web-spec skip and truncation."""
    service = _service()
    produto = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        modelo="",
        sku="SKU-9",
        ean="",
        categoria_original="",
        dynamic_attributes={"Aplicacao": "Mercedes Benz", "Contato": "11 99888 7766"},
    )

    titles = service._build_titles_with_template(
        produto=produto,
        template_titulo="Loja Exemplo {indice}",
        web_context={"nome": "", "descricao": "", "keywords": [], "specs": {}},
        base_candidates=["Filtro de Ar"],
        max_titles=2,
    )
    assert titles == []

    monkeypatch_context = {
        "nome": "",
        "descricao": "",
        "bullets": [],
        "keywords": [],
        "specs": {"Contato": "11 99888 7766"},
    }
    produto_min = _produto(
        nome_base="Filtro de Ar",
        marca="",
        modelo="",
        sku="",
        ean="",
        categoria_original="",
        dynamic_attributes="invalid",
        dados_brutos_web=monkeypatch_context,
    )
    assert (
        service._build_basic_description(
            produto=produto_min,
            tamanho_palavras=20,
            template_descricao="{desconhecido}",
        )
        == "Filtro de Ar."
    )

    produto_long = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        modelo="X1",
        sku="SKU-9",
        ean="123",
        categoria_original="Motor",
        dynamic_attributes={"Aplicacao": "Mercedes Benz", "Material": "Papel"},
        dados_brutos_web={
            "descricao_curta": " ".join(f"palavra{i}" for i in range(60)),
            "palavras_chave_seo_relevantes_lista": ["mercedes benz", "motor diesel"],
            "especificacoes_tecnicas_dict": {"Contato": "11 99888 7766", "Cor": "Azul"},
        },
    )
    truncated = service._build_basic_description(
        produto=produto_long,
        tamanho_palavras=10,
        template_descricao=service._DEFAULT_DESCRIPTION_TEMPLATE,
    )
    assert not truncated.endswith("...")
    assert len(truncated.split()) == 60


def test_build_basic_description_uses_generic_object_summary_hints_for_retail_object_names():
    service = _service()
    produto = _produto(
        nome_base="Tier Displayer",
        marca="",
        modelo="",
        sku="",
        ean="",
        categoria_original="",
        dynamic_attributes={},
        dados_brutos_web={},
    )

    descricao = service._build_basic_description(
        produto=produto,
        tamanho_palavras=120,
        template_descricao=service._DEFAULT_DESCRIPTION_TEMPLATE,
    )

    assert "Resumo tecnico:\nExpositor em camadas para organizacao e apresentacao visual de itens." in descricao
    assert "Resumo tecnico:\nTier Displayer." not in descricao


def test_build_basic_description_limits_dynamic_specs_and_skips_invalid_web_specs():
    """Cover dynamic spec loop break and invalid web-spec skip branches."""
    service = _service()
    dynamic_attributes = {f"Attr{i}": f"Valor{i}" for i in range(20)}
    dynamic_attributes["Contato"] = "11 99888 7766"
    produto = _produto(
        nome_base="Filtro de Ar",
        marca="Bosch",
        modelo="",
        sku="SKU-9",
        ean="789",
        categoria_original="Motor",
        dynamic_attributes=dynamic_attributes,
        dados_brutos_web={
            "descricao_curta": "Descricao limpa",
            "especificacoes_tecnicas_dict": {"Contato": "11 99888 7766", "Cor": "Azul"},
        },
    )
    descricao = service._build_basic_description(
        produto=produto,
        tamanho_palavras=200,
        template_descricao="{specs}",
    )
    assert "Attr9: Valor9" in descricao
    assert "Attr10: Valor10" not in descricao
    assert "99888" not in descricao
    assert "Cor: Azul" not in descricao


def test_build_title_candidates_and_description_skip_invalid_spec_pairs_from_forced_web_context(monkeypatch):
    """Inject invalid web specs directly because the extractor sanitizes them before these loops run."""
    service = _service()
    produto = _produto(
        nome_base="Filtro de Ar",
        dynamic_attributes={"Material": "Papel", "Contato": "11 99888 7766"},
    )
    forced_context = {
        "nome": "Filtro de Ar",
        "descricao": "Descricao limpa",
        "bullets": [],
        "keywords": [],
        "specs": {"Contato": "11 99888 7766", "Cor": "Azul"},
    }

    candidates = service._build_title_candidates(
        produto=produto,
        web_context=forced_context,
    )
    monkeypatch.setattr(service, "_extract_web_context", lambda *, produto: forced_context)
    descricao = service._build_basic_description(
        produto=produto,
        tamanho_palavras=100,
        template_descricao="{specs}",
    )

    assert candidates
    assert all("99888" not in item for item in candidates)
    assert "Material: Papel" in descricao
    assert "Cor: Azul" not in descricao
    assert "Contato" not in descricao
