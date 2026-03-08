from __future__ import annotations

from collections import UserDict
from enum import Enum
from types import SimpleNamespace

import pytest

from Backend.application.services.web_enrichment_components import (
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
)
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
    FALHOU = "FALHOU"


class _FakeModels:
    StatusEnriquecimentoEnum = _FakeStatus


class _FakeProdutoUpdate:
    def __init__(self, **kwargs):
        self.payload = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeSchemas:
    ProdutoUpdate = _FakeProdutoUpdate
    RegistroUsoIACreate = _FakeProdutoUpdate


class _FakeCrudProdutos:
    def __init__(self):
        self.calls = []

    def update_produto(self, *, db_produto, produto_update):
        self.calls.append((db_produto, produto_update))
        return db_produto


class _FakeSession:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _SessionProviderStub:
    def __init__(self, session):
        self._session = session

    def open_session(self):
        return self._session


class _FakeProductRepository:
    def __init__(self, produto):
        self.produto = produto
        self.status_updates = []

    def get_produto_for_update(self, *, produto_id):
        if self.produto and self.produto.id == produto_id:
            return self.produto
        return None

    def get_produto(self, *, produto_id):
        return self.get_produto_for_update(produto_id=produto_id)

    def set_web_enrichment_status(self, *, produto_id, status, log_message):
        self.status_updates.append(
            {
                "produto_id": produto_id,
                "status": status,
                "log_message": log_message,
            }
        )


class _FakeUsageRepository:
    def __init__(self):
        self.calls = []

    def create_registro_uso_ia(self, *, registro_uso):
        self.calls.append(registro_uso)
        return registro_uso


def _build_workflow() -> WebEnrichmentTaskWorkflow:
    return WebEnrichmentTaskWorkflow(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        SQLAlchemyError=Exception,
        session_provider=SimpleNamespace(open_session=lambda: object()),
        user_repository_factory=lambda _session: SimpleNamespace(),
        product_repository_factory=lambda _session: SimpleNamespace(),
        usage_repository_factory=lambda _session: SimpleNamespace(),
        models=_FakeModels,
        schemas=_FakeSchemas,
        web_extractor=SimpleNamespace(),
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


def test_query_planner_covers_non_dict_raw_payload_and_code_only_candidates():
    planner = WebEnrichmentQueryPlanner()
    produto = SimpleNamespace(
        nome_base="",
        sku="",
        ean="",
        fornecedor=SimpleNamespace(nome="RochParts"),
        dados_brutos_web="invalido",
        dynamic_attributes={
            "codigo_ref": "ABCD-123",
            "aplicacao": "Ford Cargo",
        },
    )

    candidates = planner.build_candidates(
        db_produto_obj=produto,
        termos_busca_override=None,
    )

    assert "ABCD-123 peca automotiva" in candidates
    assert "ABCD-123 RochParts" in candidates
    assert "ABCD-123 Ford Cargo" in candidates
    assert not any("especificacoes tecnicas detalhadas" in item for item in candidates)


def test_finalization_service_covers_non_dict_mapping_and_dynamic_repeat_branch():
    crud_produtos = _FakeCrudProdutos()
    finalizer = WebEnrichmentFinalizationService(
        normalize_human_text=lambda txt: txt,
        build_payload_enriquecimento_visivel=lambda **kwargs: (
            UserDict({"dynamic_attributes": {"cor": "branco", "acabamento": "fosco"}}),
            [],
            [],
        ),
        schemas=_FakeSchemas,
        product_repository_factory=lambda _session: crud_produtos,
        models=_FakeModels,
    )
    produto = SimpleNamespace(
        id=44,
        status_enriquecimento_web=_FakeStatus.CONCLUIDO_SUCESSO,
        dynamic_attributes={"cor": "branco", "acabamento": "brilhante"},
    )

    finalizer.apply(
        db=object(),
        db_produto_obj=produto,
        status_para_salvar_no_final=_FakeStatus.CONCLUIDO_SUCESSO,
        dados_extraidos_agregados={},
        log_mensagens=[],
    )

    _, produto_update = crud_produtos.calls[0]
    detalhes = produto_update.payload["log_enriquecimento_web"]["resumo_aplicacao"][
        "campos_alterados_detalhe"
    ]
    assert detalhes == []


def test_finalization_service_covers_dynamic_iteration_with_unchanged_then_changed_values():
    crud_produtos = _FakeCrudProdutos()
    finalizer = WebEnrichmentFinalizationService(
        normalize_human_text=lambda txt: txt,
        build_payload_enriquecimento_visivel=lambda **kwargs: (
            {"dynamic_attributes": {"cor": "branco", "acabamento": "fosco"}},
            [],
            [],
        ),
        schemas=_FakeSchemas,
        product_repository_factory=lambda _session: crud_produtos,
        models=_FakeModels,
    )
    produto = SimpleNamespace(
        id=45,
        status_enriquecimento_web=_FakeStatus.CONCLUIDO_SUCESSO,
        dynamic_attributes={"cor": "branco", "acabamento": "brilhante"},
    )

    finalizer.apply(
        db=object(),
        db_produto_obj=produto,
        status_para_salvar_no_final=_FakeStatus.CONCLUIDO_SUCESSO,
        dados_extraidos_agregados={},
        log_mensagens=[],
    )

    _, produto_update = crud_produtos.calls[0]
    detalhes = produto_update.payload["log_enriquecimento_web"]["resumo_aplicacao"][
        "campos_alterados_detalhe"
    ]
    assert detalhes == ["dynamic.acabamento: 'brilhante' -> 'fosco'"]


def test_aplicar_enriquecimento_heuristico_can_leave_optional_fields_empty():
    workflow = _build_workflow()
    produto = SimpleNamespace(
        nome_base="Reservatorio",
        marca="",
        modelo="",
        sku="",
        ean="",
        categoria_mapeada="",
        categoria_original="",
    )
    dados = {"texto_relevante_coletado": "Texto base relevante para heuristica"}
    logs = []

    def fake_compact(text, max_len=0):
        if text == "Texto base relevante para heuristica" and max_len == 14000:
            return text
        return ""

    workflow._compact_text = fake_compact
    workflow._split_sentences = lambda **kwargs: []
    workflow._extract_specs_from_text = lambda **kwargs: {}
    workflow._extract_keywords = lambda **kwargs: []

    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=dados,
        log_mensagens=logs,
    )

    assert dados["descricao_curta"] == ""
    assert "lista_caracteristicas_beneficios_bullets" not in dados
    assert dados["descricao_detalhada_seo"] == ""


def test_aplicar_enriquecimento_heuristico_preserves_existing_bullets_without_refill():
    workflow = _build_workflow()
    produto = SimpleNamespace(
        nome_base="Reservatorio",
        marca="",
        modelo="",
        sku="",
        ean="",
        categoria_mapeada="",
        categoria_original="",
    )
    dados = {
        "texto_relevante_coletado": "Texto base relevante para heuristica",
        "lista_caracteristicas_beneficios_bullets": [
            "bullet 1",
            "bullet 2",
            "bullet 3",
        ],
    }

    workflow._extract_specs_from_text = lambda **kwargs: {}
    workflow._extract_keywords = lambda **kwargs: []

    workflow._aplicar_enriquecimento_heuristico(
        db_produto_obj=produto,
        dados_extraidos_agregados=dados,
        log_mensagens=[],
    )

    assert dados["lista_caracteristicas_beneficios_bullets"][:3] == [
        "bullet 1",
        "bullet 2",
        "bullet 3",
    ]


@pytest.mark.asyncio
async def test_executar_llm_keeps_status_when_error_but_web_data_already_exists():
    workflow = _build_workflow()

    async def fake_llm(**kwargs):
        return {"erro_llm": "falhou"}

    workflow.web_extractor = SimpleNamespace(extrair_dados_produto_com_llm=fake_llm)
    payload = {"descricao_curta": "metadata"}
    collected, status = await workflow._executar_llm(
        openai_api_configurada=True,
        db_produto_obj=SimpleNamespace(nome_base="Reservatorio", dados_brutos_web={}),
        user=SimpleNamespace(id=7),
        dados_extraidos_agregados=payload,
        dados_coletados_de_fontes_web=True,
        log_mensagens=[],
        status_para_salvar_no_final=_FakeStatus.EM_PROGRESSO,
    )

    assert collected is True
    assert status == _FakeStatus.EM_PROGRESSO


@pytest.mark.asyncio
async def test_run_keeps_aggregated_payload_empty_for_non_dict_raw_data():
    session = _FakeSession()
    produto = SimpleNamespace(
        id=88,
        nome_base="Reservatorio",
        fornecedor=None,
        dados_brutos_web="texto cru",
        status_enriquecimento_web=_FakeStatus.EM_PROGRESSO,
        log_enriquecimento_web=None,
    )
    product_repo = _FakeProductRepository(produto)
    finalizer_calls = []
    workflow = WebEnrichmentTaskWorkflow(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        SQLAlchemyError=Exception,
        session_provider=_SessionProviderStub(session),
        user_repository_factory=lambda _session: SimpleNamespace(get_user=lambda user_id: None),
        product_repository_factory=lambda _session: product_repo,
        usage_repository_factory=lambda _session: _FakeUsageRepository(),
        models=_FakeModels,
        schemas=_FakeSchemas,
        web_extractor=SimpleNamespace(),
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
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: finalizer_calls.append(kwargs) or kwargs["status_para_salvar_no_final"]
    )

    await workflow.run(produto_id=88, user_id=404)

    assert finalizer_calls[0]["dados_extraidos_agregados"] == {}
    assert session.closed is True


@pytest.mark.asyncio
async def test_run_can_skip_finalization_and_close_when_product_turns_falsy():
    class _ToggleProduto:
        def __init__(self):
            self.id = 66
            self.nome_base = "Reservatorio"
            self.fornecedor = None
            self.dados_brutos_web = {}
            self.status_enriquecimento_web = _FakeStatus.PENDENTE
            self.log_enriquecimento_web = None
            self._bool_calls = 0

        def __bool__(self):
            self._bool_calls += 1
            return self._bool_calls <= 2

    produto = _ToggleProduto()
    product_repo = _FakeProductRepository(produto)
    finalizer_calls = []
    workflow = WebEnrichmentTaskWorkflow(
        logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
        SQLAlchemyError=Exception,
        session_provider=_SessionProviderStub(None),
        user_repository_factory=lambda _session: SimpleNamespace(get_user=lambda user_id: None),
        product_repository_factory=lambda _session: product_repo,
        usage_repository_factory=lambda _session: _FakeUsageRepository(),
        models=_FakeModels,
        schemas=_FakeSchemas,
        web_extractor=SimpleNamespace(),
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
    workflow.finalization_service = SimpleNamespace(
        apply=lambda **kwargs: finalizer_calls.append(kwargs) or kwargs["status_para_salvar_no_final"]
    )

    await workflow.run(produto_id=66, user_id=999)

    assert finalizer_calls == []
