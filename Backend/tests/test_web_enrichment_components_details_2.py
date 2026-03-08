from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

from Backend.application.services.web_enrichment_components import (
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


class _CrudProdutos:
    def __init__(self):
        self.calls = []

    def update_produto(self, *, db_produto, produto_update):
        self.calls.append((db_produto, produto_update))


def test_query_planner_helpers_cover_blank_and_non_digit_token_paths():
    planner = WebEnrichmentQueryPlanner()

    assert planner._extract_code_tokens("") == []
    assert planner._extract_code_tokens("A-1/2") == []
    assert planner._extract_code_tokens("ABCD-") == []
    assert planner._extract_code_tokens("ABCDE") == []
    assert planner._dynamic_text_hints(
        {
            "aplicacao": None,
            "material": "   ",
            "outra": "valor",
        }
    ) == {"aplicacao": "", "material": "", "marca": ""}


def test_status_resolver_uses_simplified_terminal_logic():
    resolver = WebEnrichmentStatusResolver()

    assert resolver.resolve(
        models=_FakeModels,
        status_para_salvar_no_final=_FakeStatus.EM_PROGRESSO,
        dados_coletados_de_fontes_web=False,
        openai_api_configurada=True,
        busca_web_disponivel=False,
        urls_a_processar=[],
    ) == _FakeStatus.NENHUMA_FONTE_ENCONTRADA

    assert resolver.resolve(
        models=_FakeModels,
        status_para_salvar_no_final=_FakeStatus.FALHOU,
        dados_coletados_de_fontes_web=False,
        openai_api_configurada=False,
        busca_web_disponivel=False,
        urls_a_processar=[],
    ) == _FakeStatus.FALHA_CONFIGURACAO_API_EXTERNA


def test_finalization_service_handles_dict_payload_without_field_changes():
    crud_produtos = _CrudProdutos()
    finalizer = WebEnrichmentFinalizationService(
        normalize_human_text=lambda txt: txt,
        build_payload_enriquecimento_visivel=lambda **kwargs: (
            {"descricao_original": "igual"},
            ["nome"],
            [],
        ),
        schemas=_FakeSchemas,
        product_repository_factory=lambda _db: crud_produtos,
        models=_FakeModels,
    )
    produto = SimpleNamespace(
        id=1,
        status_enriquecimento_web=_FakeStatus.CONCLUIDO_SUCESSO,
        dynamic_attributes=None,
        descricao_original="igual",
    )

    result = finalizer.apply(
        db=object(),
        db_produto_obj=produto,
        status_para_salvar_no_final=_FakeStatus.CONCLUIDO_SUCESSO,
        dados_extraidos_agregados={},
        log_mensagens=["mensagem"],
    )

    assert result == _FakeStatus.CONCLUIDO_SUCESSO
    assert crud_produtos.calls[0][1].payload["dados_brutos_web"] == {}
    assert crud_produtos.calls[0][1].payload["log_enriquecimento_web"]["resumo_aplicacao"]["campos_alterados_detalhe"] == []
