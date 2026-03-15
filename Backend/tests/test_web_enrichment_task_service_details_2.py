from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import pytest

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskWorkflow,
)


class _FakeStatus(Enum):
    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    FALHA_API_EXTERNA = "FALHA_API_EXTERNA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"
    FALHOU = "FALHOU"


class _FakeTipoAcaoEnum(Enum):
    ENRIQUECIMENTO_WEB_PRODUTO = "enriquecimento_web_produto"


class _FakeModels:
    StatusEnriquecimentoEnum = _FakeStatus
    TipoAcaoEnum = _FakeTipoAcaoEnum


class _FakeRegistroUsoIACreate:
    def __init__(self, **kwargs):
        self.payload = kwargs


class _FakeSchemas:
    RegistroUsoIACreate = _FakeRegistroUsoIACreate
    ProdutoUpdate = lambda **kwargs: kwargs


def _build_workflow():
    return WebEnrichmentTaskWorkflow(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        SQLAlchemyError=Exception,
        session_provider=SimpleNamespace(open_session=lambda: object()),
        user_repository_factory=lambda _session: SimpleNamespace(),
        product_repository_factory=lambda _session: SimpleNamespace(),
        usage_repository_factory=lambda _session: SimpleNamespace(
            create_registro_uso_ia=lambda **kwargs: kwargs
        ),
        models=_FakeModels,
        schemas=_FakeSchemas,
        web_extractor=SimpleNamespace(
            extrair_dados_produto_com_llm=lambda **kwargs: None,
        ),
        settings=SimpleNamespace(),
        json=SimpleNamespace(dumps=lambda *args, **kwargs: "{}"),
        normalize_human_text=lambda value: value,
        build_payload_enriquecimento_visivel=lambda **kwargs: ({}, [], []),
        extrair_dominio_fornecedor=lambda value: value,
        priorizar_urls_para_enriquecimento=lambda **kwargs: ([], []),
        is_meaningful_extracted_text=lambda text: bool(text),
        metadata_has_minimum_signal=lambda metadata: bool(metadata),
        is_source_relevant_for_product=lambda *args, **kwargs: True,
    )


def test_timeline_helpers_cover_empty_pattern_and_all_filtered_cases():
    workflow = _build_workflow()

    assert workflow._looks_like_company_timeline_claim("") is False
    assert workflow._looks_like_company_timeline_claim("desde 2012.") is False
    assert workflow._looks_like_company_timeline_claim("A empresa foi fundada em 2012.") is True
    assert workflow._sanitize_company_timeline_text("x\nA empresa foi fundada em 2012.") == "x A empresa foi fundada em 2012."
    assert workflow._sanitize_company_timeline_text(None) == ""


def test_low_level_helpers_cover_empty_payload_specs_keywords_and_session_close():
    workflow = _build_workflow()

    workflow._sanitize_aggregated_payload("nao-dict")
    workflow._sanitize_aggregated_payload(
        {
            "fontes_web_coletadas": ["ignorar", {"url": "u", "descricao_curta": "Produto valido"}],
            "lista_caracteristicas_beneficios_bullets": ["A empresa foi fundada em 2012.", "Aplicacao real"],
        }
    )
    assert workflow._extract_specs_from_text(text="http: foo; sku: 1; link: //site; Material: Aco; Material: Aluminio", limit=1) == {
        "material": "Aco"
    }
    keywords = workflow._extract_keywords(
        source_texts=["a aa com http 12 123 ford 1234 http://site"],
        limit=5,
    )
    assert "com" not in keywords
    assert "http" not in keywords
    assert "12" not in keywords
    assert "ford" in keywords
    assert workflow._has_meaningful_llm_value(7) is True
    assert workflow._has_meaningful_llm_value([]) is False

    class _BadSession:
        def close(self):
            raise RuntimeError("close")

    workflow._close_session_quietly(_BadSession())
    workflow._close_session_quietly(None)


def test_heuristic_enrichment_covers_early_return_and_fallback_name():
    workflow = _build_workflow()
    produto = SimpleNamespace(
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-1",
        modelo="M1",
        ean="12345678",
        categoria_mapeada="Freios",
        categoria_original="Freios",
    )
    logs = []
    payload = {}

    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=payload,
        log_mensagens=logs,
    )
    assert payload == {
        "descricao_curta": "",
        "descricao_detalhada_seo": "",
        "texto_relevante_coletado": "",
    }

    payload = {"descricao_curta": "", "texto_relevante_coletado": "Material: Aco carbono. Aplicacao: Volvo."}
    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=payload,
        log_mensagens=logs,
    )

    assert payload["nome"] == "Reservatorio MarcaX SKU-1"
    assert payload["descricao_curta"]
    assert payload["descricao_detalhada_seo"]
    assert payload["palavras_chave_seo_relevantes_lista"]


def test_sentence_and_spec_helpers_cover_timeline_skip_and_empty_text():
    workflow = _build_workflow()

    assert workflow._extract_specs_from_text(text="") == {}
    assert workflow._split_sentences(
        text="Desde 2012 no mercado. Frase tecnica util e longa o suficiente.",
        max_items=3,
        min_len=20,
    ) == ["Frase tecnica util e longa o suficiente"]


@pytest.mark.asyncio
async def test_busca_e_llm_cover_no_results_and_error_payload_paths():
    workflow = _build_workflow()
    logs = []

    async def _buscar_urls_google(**kwargs):
        return []

    async def _buscar_urls_publicas(**kwargs):
        return []

    async def _extrair_dados_produto_com_llm(**kwargs):
        return {"erro_llm": "timeout"}

    workflow.web_extractor = SimpleNamespace(
        buscar_urls_google=_buscar_urls_google,
        buscar_urls_publicas=_buscar_urls_publicas,
        extrair_dados_produto_com_llm=_extrair_dados_produto_com_llm,
    )

    urls = await workflow._buscar_urls(
        query_candidates=["a", "b"],
        busca_web_disponivel=True,
        google_api_key=None,
        google_search_engine_id=None,
        log_mensagens=logs,
    )
    assert urls == []
    assert "Nenhuma URL encontrada" in logs[-1]

    collected, status = await workflow._executar_llm(
        openai_api_configurada=True,
        usar_ia=True,
        db_produto_obj=SimpleNamespace(nome_base="Produto", dados_brutos_web={}),
        user=SimpleNamespace(id=1),
        dados_extraidos_agregados={"nome": "Produto"},
        dados_coletados_de_fontes_web=False,
        log_mensagens=logs,
        status_para_salvar_no_final=_FakeStatus.PENDENTE,
    )
    assert collected is False
    assert status == _FakeStatus.FALHA_API_EXTERNA


@pytest.mark.asyncio
async def test_executar_llm_skips_when_no_text_and_no_metadata():
    workflow = _build_workflow()
    logs = []

    collected, status = await workflow._executar_llm(
        openai_api_configurada=True,
        usar_ia=None,
        db_produto_obj=SimpleNamespace(nome_base="Produto", dados_brutos_web=None),
        user=SimpleNamespace(id=1),
        dados_extraidos_agregados={},
        dados_coletados_de_fontes_web=True,
        log_mensagens=logs,
        status_para_salvar_no_final=_FakeStatus.PENDENTE,
    )

    assert collected is True
    assert status == _FakeStatus.PENDENTE
    assert logs[-1] == "Nenhum texto ou metadado suficiente para enviar ao LLM."
