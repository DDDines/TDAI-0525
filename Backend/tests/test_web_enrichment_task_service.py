"""Module test web enrichment task service.

Contains backend logic related to test web enrichment task service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

import pytest

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskWorkflow,
)


class _FakeStatus(Enum):
    """Represent fake status and centralize responsibilities for this module."""

    PENDENTE = "PENDENTE"
    EM_PROGRESSO = "EM_PROGRESSO"
    CONCLUIDO_SUCESSO = "CONCLUIDO_SUCESSO"
    CONCLUIDO_COM_DADOS_PARCIAIS = "CONCLUIDO_COM_DADOS_PARCIAIS"
    NENHUMA_FONTE_ENCONTRADA = "NENHUMA_FONTE_ENCONTRADA"
    FALHA_API_EXTERNA = "FALHA_API_EXTERNA"
    FALHA_CONFIGURACAO_API_EXTERNA = "FALHA_CONFIGURACAO_API_EXTERNA"
    FALHOU = "FALHOU"


class _FakeTipoAcaoEnum(Enum):
    """Represent fake tipo acao enum and centralize responsibilities for this module."""

    ENRIQUECIMENTO_WEB_PRODUTO = "enriquecimento_web_produto"


class _FakeRegistroUsoIACreate:
    """Represent fake usage schema and centralize responsibilities for this module."""

    def __init__(self, **kwargs):
        """Store input payload for later assertions."""
        self.payload = kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeModels:
    """Represent fake models and centralize responsibilities for this module."""

    StatusEnriquecimentoEnum = _FakeStatus
    TipoAcaoEnum = _FakeTipoAcaoEnum


class _FakeSchemas:
    """Represent fake schemas and centralize responsibilities for this module."""

    RegistroUsoIACreate = _FakeRegistroUsoIACreate
    ProdutoUpdate = lambda **kwargs: kwargs


class _FakeSession:
    """Represent fake session and centralize responsibilities for this module."""

    def __init__(self):
        """Track session operations for assertions."""
        self.commits = 0
        self.refreshes = []
        self.closed = False

    def commit(self):
        """Track commit execution."""
        self.commits += 1

    def refresh(self, obj):
        """Track refresh execution."""
        self.refreshes.append(obj)

    def close(self):
        """Track session closing."""
        self.closed = True


class _SessionProviderStub:
    """Represent session provider stub and centralize responsibilities for this module."""

    def __init__(self, session):
        """Store session to be returned by open_session."""
        self._session = session

    def open_session(self):
        """Return the injected session instance."""
        return self._session


class _FakeUsageRepository:
    """Represent fake usage repository and centralize responsibilities for this module."""

    def __init__(self):
        """Capture created usage entries."""
        self.calls = []

    def create_registro_uso_ia(self, *, registro_uso):
        """Capture usage creation calls."""
        self.calls.append(registro_uso)
        return registro_uso


class _FakeProductRepository:
    """Represent fake product repository and centralize responsibilities for this module."""

    def __init__(self, produto):
        """Initialize collaborators and storage required by this repository stub."""
        self.produto = produto
        self.status_updates = []
        self.update_calls = []

    def get_produto_for_update(self, *, produto_id):
        """Return the tracked product if ids match."""
        if self.produto and self.produto.id == produto_id:
            return self.produto
        return None

    def get_produto(self, *, produto_id):
        """Fallback getter for products."""
        return self.get_produto_for_update(produto_id=produto_id)

    def set_web_enrichment_status(self, *, produto_id, status, log_message):
        """Capture forced terminal status updates."""
        self.status_updates.append(
            {
                "produto_id": produto_id,
                "status": status,
                "log_message": log_message,
            }
        )

    def update_produto(self, *, db_produto, produto_update):
        """Capture product update payloads used by finalization."""
        self.update_calls.append(
            {
                "db_produto": db_produto,
                "produto_update": produto_update,
            }
        )
        return db_produto


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""

    @staticmethod
    def _build_workflow() -> WebEnrichmentTaskWorkflow:
        """Build a workflow instance with lightweight runtime stubs."""
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

    @staticmethod
    def test_aplicar_enriquecimento_heuristico_popula_campos_chave():
        """Run test aplicar enriquecimento heuristico popula campos chave in this workflow."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        produto = SimpleNamespace(
            nome_base="Suporte de Fixacao",
            marca="Pickup Parts",
            modelo="SP1081",
            sku="SP1081",
            ean="7891234567890",
            categoria_mapeada="Lataria",
            categoria_original="Lataria",
        )
        dados = {
            "texto_relevante_coletado": (
                "Suporte de fixacao reforcado para linha pesada. "
                "Material: Aco carbono. Aplicacao: Ford Cargo. "
                "Acabamento: Pintura eletrostatica."
            ),
        }
        logs = []

        workflow._aplicar_enriquecimento_heuristico(
            db_produto_obj=produto,
            dados_extraidos_agregados=dados,
            log_mensagens=logs,
        )

        assert dados.get("nome")
        assert dados.get("descricao_curta")
        assert dados.get("descricao_detalhada_seo")
        assert isinstance(dados.get("lista_caracteristicas_beneficios_bullets"), list)
        assert len(dados.get("lista_caracteristicas_beneficios_bullets")) >= 1
        assert isinstance(dados.get("palavras_chave_seo_relevantes_lista"), list)
        assert len(dados.get("palavras_chave_seo_relevantes_lista")) >= 3
        assert isinstance(dados.get("especificacoes_tecnicas_dict"), dict)
        assert "Material" in dados.get("especificacoes_tecnicas_dict")

    @staticmethod
    def test_merge_collected_text_acumula_sem_duplicar():
        """Run test merge collected text acumula sem duplicar in this workflow."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        merged = workflow._merge_collected_text(
            existing_text="Texto base do produto.",
            new_text="Detalhes adicionais da aplicacao.",
            max_len=200,
        )
        merged_again = workflow._merge_collected_text(
            existing_text=merged,
            new_text="Texto base do produto.",
            max_len=200,
        )

        assert "Texto base do produto." in merged
        assert "Detalhes adicionais da aplicacao." in merged
        assert merged_again.count("Texto base do produto.") == 1
        assert merged_again.count("Detalhes adicionais da aplicacao.") == 1

    @staticmethod
    def test_aplicar_enriquecimento_heuristico_remove_historico_empresa():
        """Run test aplicar enriquecimento heuristico remove historico empresa in this workflow."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        produto = SimpleNamespace(
            nome_base="Paralama Externo",
            marca="Rodoplast",
            modelo="IV-FD",
            sku="900484",
            ean=None,
            categoria_mapeada="Lataria",
            categoria_original="Lataria",
        )
        dados = {
            "texto_relevante_coletado": (
                "Paralama externo reforcado para linha pesada. "
                "A Uouu iniciou suas atividades no ano de 2015 e atua no mercado."
            ),
        }
        logs = []

        workflow._aplicar_enriquecimento_heuristico(
            db_produto_obj=produto,
            dados_extraidos_agregados=dados,
            log_mensagens=logs,
        )

        assert "iniciou suas atividades" not in dados.get("texto_relevante_coletado", "").lower()
        assert "iniciou suas atividades" not in dados.get("descricao_curta", "").lower()
        assert "iniciou suas atividades" not in dados.get("descricao_detalhada_seo", "").lower()

    @staticmethod
    @pytest.mark.asyncio
    async def test_coletar_de_urls_ignora_html_vazio_texto_fraco_e_fonte_irrelevante():
        """Ignore sources with missing HTML, weak text or irrelevant metadata."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        calls = []

        async def coletar_html(url):
            calls.append(("html", url))
            if url.endswith("1"):
                return None
            return f"<html>{url}</html>"

        def extrair_texto(_html):
            return "texto fraco"

        def extrair_metadados(_html, url):
            return {"nome": f"Fonte {url}", "descricao_curta": "Descricao da fonte"}

        workflow.web_extractor = SimpleNamespace(
            coletar_conteudo_pagina_playwright=coletar_html,
            extrair_texto_principal_com_trafilatura=extrair_texto,
            extrair_metadados_estruturados=extrair_metadados,
            normalizar_dados_de_metadados=lambda value: value,
        )
        workflow.is_meaningful_extracted_text = lambda _text: False
        workflow.metadata_has_minimum_signal = lambda _metadata: True
        workflow.is_source_relevant_for_product = lambda *args, **kwargs: False

        payload = {}
        logs = []
        produto = SimpleNamespace(id=10, nome_base="Reservatorio")

        result = await workflow._coletar_de_urls(
            db_produto_obj=produto,
            urls_a_processar=["https://example.com/1", "https://example.com/2"],
            dados_extraidos_agregados=payload,
            log_mensagens=logs,
            busca_web_disponivel=True,
        )

        assert result is False
        assert payload == {}
        assert len(calls) == 2
        assert any("nao foi possivel obter conteudo html" in item.lower() for item in logs)
        assert any("baixa relevancia" in item.lower() for item in logs)

    @staticmethod
    @pytest.mark.asyncio
    async def test_coletar_de_urls_agrega_payload_e_para_quando_fonte_ja_tem_nome_e_descricao():
        """Aggregate source payload and stop after a strong first source."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        html_calls = []

        async def coletar_html(url):
            html_calls.append(url)
            return f"<html>{url}</html>"

        workflow.web_extractor = SimpleNamespace(
            coletar_conteudo_pagina_playwright=coletar_html,
            extrair_texto_principal_com_trafilatura=lambda _html: (
                "Reservatorio de ar para linha pesada. Material: Aco carbono."
            ),
            extrair_metadados_estruturados=lambda _html, url: {
                "nome": f"Reservatorio Linha Pesada {url[-1]}",
                "descricao_curta": "Reservatorio reforcado para freio pneumático.",
            },
            normalizar_dados_de_metadados=lambda value: value,
        )
        workflow.is_meaningful_extracted_text = lambda text: bool(text)
        workflow.metadata_has_minimum_signal = lambda metadata: bool(metadata.get("nome"))
        workflow.is_source_relevant_for_product = lambda *args, **kwargs: True

        payload = {}
        logs = []
        produto = SimpleNamespace(id=10, nome_base="Reservatorio")

        result = await workflow._coletar_de_urls(
            db_produto_obj=produto,
            urls_a_processar=["https://example.com/1", "https://example.com/2"],
            dados_extraidos_agregados=payload,
            log_mensagens=logs,
            busca_web_disponivel=True,
        )

        assert result is True
        assert html_calls == ["https://example.com/1"]
        assert payload["nome"].startswith("Reservatorio Linha Pesada")
        assert "texto_relevante_coletado" in payload
        assert payload["fontes_web_coletadas"][0]["url"] == "https://example.com/1"
        assert any("dados chave" in item.lower() for item in logs)

    @staticmethod
    @pytest.mark.asyncio
    async def test_executar_llm_retorna_falha_api_externa_quando_provedor_responde_com_erro():
        """Translate LLM provider errors into the expected terminal status."""
        workflow = _TopLevelFunctionSurface._build_workflow()
        async def fake_llm(**kwargs):
            return {"erro_llm": "upstream timeout"}

        workflow.web_extractor = SimpleNamespace(extrair_dados_produto_com_llm=fake_llm)
        produto = SimpleNamespace(nome_base="Reservatorio", dados_brutos_web={})
        user = SimpleNamespace(id=7)
        logs = []

        collected, status = await workflow._executar_llm(
            openai_api_configurada=True,
            db_produto_obj=produto,
            user=user,
            dados_extraidos_agregados={"texto_relevante_coletado": "texto relevante"},
            dados_coletados_de_fontes_web=False,
            log_mensagens=logs,
            status_para_salvar_no_final=_FakeStatus.EM_PROGRESSO,
        )

        assert collected is False
        assert status == _FakeStatus.FALHA_API_EXTERNA
        assert any("erro do llm" in item.lower() for item in logs)

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_registra_falha_de_configuracao_quando_nao_ha_openai_nem_busca():
        """Persist a configuration failure when no external providers are available."""
        session = _FakeSession()
        produto = SimpleNamespace(
            id=88,
            nome_base="Reservatorio",
            fornecedor=None,
            dados_brutos_web={},
            status_enriquecimento_web=_FakeStatus.PENDENTE,
        )
        product_repo = _FakeProductRepository(produto)
        usage_repo = _FakeUsageRepository()
        finalizer_calls = []
        workflow = WebEnrichmentTaskWorkflow(
            logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
            SQLAlchemyError=Exception,
            session_provider=_SessionProviderStub(session),
            user_repository_factory=lambda _session: SimpleNamespace(
                get_user=lambda user_id: SimpleNamespace(id=user_id, chave_openai_pessoal=None)
            ),
            product_repository_factory=lambda _session: product_repo,
            usage_repository_factory=lambda _session: usage_repo,
            models=_FakeModels,
            schemas=_FakeSchemas,
            web_extractor=SimpleNamespace(busca_publica_disponivel=lambda: False),
            settings=SimpleNamespace(OPENAI_API_KEY=None, GOOGLE_CSE_API_KEY=None, GOOGLE_CSE_ID=None),
            json=SimpleNamespace(dumps=lambda *args, **kwargs: "{}"),
            normalize_human_text=lambda value: value,
            build_payload_enriquecimento_visivel=lambda **kwargs: ({}, [], []),
            extrair_dominio_fornecedor=lambda value: value,
            priorizar_urls_para_enriquecimento=lambda **kwargs: ([], []),
            is_meaningful_extracted_text=lambda text: bool(text),
            metadata_has_minimum_signal=lambda metadata: bool(metadata),
            is_source_relevant_for_product=lambda *args, **kwargs: True,
        )

        def fake_finalize(**kwargs):
            finalizer_calls.append(kwargs)
            return kwargs["status_para_salvar_no_final"]

        workflow.finalization_service = SimpleNamespace(apply=fake_finalize)

        await workflow.run(produto_id=88, user_id=7)

        assert len(usage_repo.calls) == 1
        assert usage_repo.calls[0].status == "FALHA"
        assert finalizer_calls[0]["status_para_salvar_no_final"] == _FakeStatus.FALHA_CONFIGURACAO_API_EXTERNA
        assert session.closed is True

    @staticmethod
    @pytest.mark.asyncio
    async def test_run_forca_status_falhou_quando_finalizacao_explode():
        """Force a terminal failure if final persistence crashes in the finally block."""
        session = _FakeSession()
        produto = SimpleNamespace(
            id=99,
            nome_base="Reservatorio",
            fornecedor=None,
            dados_brutos_web={},
            status_enriquecimento_web=_FakeStatus.PENDENTE,
            log_enriquecimento_web=None,
        )
        product_repo = _FakeProductRepository(produto)
        workflow = WebEnrichmentTaskWorkflow(
            logger=SimpleNamespace(info=lambda *a, **k: None, error=lambda *a, **k: None),
            SQLAlchemyError=Exception,
            session_provider=_SessionProviderStub(session),
            user_repository_factory=lambda _session: SimpleNamespace(
                get_user=lambda user_id: SimpleNamespace(id=user_id, chave_openai_pessoal=None)
            ),
            product_repository_factory=lambda _session: product_repo,
            usage_repository_factory=lambda _session: _FakeUsageRepository(),
            models=_FakeModels,
            schemas=_FakeSchemas,
            web_extractor=SimpleNamespace(busca_publica_disponivel=lambda: True),
            settings=SimpleNamespace(OPENAI_API_KEY=None, GOOGLE_CSE_API_KEY="k", GOOGLE_CSE_ID="cx"),
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
            apply=lambda **kwargs: (_ for _ in ()).throw(RuntimeError("persist crash"))
        )

        async def fake_busca_urls(**kwargs):
            return []

        async def fake_coleta_urls(**kwargs):
            return False

        workflow._buscar_urls = fake_busca_urls
        workflow._coletar_de_urls = fake_coleta_urls

        async def fake_execute_llm(**kwargs):
            return False, _FakeStatus.NENHUMA_FONTE_ENCONTRADA

        workflow._executar_llm = fake_execute_llm

        await workflow.run(produto_id=99, user_id=5)

        assert len(product_repo.status_updates) == 1
        assert product_repo.status_updates[0]["produto_id"] == 99
        assert product_repo.status_updates[0]["status"] == _FakeStatus.FALHOU
        assert "falha ao persistir status final" in product_repo.status_updates[0]["log_message"].lower()
        assert session.closed is True


_build_workflow = _TopLevelFunctionSurface._build_workflow
test_aplicar_enriquecimento_heuristico_popula_campos_chave = _TopLevelFunctionSurface.test_aplicar_enriquecimento_heuristico_popula_campos_chave
test_merge_collected_text_acumula_sem_duplicar = _TopLevelFunctionSurface.test_merge_collected_text_acumula_sem_duplicar
test_aplicar_enriquecimento_heuristico_remove_historico_empresa = _TopLevelFunctionSurface.test_aplicar_enriquecimento_heuristico_remove_historico_empresa
test_coletar_de_urls_ignora_html_vazio_texto_fraco_e_fonte_irrelevante = (
    _TopLevelFunctionSurface.test_coletar_de_urls_ignora_html_vazio_texto_fraco_e_fonte_irrelevante
)
test_coletar_de_urls_agrega_payload_e_para_quando_fonte_ja_tem_nome_e_descricao = (
    _TopLevelFunctionSurface.test_coletar_de_urls_agrega_payload_e_para_quando_fonte_ja_tem_nome_e_descricao
)
test_executar_llm_retorna_falha_api_externa_quando_provedor_responde_com_erro = (
    _TopLevelFunctionSurface.test_executar_llm_retorna_falha_api_externa_quando_provedor_responde_com_erro
)
test_run_registra_falha_de_configuracao_quando_nao_ha_openai_nem_busca = (
    _TopLevelFunctionSurface.test_run_registra_falha_de_configuracao_quando_nao_ha_openai_nem_busca
)
test_run_forca_status_falhou_quando_finalizacao_explode = (
    _TopLevelFunctionSurface.test_run_forca_status_falhou_quando_finalizacao_explode
)
