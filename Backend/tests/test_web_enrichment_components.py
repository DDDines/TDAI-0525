"""Module test web enrichment components.

Contains backend logic related to test web enrichment components and documents its role in the OOP architecture.
"""

from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import pytest

from Backend.application.services.web_enrichment_components import (
    WebEnrichmentConfigInspector,
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
    WebEnrichmentStatusResolver,
)


class _FakeStatus(Enum):
    """Represent fake status and centralize responsibilities for this module."""
    EM_PROGRESSO = "EM_PROGRESSO"
    FALHOU = "FALHOU"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"


class _FakeModels:
    """Represent fake models and centralize responsibilities for this module."""
    StatusEnriquecimentoEnum = _FakeStatus


class _FakeProdutoUpdate:
    """Represent fake produto update and centralize responsibilities for this module."""
    def __init__(self, **kwargs):
        """Initialize collaborators and configuration required by this component."""
        self.payload = kwargs


class _FakeSchemas:
    """Represent fake schemas and centralize responsibilities for this module."""
    ProdutoUpdate = _FakeProdutoUpdate


class _FakeCrudProdutos:
    """Represent fake crud produtos and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def update_produto(self, *, db_produto, produto_update):
        """Update produto for this workflow."""
        self.calls.append((db_produto, produto_update))


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_config_snapshot_as_log_line_formats_flags():
        """Expose the config snapshot formatting branch directly."""
        snapshot = WebEnrichmentConfigInspector().inspect(
            user=SimpleNamespace(chave_openai_pessoal="sk-test-12345678901234567890"),
            settings=SimpleNamespace(OPENAI_API_KEY=None, GOOGLE_CSE_API_KEY=None, GOOGLE_CSE_ID=None),
            web_extractor=SimpleNamespace(busca_publica_disponivel=lambda: False),
        )

        assert snapshot.as_log_line() == (
            "Config API: openai_user=sim, openai_sistema=nao, google_cse=nao, busca_publica=nao."
        )

    def test_config_inspector_reads_sources():
        """Run test config inspector reads sources in this workflow."""
        inspector = WebEnrichmentConfigInspector()
        user = SimpleNamespace(chave_openai_pessoal=None)
        settings = SimpleNamespace(OPENAI_API_KEY=None, GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx")
        extractor = SimpleNamespace(busca_publica_disponivel=lambda: True)
    
        snapshot = inspector.inspect(user=user, settings=settings, web_extractor=extractor)
        assert snapshot.openai_api_configurada is False
        assert snapshot.google_api_configurada is True
        assert snapshot.busca_publica_fallback is True
        assert snapshot.busca_web_disponivel is True

    def test_config_inspector_ignora_openai_malformada():
        """Treat malformed saved OpenAI values as absent configuration."""
        inspector = WebEnrichmentConfigInspector()
        user = SimpleNamespace(chave_openai_pessoal="adminpassword")
        settings = SimpleNamespace(
            OPENAI_API_KEY="not-a-real-key",
            GOOGLE_CSE_API_KEY="k",
            GOOGLE_CSE_ID="cx",
        )
        extractor = SimpleNamespace(busca_publica_disponivel=lambda: True)

        snapshot = inspector.inspect(user=user, settings=settings, web_extractor=extractor)
        assert snapshot.openai_user_configurada is False
        assert snapshot.openai_system_configurada is False
        assert snapshot.openai_api_configurada is False
        assert snapshot.busca_web_disponivel is True

    def test_query_planner_override_has_priority():
        """Run test query planner override has priority in this workflow."""
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
        """Run test query planner generates base terms in this workflow."""
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

    def test_query_planner_helpers_cover_token_filters_and_dynamic_hints():
        """Exercise helper branches used when building search candidates."""
        planner = WebEnrichmentQueryPlanner()
        assert planner._dedupe(["a", "a", "", "b"]) == ["a", "b"]
        assert planner._extract_code_tokens("sem codigo util") == []
        assert planner._extract_code_tokens("Ref SP-1081 / abc / 1234") == ["SP-1081"]
        assert planner._dynamic_text_hints(None) == {"aplicacao": "", "material": "", "marca": ""}
        assert planner._dynamic_text_hints(
            {
                "Aplicacao principal": "Ford Cargo",
                "Material Base": "Aco",
                "Marca Original": "Rodo",
            }
        ) == {
            "aplicacao": "Ford Cargo",
            "material": "Aco",
            "marca": "Rodo",
        }

    def test_query_planner_generates_code_and_dynamic_queries():
        """Generate queries from code-like dynamic fields and supplier name."""
        planner = WebEnrichmentQueryPlanner()
        produto = SimpleNamespace(
            nome_base="Reservatorio de Ar",
            sku="RA-5500",
            ean="",
            fornecedor=SimpleNamespace(nome="RochParts"),
            dados_brutos_web={"codigo_original": "XP-9988"},
            dynamic_attributes={
                "codigo_ref": "ABC-7788",
                "aplicacao": "Volvo FH",
                "material": "Aco carbono",
                "marca": "Master",
            },
        )

        candidates = planner.build_candidates(
            db_produto_obj=produto,
            termos_busca_override=None,
        )

        assert any("Volvo FH" in item for item in candidates)
        assert any("Aco carbono" in item for item in candidates)
        assert any("RochParts" in item for item in candidates)
        assert any("peca automotiva" in item for item in candidates)

    def test_status_resolver_handles_partial_without_openai():
        """Run test status resolver handles partial without openai in this workflow."""
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
        """Run test status resolver handles no sources in this workflow."""
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

    @pytest.mark.parametrize(
        ("input_status", "dados", "openai", "busca", "urls", "expected"),
        [
            (_FakeStatus.CONCLUIDO_SUCESSO, False, False, False, [], _FakeStatus.CONCLUIDO_SUCESSO),
            (_FakeStatus.FALHOU, True, True, True, ["https://ok"], _FakeStatus.CONCLUIDO_SUCESSO),
            (_FakeStatus.EM_PROGRESSO, False, False, True, ["https://ok"], _FakeStatus.NENHUMA_FONTE_ENCONTRADA),
            (_FakeStatus.EM_PROGRESSO, False, True, False, [], _FakeStatus.NENHUMA_FONTE_ENCONTRADA),
            (_FakeStatus.EM_PROGRESSO, False, True, True, [], _FakeStatus.NENHUMA_FONTE_ENCONTRADA),
        ],
    )
    def test_status_resolver_cobre_demais_ramos(input_status, dados, openai, busca, urls, expected):
        """Cover remaining resolver branches explicitly."""
        resolver = WebEnrichmentStatusResolver()
        assert resolver.resolve(
            models=_FakeModels,
            status_para_salvar_no_final=input_status,
            dados_coletados_de_fontes_web=dados,
            openai_api_configurada=openai,
            busca_web_disponivel=busca,
            urls_a_processar=urls,
        ) == expected

    def test_finalization_service_updates_payload_and_normalizes_logs():
        """Run test finalization service updates payload and normalizes logs in this workflow."""
        crud_produtos = _FakeCrudProdutos()
        finalizer = WebEnrichmentFinalizationService(
            normalize_human_text=lambda txt: txt.strip(),
            build_payload_enriquecimento_visivel=lambda **kwargs: (
                {"descricao_original": "Nova"},
                ["descricao_original"],
                ["marca"],
            ),
            schemas=_FakeSchemas,
            product_repository_factory=lambda _session: crud_produtos,
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
        _, produto_update = crud_produtos.calls[0]
        assert produto_update.payload["descricao_original"] == "Nova"
        assert produto_update.payload["status_enriquecimento_web"] == _FakeStatus.FALHOU.value
        assert "resumo_aplicacao" in produto_update.payload["log_enriquecimento_web"]

    def test_finalization_service_cobre_sem_campos_visiveis_e_com_dynamic_attributes():
        """Cover ignored/no-op finalization branches and dynamic diff formatting."""
        crud_produtos = _FakeCrudProdutos()
        finalizer = WebEnrichmentFinalizationService(
            normalize_human_text=lambda txt: txt.strip() if txt.strip() != "skip" else "",
            build_payload_enriquecimento_visivel=lambda **kwargs: (
                {"dynamic_attributes": {"cor": "preto"}},
                [],
                ["descricao_original"],
            ),
            schemas=_FakeSchemas,
            product_repository_factory=lambda _session: crud_produtos,
            models=_FakeModels,
        )
        produto = SimpleNamespace(
            id=77,
            status_enriquecimento_web=_FakeStatus.CONCLUIDO_SUCESSO,
            dynamic_attributes={"cor": "branco"},
        )
        logs = [" skip ", " log util "]

        final_status = finalizer.apply(
            db=object(),
            db_produto_obj=produto,
            status_para_salvar_no_final=_FakeStatus.CONCLUIDO_SUCESSO,
            dados_extraidos_agregados={},
            log_mensagens=logs,
        )

        assert final_status == _FakeStatus.CONCLUIDO_SUCESSO
        _, produto_update = crud_produtos.calls[0]
        resumo = produto_update.payload["log_enriquecimento_web"]["resumo_aplicacao"]
        assert resumo["aplicados_total"] == 0
        assert resumo["ignorados_total"] == 1
        assert "dynamic.cor" in resumo["campos_alterados_detalhe"][0]
        assert produto_update.payload["log_enriquecimento_web"]["historico_mensagens"] == [
            "log util",
            "Enriquecimento finalizado sem novos campos visiveis para preencher no produto.",
            "Campos ignorados (mantidos os valores atuais): descricao_original",
            "Resumo de aplicação: 0 aplicado(s), 1 ignorado(s).",
        ]

test_config_snapshot_as_log_line_formats_flags = _TopLevelFunctionSurface.test_config_snapshot_as_log_line_formats_flags
test_config_inspector_reads_sources = _TopLevelFunctionSurface.test_config_inspector_reads_sources
test_config_inspector_ignora_openai_malformada = _TopLevelFunctionSurface.test_config_inspector_ignora_openai_malformada
test_query_planner_override_has_priority = _TopLevelFunctionSurface.test_query_planner_override_has_priority
test_query_planner_generates_base_terms = _TopLevelFunctionSurface.test_query_planner_generates_base_terms
test_query_planner_helpers_cover_token_filters_and_dynamic_hints = (
    _TopLevelFunctionSurface.test_query_planner_helpers_cover_token_filters_and_dynamic_hints
)
test_query_planner_generates_code_and_dynamic_queries = (
    _TopLevelFunctionSurface.test_query_planner_generates_code_and_dynamic_queries
)
test_status_resolver_handles_partial_without_openai = _TopLevelFunctionSurface.test_status_resolver_handles_partial_without_openai
test_status_resolver_handles_no_sources = _TopLevelFunctionSurface.test_status_resolver_handles_no_sources
test_status_resolver_cobre_demais_ramos = _TopLevelFunctionSurface.test_status_resolver_cobre_demais_ramos
test_finalization_service_updates_payload_and_normalizes_logs = _TopLevelFunctionSurface.test_finalization_service_updates_payload_and_normalizes_logs
test_finalization_service_cobre_sem_campos_visiveis_e_com_dynamic_attributes = (
    _TopLevelFunctionSurface.test_finalization_service_cobre_sem_campos_visiveis_e_com_dynamic_attributes
)










