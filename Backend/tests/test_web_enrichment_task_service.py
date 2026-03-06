"""Module test web enrichment task service.

Contains backend logic related to test web enrichment task service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskWorkflow,
)


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
            models=SimpleNamespace(StatusEnriquecimentoEnum=SimpleNamespace()),
            schemas=SimpleNamespace(ProdutoUpdate=lambda **kwargs: kwargs),
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


_build_workflow = _TopLevelFunctionSurface._build_workflow
test_aplicar_enriquecimento_heuristico_popula_campos_chave = _TopLevelFunctionSurface.test_aplicar_enriquecimento_heuristico_popula_campos_chave
test_merge_collected_text_acumula_sem_duplicar = _TopLevelFunctionSurface.test_merge_collected_text_acumula_sem_duplicar
test_aplicar_enriquecimento_heuristico_remove_historico_empresa = _TopLevelFunctionSurface.test_aplicar_enriquecimento_heuristico_remove_historico_empresa
