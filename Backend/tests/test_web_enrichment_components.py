from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

from Backend.application.services.web_enrichment_components import (
    WebEnrichmentConfigInspector,
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
    WebEnrichmentStatusResolver,
)


class _FakeStatus(Enum):
    EM_PROGRESSO = "EM_PROGRESSO"
    FALHOU = "FALHOU"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"


class _FakeModels:
    StatusEnriquecimentoEnum = _FakeStatus


class _FakeProdutoUpdate:
    def __init__(self, **kwargs):
        self.payload = kwargs


class _FakeSchemas:
    ProdutoUpdate = _FakeProdutoUpdate


class _FakeCrudProdutos:
    def __init__(self):
        self.calls = []

    def update_produto(self, db, db_produto, produto_update):
        self.calls.append((db, db_produto, produto_update))


def test_config_inspector_reads_sources():
    inspector = WebEnrichmentConfigInspector()
    user = SimpleNamespace(chave_openai_pessoal=None)
    settings = SimpleNamespace(OPENAI_API_KEY=None, GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx")
    extractor = SimpleNamespace(busca_publica_disponivel=lambda: True)

    snapshot = inspector.inspect(user=user, settings=settings, web_extractor=extractor)
    assert snapshot.openai_api_configurada is False
    assert snapshot.google_api_configurada is True
    assert snapshot.busca_publica_fallback is True
    assert snapshot.busca_web_disponivel is True


def test_query_planner_override_has_priority():
    planner = WebEnrichmentQueryPlanner()
    produto = SimpleNamespace(
        nome_base="Suporte do Aparabarro",
        sku="ABC-123",
        ean="7891234567890",
        fornecedor=SimpleNamespace(nome="Amalcaburio"),
        dados_brutos_web={"codigo_original": "SP1081"},
    )
    candidates = planner.build_candidates(
        db_produto_obj=produto,
        termos_busca_override="termo customizado",
    )
    assert candidates == ["termo customizado"]


def test_query_planner_generates_base_terms():
    planner = WebEnrichmentQueryPlanner()
    produto = SimpleNamespace(
        nome_base="Suporte do Aparabarro",
        sku="ABC-123",
        ean="7891234567890",
        fornecedor=SimpleNamespace(nome="Amalcaburio"),
        dados_brutos_web={"codigo_original": "SP1081"},
    )
    candidates = planner.build_candidates(
        db_produto_obj=produto,
        termos_busca_override=None,
    )
    assert any("especificacoes tecnicas detalhadas" in q for q in candidates)
    assert any("ficha tecnica" in q for q in candidates)
    assert "SP1081" in candidates


def test_status_resolver_handles_partial_without_openai():
    resolver = WebEnrichmentStatusResolver()
    status = resolver.resolve(
        models=_FakeModels,
        status_para_salvar_no_final=_FakeStatus.FALHOU,
        dados_coletados_de_fontes_web=True,
        openai_api_configurada=False,
        busca_web_disponivel=True,
        urls_a_processar=["https://example.com/item"],
    )
    assert status == _FakeStatus.CONCLUIDO_COM_DADOS_PARCIAIS


def test_status_resolver_handles_no_sources():
    resolver = WebEnrichmentStatusResolver()
    status = resolver.resolve(
        models=_FakeModels,
        status_para_salvar_no_final=_FakeStatus.EM_PROGRESSO,
        dados_coletados_de_fontes_web=False,
        openai_api_configurada=False,
        busca_web_disponivel=False,
        urls_a_processar=[],
    )
    assert status == _FakeStatus.FALHA_CONFIGURACAO_API_EXTERNA


def test_finalization_service_updates_payload_and_normalizes_logs():
    crud_produtos = _FakeCrudProdutos()
    finalizer = WebEnrichmentFinalizationService(
        normalize_human_text=lambda txt: txt.strip(),
        build_payload_enriquecimento_visivel=lambda **kwargs: (
            {"descricao_original": "Nova"},
            ["descricao_original"],
            ["marca"],
        ),
        schemas=_FakeSchemas,
        product_repository=crud_produtos,
        models=_FakeModels,
    )
    db_obj = object()
    produto = SimpleNamespace(
        id=55,
        status_enriquecimento_web=_FakeStatus.EM_PROGRESSO,
    )
    logs = [" log 1 ", "log 2"]
    final_status = finalizer.apply(
        db=db_obj,
        db_produto_obj=produto,
        status_para_salvar_no_final=_FakeStatus.EM_PROGRESSO,
        dados_extraidos_agregados={"k": "v"},
        log_mensagens=logs,
    )

    assert final_status == _FakeStatus.FALHOU
    assert len(crud_produtos.calls) == 1
    _, _, produto_update = crud_produtos.calls[0]
    assert produto_update.payload["descricao_original"] == "Nova"
    assert produto_update.payload["status_enriquecimento_web"] == _FakeStatus.FALHOU.value
    assert "resumo_aplicacao" in produto_update.payload["log_enriquecimento_web"]
