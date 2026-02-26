from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class WebEnrichmentConfigSnapshot:
    openai_user_configurada: bool
    openai_system_configurada: bool
    openai_api_configurada: bool
    google_api_configurada: bool
    busca_publica_fallback: bool
    busca_web_disponivel: bool

    def as_log_line(self) -> str:
        return (
            "Config API: "
            f"openai_user={'sim' if self.openai_user_configurada else 'não'}, "
            f"openai_sistema={'sim' if self.openai_system_configurada else 'não'}, "
            f"google_cse={'sim' if self.google_api_configurada else 'não'}, "
            f"busca_publica={'sim' if self.busca_publica_fallback else 'não'}."
        )


class WebEnrichmentConfigInspector:
    """Inspeciona disponibilidade de provedores externos para enriquecimento."""

    def inspect(self, *, user: Any, settings: Any, web_extractor: Any) -> WebEnrichmentConfigSnapshot:
        openai_user_configurada = bool(getattr(user, "chave_openai_pessoal", None))
        openai_system_configurada = bool(getattr(settings, "OPENAI_API_KEY", None))
        openai_api_configurada = bool(openai_user_configurada or openai_system_configurada)
        google_api_configurada = bool(
            getattr(settings, "GOOGLE_CSE_API_KEY", None)
            and getattr(settings, "GOOGLE_CSE_ID", None)
        )
        busca_publica_fallback = bool(
            getattr(web_extractor, "busca_publica_disponivel", lambda: False)()
        )
        busca_web_disponivel = bool(google_api_configurada or busca_publica_fallback)
        return WebEnrichmentConfigSnapshot(
            openai_user_configurada=openai_user_configurada,
            openai_system_configurada=openai_system_configurada,
            openai_api_configurada=openai_api_configurada,
            google_api_configurada=google_api_configurada,
            busca_publica_fallback=busca_publica_fallback,
            busca_web_disponivel=busca_web_disponivel,
        )


class WebEnrichmentQueryPlanner:
    """Monta termos de busca para maximizar recall com baixo ruído."""

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        return [v for v in dict.fromkeys(v for v in values if v)]

    def build_candidates(
        self,
        *,
        db_produto_obj: Any,
        termos_busca_override: Optional[str],
    ) -> List[str]:
        if termos_busca_override:
            return self._dedupe([termos_busca_override.strip()])

        query_parts: List[str] = [str(getattr(db_produto_obj, "nome_base", "") or "").strip()]
        sku = str(getattr(db_produto_obj, "sku", "") or "").strip()
        if sku:
            query_parts.append(sku)
        ean_raw = str(getattr(db_produto_obj, "ean", "") or "").strip()
        ean_digits = re.sub(r"\D", "", ean_raw)
        if ean_digits and 8 <= len(ean_digits) <= 14:
            query_parts.append(ean_digits)
        query_base = " ".join([part for part in query_parts if part])

        nome_base_clean = str(getattr(db_produto_obj, "nome_base", "") or "").strip()
        fornecedor_obj = getattr(db_produto_obj, "fornecedor", None)
        fornecedor_nome = (
            str(getattr(fornecedor_obj, "nome", "") or "").strip() if fornecedor_obj else ""
        )
        codigo_original = ""
        dados_brutos_web = getattr(db_produto_obj, "dados_brutos_web", None)
        if isinstance(dados_brutos_web, dict):
            codigo_original = str(
                dados_brutos_web.get("codigo_original")
                or dados_brutos_web.get("sku_original")
                or ""
            ).strip()

        query_candidates: List[str] = []
        if query_base:
            query_candidates.append(f"{query_base} especificacoes tecnicas detalhadas")
            query_candidates.append(f"{query_base} ficha tecnica")
        if nome_base_clean:
            query_candidates.append(f"{nome_base_clean} especificacoes tecnicas")
            query_candidates.append(nome_base_clean)
            if fornecedor_nome:
                query_candidates.append(f"{nome_base_clean} {fornecedor_nome}")
            if codigo_original:
                query_candidates.append(f"{nome_base_clean} {codigo_original}")
                query_candidates.append(codigo_original)
        return self._dedupe(query_candidates)


class WebEnrichmentStatusResolver:
    """Resolve status final do enriquecimento com base no que foi coletado."""

    def resolve(
        self,
        *,
        models: Any,
        status_para_salvar_no_final: Any,
        dados_coletados_de_fontes_web: bool,
        openai_api_configurada: bool,
        busca_web_disponivel: bool,
        urls_a_processar: List[str],
    ) -> Any:
        if status_para_salvar_no_final not in {
            models.StatusEnriquecimentoEnum.EM_PROGRESSO,
            models.StatusEnriquecimentoEnum.FALHOU,
        }:
            return status_para_salvar_no_final

        if dados_coletados_de_fontes_web:
            if not openai_api_configurada:
                return models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
            return models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO

        if urls_a_processar:
            return models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        if busca_web_disponivel and not urls_a_processar:
            return models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        if not busca_web_disponivel and not openai_api_configurada:
            return models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
        if not busca_web_disponivel and openai_api_configurada:
            return models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        return models.StatusEnriquecimentoEnum.FALHOU


class WebEnrichmentFinalizationService:
    """Encapsula aplicacao final de status/log/payload no produto enriquecido."""

    def __init__(
        self,
        *,
        normalize_human_text: Any,
        build_payload_enriquecimento_visivel: Any,
        schemas: Any,
        crud_produtos: Any,
        models: Any,
    ) -> None:
        self._normalize_human_text = normalize_human_text
        self._build_payload_enriquecimento_visivel = build_payload_enriquecimento_visivel
        self._schemas = schemas
        self._crud_produtos = crud_produtos
        self._models = models

    def apply(
        self,
        *,
        db: Any,
        db_produto_obj: Any,
        status_para_salvar_no_final: Any,
        dados_extraidos_agregados: Dict[str, Any],
        log_mensagens: List[str],
    ) -> Any:
        if (
            db_produto_obj.status_enriquecimento_web
            == self._models.StatusEnriquecimentoEnum.EM_PROGRESSO
            and status_para_salvar_no_final
            == self._models.StatusEnriquecimentoEnum.EM_PROGRESSO
        ):
            status_para_salvar_no_final = self._models.StatusEnriquecimentoEnum.FALHOU
            log_mensagens.append(
                "ALERTA FINALLY: Status final e do DB eram EM_PROGRESSO, forçando para FALHOU."
            )

        status_valor_str = status_para_salvar_no_final.value
        (
            campos_visiveis_update,
            notas_campos,
            notas_ignoradas,
        ) = self._build_payload_enriquecimento_visivel(
            db_produto_obj=db_produto_obj,
            dados_extraidos_agregados=dados_extraidos_agregados,
        )
        if notas_campos:
            log_mensagens.append(
                "Campos preenchidos no produto a partir do enriquecimento: "
                + ", ".join(notas_campos)
            )
        else:
            log_mensagens.append(
                "Enriquecimento finalizado sem novos campos visíveis para preencher no produto."
            )
        if notas_ignoradas:
            log_mensagens.append(
                "Campos ignorados (mantidos os valores atuais): "
                + ", ".join(notas_ignoradas)
            )

        resumo_aplicacao = {
            "aplicados": notas_campos,
            "ignorados": notas_ignoradas,
        }
        log_mensagens_normalizadas: List[str] = []
        for message in log_mensagens:
            normalized_message = self._normalize_human_text(message)
            if normalized_message:
                log_mensagens_normalizadas.append(normalized_message)

        payload_final_update = self._schemas.ProdutoUpdate(
            **campos_visiveis_update,
            dados_brutos_web=dados_extraidos_agregados,
            status_enriquecimento_web=status_valor_str,
            log_enriquecimento_web={
                "historico_mensagens": log_mensagens_normalizadas,
                "resumo_aplicacao": resumo_aplicacao,
            },
        )
        self._crud_produtos.update_produto(
            db,
            db_produto=db_produto_obj,
            produto_update=payload_final_update,
        )
        log_mensagens.append(
            f"Produto ID {db_produto_obj.id} FINALMENTE atualizado com status: {status_valor_str}."
        )
        return status_para_salvar_no_final
