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
            f"openai_user={'sim' if self.openai_user_configurada else 'nao'}, "
            f"openai_sistema={'sim' if self.openai_system_configurada else 'nao'}, "
            f"google_cse={'sim' if self.google_api_configurada else 'nao'}, "
            f"busca_publica={'sim' if self.busca_publica_fallback else 'nao'}."
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
    """Monta termos de busca para maximizar recall com baixo ruido."""

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        return [v for v in dict.fromkeys(v for v in values if v)]

    @staticmethod
    def _extract_code_tokens(value: Any) -> List[str]:
        text = str(value or "").upper()
        if not text:
            return []
        tokens = re.findall(r"\b[A-Z0-9][A-Z0-9./-]{4,}\b", text)
        filtered: List[str] = []
        for token in tokens:
            compact = re.sub(r"[^A-Z0-9]", "", token)
            if len(compact) < 5:
                continue
            if not any(ch.isdigit() for ch in compact):
                continue
            filtered.append(token)
        return list(dict.fromkeys(filtered))

    @staticmethod
    def _dynamic_text_hints(dynamic_attributes: Any) -> Dict[str, str]:
        hints = {"aplicacao": "", "material": "", "marca": ""}
        if not isinstance(dynamic_attributes, dict):
            return hints

        for key, value in dynamic_attributes.items():
            if value is None:
                continue
            key_norm = re.sub(r"[^a-z0-9]+", "", str(key or "").lower())
            text_value = str(value).strip()
            if not text_value:
                continue
            if not hints["aplicacao"] and ("aplic" in key_norm or "application" in key_norm):
                hints["aplicacao"] = text_value
            elif not hints["material"] and "material" in key_norm:
                hints["material"] = text_value
            elif not hints["marca"] and "marca" in key_norm:
                hints["marca"] = text_value
        return hints

    def build_candidates(
        self,
        *,
        db_produto_obj: Any,
        termos_busca_override: Optional[str],
    ) -> List[str]:
        if termos_busca_override:
            return self._dedupe([termos_busca_override.strip()])

        nome_base_clean = str(getattr(db_produto_obj, "nome_base", "") or "").strip()
        query_parts: List[str] = [nome_base_clean]
        sku = str(getattr(db_produto_obj, "sku", "") or "").strip()
        if sku:
            query_parts.append(sku)
        ean_raw = str(getattr(db_produto_obj, "ean", "") or "").strip()
        ean_digits = re.sub(r"\D", "", ean_raw)
        if ean_digits and 8 <= len(ean_digits) <= 14:
            query_parts.append(ean_digits)
        query_base = " ".join([part for part in query_parts if part])

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
        dynamic_attributes = getattr(db_produto_obj, "dynamic_attributes", None)
        dynamic_hints = self._dynamic_text_hints(dynamic_attributes)

        code_hints: List[str] = []
        if codigo_original:
            code_hints.extend(self._extract_code_tokens(codigo_original))
        if sku:
            code_hints.extend(self._extract_code_tokens(sku))
        if ean_digits:
            code_hints.extend([ean_digits])
        code_hints.extend(self._extract_code_tokens(nome_base_clean))
        if isinstance(dynamic_attributes, dict):
            for key, value in dynamic_attributes.items():
                key_norm = re.sub(r"[^a-z0-9]+", "", str(key or "").lower())
                if any(marker in key_norm for marker in ("id", "codigo", "sku", "ref")):
                    code_hints.extend(self._extract_code_tokens(value))
        code_hints = self._dedupe([code.strip() for code in code_hints])[:6]

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
            if dynamic_hints["aplicacao"]:
                query_candidates.append(f"{nome_base_clean} {dynamic_hints['aplicacao']}")
            if dynamic_hints["material"]:
                query_candidates.append(f"{nome_base_clean} {dynamic_hints['material']}")

        for code_hint in code_hints:
            if nome_base_clean:
                query_candidates.append(f"{nome_base_clean} {code_hint}")
            if fornecedor_nome:
                query_candidates.append(f"{code_hint} {fornecedor_nome}")
            if dynamic_hints["aplicacao"]:
                query_candidates.append(f"{code_hint} {dynamic_hints['aplicacao']}")
            query_candidates.append(f"{code_hint} peca automotiva")

        if dynamic_hints["marca"] and nome_base_clean:
            query_candidates.append(f"{nome_base_clean} {dynamic_hints['marca']}")
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
        models: Any,
        product_repository: Any | None = None,
    ) -> None:
        self._normalize_human_text = normalize_human_text
        self._build_payload_enriquecimento_visivel = build_payload_enriquecimento_visivel
        self._schemas = schemas
        self._product_repository = product_repository
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
                "ALERTA FINALLY: Status final e do DB eram EM_PROGRESSO, forcando para FALHOU."
            )

        status_valor_str = status_para_salvar_no_final.value
        dynamic_before = (
            dict(db_produto_obj.dynamic_attributes)
            if isinstance(getattr(db_produto_obj, "dynamic_attributes", None), dict)
            else {}
        )
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
                "Enriquecimento finalizado sem novos campos visiveis para preencher no produto."
            )
        if notas_ignoradas:
            log_mensagens.append(
                "Campos ignorados (mantidos os valores atuais): "
                + ", ".join(notas_ignoradas)
            )

        applied_details: List[str] = []
        if isinstance(campos_visiveis_update, dict):
            for field_name, new_value in campos_visiveis_update.items():
                if field_name == "dynamic_attributes" and isinstance(new_value, dict):
                    for dyn_key, dyn_value in new_value.items():
                        previous_dyn = dynamic_before.get(dyn_key)
                        if previous_dyn != dyn_value:
                            applied_details.append(
                                f"dynamic.{dyn_key}: {previous_dyn!r} -> {dyn_value!r}"
                            )
                    continue

                previous_value = getattr(db_produto_obj, field_name, None)
                if previous_value != new_value:
                    applied_details.append(
                        f"{field_name}: {previous_value!r} -> {new_value!r}"
                    )

        resumo_aplicacao = {
            "aplicados": notas_campos,
            "ignorados": notas_ignoradas,
            "aplicados_total": len(notas_campos),
            "ignorados_total": len(notas_ignoradas),
            "status_final": status_valor_str,
            "campos_alterados_detalhe": applied_details,
        }
        log_mensagens.append(
            "Resumo de aplicação: "
            f"{resumo_aplicacao['aplicados_total']} aplicado(s), "
            f"{resumo_aplicacao['ignorados_total']} ignorado(s)."
        )
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
        product_repo = self._resolve_product_repository(db=db)
        product_repo.update_produto(
            db_produto=db_produto_obj,
            produto_update=payload_final_update,
        )
        log_mensagens.append(
            f"Produto ID {db_produto_obj.id} FINALMENTE atualizado com status: {status_valor_str}."
        )
        return status_para_salvar_no_final

    def _resolve_product_repository(self, *, db: Any) -> Any:
        if self._product_repository is None:
            raise ValueError("product_repository is required")
        if callable(self._product_repository):
            try:
                return self._product_repository(db)
            except TypeError:
                pass
        return self._product_repository
