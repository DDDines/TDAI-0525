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


class _FakeSession:
    def __init__(self):
        self.closed = False
        self.added = []
        self.commits = 0
        self.refresh_calls = []

    def add(self, obj):
        self.added.append(obj)

    def commit(self):
        self.commits += 1

    def refresh(self, obj, attribute_names=None):
        self.refresh_calls.append((obj, attribute_names))

    def close(self):
        self.closed = True


class _FakeProductRepository:
    def __init__(self, produto, *, fallback_error: Exception | None = None):
        self.produto = produto
        self.fallback_error = fallback_error
        self.status_updates = []

    def get_produto_for_update(self, *, produto_id):
        if self.produto and self.produto.id == produto_id:
            return self.produto
        return None

    def set_web_enrichment_status(self, *, produto_id, status, log_message):
        if self.fallback_error is not None:
            raise self.fallback_error
        self.status_updates.append((produto_id, status, log_message))


def _build_workflow(**overrides):
    defaults = {
        "logger": SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        "SQLAlchemyError": Exception,
        "session_provider": SimpleNamespace(open_session=lambda: _FakeSession()),
        "user_repository_factory": lambda _session: SimpleNamespace(
            get_user=lambda user_id: SimpleNamespace(id=user_id, chave_openai_pessoal=None)
        ),
        "product_repository_factory": lambda _session: _FakeProductRepository(
            SimpleNamespace(
                id=1,
                nome_base="Produto",
                marca="Marca",
                sku="SKU-1",
                modelo="Modelo",
                ean="789",
                categoria_mapeada="Freios",
                categoria_original="Freios",
                fornecedor=None,
                dados_brutos_web={},
                status_enriquecimento_web=_FakeStatus.PENDENTE,
                log_enriquecimento_web=None,
            )
        ),
        "usage_repository_factory": lambda _session: SimpleNamespace(
            create_registro_uso_ia=lambda **kwargs: kwargs
        ),
        "models": _FakeModels,
        "schemas": _FakeSchemas,
        "web_extractor": SimpleNamespace(
            buscar_urls_google=lambda **kwargs: [],
            coletar_conteudo_pagina_playwright=lambda url: None,
            extrair_texto_principal_com_trafilatura=lambda html: None,
            extrair_metadados_estruturados=lambda html, url: {},
            normalizar_dados_de_metadados=lambda value: value,
            extrair_dados_produto_com_llm=lambda **kwargs: None,
            busca_publica_disponivel=lambda: True,
        ),
        "settings": SimpleNamespace(OPENAI_API_KEY="sk-test-12345678901234567890"),
        "json": SimpleNamespace(dumps=lambda *args, **kwargs: "{}"),
        "normalize_human_text": lambda value: value,
        "build_payload_enriquecimento_visivel": lambda **kwargs: ({}, [], []),
        "extrair_dominio_fornecedor": lambda value: value,
        "priorizar_urls_para_enriquecimento": lambda **kwargs: ([], []),
        "is_meaningful_extracted_text": lambda text: bool(text),
        "metadata_has_minimum_signal": lambda metadata: bool(metadata),
        "is_source_relevant_for_product": lambda *args, **kwargs: True,
    }
    defaults.update(overrides)
    return WebEnrichmentTaskWorkflow(**defaults)


def test_helper_branches_cover_short_chunks_specs_keywords_and_none_signal():
    workflow = _build_workflow()

    assert workflow._sanitize_company_timeline_text("x. Produto tecnico robusto") == (
        "Produto tecnico robusto"
    )
    assert workflow._extract_specs_from_text(
        text="Codigo: --; Material: Aco; Aplicacao: Volvo FH; link: //site; EAN: 123",
        limit=5,
    ) == {"material": "Aco", "aplicacao": "Volvo FH"}

    keywords = workflow._extract_keywords(
        source_texts=["aa. http://site 123 freio carga"],
        limit=5,
    )
    assert "aa" not in keywords
    assert "123" not in keywords
    assert "freio" in keywords
    assert workflow._has_meaningful_llm_value(None) is False


def test_heuristic_branches_cover_existing_values_duplicates_and_breaks(monkeypatch):
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
    payload = {
        "nome": "Nome pronto",
        "descricao_curta": "Descricao pronta",
        "descricao_detalhada_seo": "Descricao final pronta",
        "texto_relevante_coletado": "Material: Aco; Aplicacao: Volvo FH; Frase longa suficiente para virar bullet.",
        "especificacoes_tecnicas_dict": {"Material": "Aco"},
        "lista_caracteristicas_beneficios_bullets": ["Bullet repetido"],
        "palavras_chave_seo_relevantes_lista": ["freio"],
    }

    monkeypatch.setattr(
        workflow,
        "_split_sentences",
        lambda **kwargs: [
            "Bullet repetido",
            "Aplicacao em linha pesada",
            "Alta resistencia mecanica",
            "Acabamento tecnico",
            "Instalacao confiavel",
            "Excedente",
        ],
    )
    monkeypatch.setattr(
        workflow,
        "_extract_keywords",
        lambda **kwargs: ["freio", "suspensao", "volvo", "linha-pesada"],
    )

    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=payload,
        log_mensagens=[],
    )

    assert payload["nome"] == "Nome pronto"
    assert payload["descricao_curta"] == "Descricao pronta"
    assert payload["descricao_detalhada_seo"] == "Descricao final pronta"
    assert payload["especificacoes_tecnicas_dict"]["Material"] == "Aco"
    assert payload["especificacoes_tecnicas_dict"]["Aplicacao"] == "Volvo FH"
    assert payload["lista_caracteristicas_beneficios_bullets"] == [
        "Bullet repetido",
        "Aplicacao em linha pesada",
        "Alta resistencia mecanica",
        "Acabamento tecnico",
        "Instalacao confiavel",
    ]
    assert payload["palavras_chave_seo_relevantes_lista"] == [
        "freio",
        "suspensao",
        "volvo",
        "linha-pesada",
    ]


def test_heuristic_branches_cover_empty_name_fallback_and_no_keywords(monkeypatch):
    workflow = _build_workflow()
    produto = SimpleNamespace(
        nome_base="",
        marca="",
        sku="",
        modelo="",
        ean="",
        categoria_mapeada="",
        categoria_original="",
    )
    payload = {
        "texto_relevante_coletado": "Material: Aco. http-prod. Conteudo tecnico.",
        "descricao_detalhada_seo": "descricao pronta",
    }

    monkeypatch.setattr(workflow, "_extract_keywords", lambda **kwargs: [])
    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=payload,
        log_mensagens=[],
    )

    assert "nome" not in payload
    assert "palavras_chave_seo_relevantes_lista" not in payload


def test_helper_branches_cover_http_keyword_and_heuristic_composition_logs(monkeypatch):
    workflow = _build_workflow()
    keywords = workflow._extract_keywords(
        source_texts=["http-prod freio carga pesada"],
        limit=5,
    )
    assert "http-prod" not in keywords
    assert "freio" in keywords

    produto = SimpleNamespace(
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-2",
        modelo="M2",
        ean="",
        categoria_mapeada="Freios",
        categoria_original="Freios",
    )
    payload = {
        "texto_relevante_coletado": "Material: Aco. Aplicacao em freios pesados. Alta resistencia estrutural.",
    }
    monkeypatch.setattr(
        workflow,
        "_split_sentences",
        lambda **kwargs: [
            "Aplicacao em freios pesados",
            "Alta resistencia estrutural",
        ],
    )
    monkeypatch.setattr(workflow, "_extract_keywords", lambda **kwargs: ["freio", "carga"])

    logs = []
    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=payload,
        log_mensagens=logs,
    )

    assert payload["nome"] == "Reservatorio MarcaX SKU-2"
    assert payload["descricao_curta"] == "Aplicacao em freios pesados Alta resistencia estrutural"
    assert payload["especificacoes_tecnicas_dict"]["Material"].startswith("Aco")
    assert payload["palavras_chave_seo_relevantes_lista"] == ["freio", "carga"]
    assert payload["descricao_detalhada_seo"].startswith(payload["descricao_curta"])
    assert any("Nome preenchido heuristica" in item for item in logs)
    assert any("Descricao curta criada heuristica" in item for item in logs)
    assert any("Especificacoes tecnicas inferidas heuristica" in item for item in logs)


@pytest.mark.asyncio
async def test_coletar_de_urls_covers_metadata_discard_duplicate_source_and_break():
    workflow = _build_workflow()

    async def coletar_html(url):
        return f"<html>{url}</html>"

    workflow.web_extractor = SimpleNamespace(
        coletar_conteudo_pagina_playwright=coletar_html,
        extrair_texto_principal_com_trafilatura=lambda html: (
            "Texto tecnico util e suficiente" if "u1" in html else ""
        ),
        extrair_metadados_estruturados=lambda html, url: (
            {"nome": "fraco"} if url.endswith("u1") else {"nome": "Nome forte", "descricao_curta": "Descricao forte"}
        ),
        normalizar_dados_de_metadados=lambda metadata: metadata,
    )
    workflow.metadata_has_minimum_signal = lambda metadata: bool(metadata.get("descricao_curta"))

    payload = {"fontes_web_coletadas": [{"url": "https://site/u1"}]}
    logs = []

    result = await workflow._coletar_de_urls(
        db_produto_obj=SimpleNamespace(id=7, nome_base="Produto"),
        urls_a_processar=["https://site/u1", "https://site/u2"],
        dados_extraidos_agregados=payload,
        log_mensagens=logs,
        busca_web_disponivel=True,
    )

    assert result is True
    assert payload["nome"] == "Nome forte"
    assert payload["descricao_curta"] == "Descricao forte"
    assert payload["fontes_web_coletadas"] == [{"url": "https://site/u1"}]
    assert any("metadados descartados por baixa qualidade" in item.lower() for item in logs)
    assert any("texto principal extraido da url https://site/u1" in item.lower() for item in logs)
    assert any("dados chave (nome, descricao) encontrados" in item.lower() for item in logs)


@pytest.mark.asyncio
async def test_run_covers_session_provider_missing_partial_config_and_ranking_logs():
    with pytest.raises(ValueError, match="session_provider is required"):
        await _build_workflow(
            session_provider=None,
            SQLAlchemyError=RuntimeError,
        ).run(produto_id=1, user_id=2)

    session = _FakeSession()
    produto = SimpleNamespace(
        id=55,
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-9",
        modelo="M9",
        ean="789",
        categoria_mapeada="Freios",
        categoria_original="Freios",
        fornecedor=None,
        dados_brutos_web={},
        status_enriquecimento_web=_FakeStatus.PENDENTE,
        log_enriquecimento_web=None,
    )
    product_repo = _FakeProductRepository(produto)
    finalizer_calls = []
    config_calls = []

    workflow = _build_workflow(
        session_provider=SimpleNamespace(open_session=lambda: session),
        product_repository_factory=lambda _session: product_repo,
        settings=SimpleNamespace(OPENAI_API_KEY=None),
    )
    workflow.config_inspector = SimpleNamespace(
        inspect=lambda **kwargs: SimpleNamespace(
            openai_api_configurada=False,
            google_api_configurada=False,
            busca_publica_fallback=True,
            busca_web_disponivel=True,
            as_log_line=lambda: "cfg",
        )
    )
    workflow._register_config_failure = lambda **kwargs: config_calls.append(kwargs)
    workflow._mark_in_progress = lambda **kwargs: None

    async def fake_busca_urls(**kwargs):
        return ["https://site/u1"]

    workflow._buscar_urls = fake_busca_urls
    workflow.priorizar_urls_para_enriquecimento = lambda **kwargs: ([], [])
    async def fake_coletar_urls(**kwargs):
        return False

    workflow._coletar_de_urls = fake_coletar_urls
    workflow._executar_llm = lambda **kwargs: (_ for _ in ()).throw(
        AssertionError("LLM should not be called directly in this test")
    )
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: finalizer_calls.append(kwargs) or kwargs["status_para_salvar_no_final"]
    )

    async def fake_execute_llm(**kwargs):
        return False, kwargs["status_para_salvar_no_final"]

    workflow._executar_llm = fake_execute_llm

    await workflow.run(produto_id=55, user_id=9)

    final_logs = finalizer_calls[0]["log_mensagens"]
    assert len(config_calls) == 1
    assert any("usando fallback de busca publica sem api key" in item.lower() for item in final_logs)
    assert any("chave api openai nao configurada" in item.lower() for item in final_logs)
    assert any("urls encontradas, mas descartadas" in item.lower() for item in final_logs)
    assert session.closed is True


@pytest.mark.asyncio
async def test_run_covers_unexpected_main_error_and_fallback_failure_logging():
    session = _FakeSession()
    produto = SimpleNamespace(
        id=77,
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-10",
        modelo="M10",
        ean="789",
        categoria_mapeada="Freios",
        categoria_original="Freios",
        fornecedor=None,
        dados_brutos_web={},
        status_enriquecimento_web=_FakeStatus.PENDENTE,
        log_enriquecimento_web=None,
    )
    logger_errors = []
    product_repo = _FakeProductRepository(produto, fallback_error=RuntimeError("fallback fail"))

    workflow = _build_workflow(
        logger=SimpleNamespace(
            info=lambda *a, **k: None,
            error=lambda *a, **k: logger_errors.append(a[0] if a else ""),
        ),
        session_provider=SimpleNamespace(open_session=lambda: session),
        product_repository_factory=lambda _session: product_repo,
    )
    workflow.config_inspector = SimpleNamespace(
        inspect=lambda **kwargs: SimpleNamespace(
            openai_api_configurada=True,
            google_api_configurada=True,
            busca_publica_fallback=False,
            busca_web_disponivel=True,
            as_log_line=lambda: "cfg",
        )
    )
    workflow._mark_in_progress = lambda **kwargs: None

    async def boom_busca(**kwargs):
        raise RuntimeError("boom")

    workflow._buscar_urls = boom_busca
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("persist fail"))
    )

    await workflow.run(produto_id=77, user_id=3)

    assert session.closed is True
    assert any("ERRO CRITICO INESPERADO" in item for item in logger_errors)
    assert any("ERRO CRITICO ao forcar status terminal de falha" in item for item in logger_errors)


@pytest.mark.asyncio
async def test_run_covers_ranking_log_when_urls_scored_exist():
    session = _FakeSession()
    produto = SimpleNamespace(
        id=91,
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-11",
        modelo="M11",
        ean="789",
        categoria_mapeada="Freios",
        categoria_original="Freios",
        fornecedor=None,
        dados_brutos_web={},
        status_enriquecimento_web=_FakeStatus.PENDENTE,
        log_enriquecimento_web=None,
    )
    finalizer_calls = []

    workflow = _build_workflow(
        session_provider=SimpleNamespace(open_session=lambda: session),
        product_repository_factory=lambda _session: _FakeProductRepository(produto),
    )
    workflow.config_inspector = SimpleNamespace(
        inspect=lambda **kwargs: SimpleNamespace(
            openai_api_configurada=True,
            google_api_configurada=True,
            busca_publica_fallback=False,
            busca_web_disponivel=True,
            as_log_line=lambda: "cfg",
        )
    )
    workflow._mark_in_progress = lambda **kwargs: None

    async def fake_busca_urls(**kwargs):
        return ["https://site/a"]

    async def fake_coleta_urls(**kwargs):
        return False

    async def fake_llm(**kwargs):
        return False, kwargs["status_para_salvar_no_final"]

    workflow._buscar_urls = fake_busca_urls
    workflow.priorizar_urls_para_enriquecimento = lambda **kwargs: (
        ["https://site/a"],
        [("https://site/a", 10)],
    )
    workflow._coletar_de_urls = fake_coleta_urls
    workflow._executar_llm = fake_llm
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: finalizer_calls.append(kwargs) or kwargs["status_para_salvar_no_final"]
    )

    await workflow.run(produto_id=91, user_id=4)

    assert any(
        "ranking de urls por relevancia" in item.lower()
        for item in finalizer_calls[0]["log_mensagens"]
    )


@pytest.mark.asyncio
async def test_executar_llm_covers_empty_response_and_em_progresso_run_branch():
    session = _FakeSession()
    produto = SimpleNamespace(
        id=101,
        nome_base="Reservatorio",
        marca="MarcaX",
        sku="SKU-20",
        modelo="M20",
        ean="789",
        categoria_mapeada="Freios",
        categoria_original="Freios",
        fornecedor=None,
        dados_brutos_web={},
        status_enriquecimento_web=_FakeStatus.EM_PROGRESSO,
        log_enriquecimento_web=None,
    )
    product_repo = _FakeProductRepository(produto)
    finalizer_calls = []

    workflow = _build_workflow(
        session_provider=SimpleNamespace(open_session=lambda: session),
        product_repository_factory=lambda _session: product_repo,
        web_extractor=SimpleNamespace(
            extrair_dados_produto_com_llm=None,
            buscar_urls_google=lambda **kwargs: [],
            busca_publica_disponivel=lambda: True,
        ),
    )
    async def _llm_none(**kwargs):
        return None

    workflow.web_extractor.extrair_dados_produto_com_llm = _llm_none

    collected, status_result = await workflow._executar_llm(
        openai_api_configurada=True,
        db_produto_obj=produto,
        user=SimpleNamespace(id=1),
        dados_extraidos_agregados={"texto_relevante_coletado": "Texto tecnico util"},
        dados_coletados_de_fontes_web=False,
        log_mensagens=[],
        status_para_salvar_no_final=_FakeStatus.PENDENTE,
    )
    assert collected is False
    assert status_result == _FakeStatus.PENDENTE

    workflow.config_inspector = SimpleNamespace(
        inspect=lambda **kwargs: SimpleNamespace(
            openai_api_configurada=False,
            google_api_configurada=False,
            busca_publica_fallback=True,
            busca_web_disponivel=True,
            as_log_line=lambda: "cfg",
        )
    )
    workflow._register_config_failure = lambda **kwargs: None
    workflow._mark_in_progress = lambda **kwargs: None

    async def _buscar_urls(**kwargs):
        return []

    async def _coletar_de_urls(**kwargs):
        return False

    workflow._buscar_urls = _buscar_urls
    workflow._coletar_de_urls = _coletar_de_urls

    async def _executar_llm_guard(**kwargs):
        raise AssertionError("nao deve chamar llm")

    workflow._executar_llm = _executar_llm_guard
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: finalizer_calls.append(kwargs) or kwargs["status_para_salvar_no_final"]
    )

    await workflow.run(produto_id=101, user_id=5)

    assert any("EM_PROGRESSO no inicio" in item for item in finalizer_calls[0]["log_mensagens"])
