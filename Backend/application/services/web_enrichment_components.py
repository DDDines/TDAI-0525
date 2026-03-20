"""Document web enrichment components module responsibilities and runtime integration points."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, quote_plus, urlencode, urlparse, urlunparse

from Backend import models
from Backend.core.api_key_validation import looks_like_openai_api_key, normalize_optional_secret
from Backend.infrastructure.repositories.external_credential_repository import (
    ExternalCredentialRepository,
)


@dataclass(frozen=True)
class WebEnrichmentConfigSnapshot:
    """Represent Web Enrichment Config Snapshot and centralize its responsibilities inside this module."""
    openai_user_configurada: bool
    openai_system_configurada: bool
    openai_api_configurada: bool
    google_api_configurada: bool
    busca_publica_fallback: bool
    busca_web_disponivel: bool

    def as_log_line(self) -> str:
        """Execute as log line as part of this module workflow."""
        return (
            "Config API: "
            f"openai_user={'sim' if self.openai_user_configurada else 'nao'}, "
            f"openai_sistema={'sim' if self.openai_system_configurada else 'nao'}, "
            f"google_cse={'sim' if self.google_api_configurada else 'nao'}, "
            f"busca_publica={'sim' if self.busca_publica_fallback else 'nao'}."
        )


@dataclass(frozen=True)
class WebEnrichmentSearchPlan:
    """Represent the full supplier-aware enrichment search plan for a product."""

    query_candidates: List[str]
    direct_candidate_urls: List[str]
    supplier_domain: str


class WebEnrichmentConfigInspector:
    """Inspeciona disponibilidade de provedores externos para enriquecimento."""

    def inspect(
        self,
        *,
        user: Any,
        settings: Any,
        web_extractor: Any,
        db: Any | None = None,
    ) -> WebEnrichmentConfigSnapshot:
        """Execute inspect as part of this module workflow."""
        openai_user_configurada = looks_like_openai_api_key(
            getattr(user, "chave_openai_pessoal", None)
        )
        provider_name = normalize_optional_secret(getattr(settings, "AI_PROVIDER", None))
        lm_studio_configurada = str(provider_name or "").strip().lower() == "lm_studio"
        openai_system_configurada = looks_like_openai_api_key(
            getattr(settings, "OPENAI_API_KEY", None)
        )
        google_api_configurada = bool(
            getattr(settings, "GOOGLE_CSE_API_KEY", None)
            and getattr(settings, "GOOGLE_CSE_ID", None)
        )
        openai_company_or_effective_configurada = False
        if db is not None:
            credential_repo = ExternalCredentialRepository(db)
            openai_effective = credential_repo.resolve_effective_source(
                provider=models.ExternalCredentialProviderEnum.OPENAI,
                current_user=user,
                settings=settings,
            )
            openai_company_or_effective_configurada = bool(
                openai_effective.get("configured")
                and looks_like_openai_api_key(openai_effective.get("secret_value"))
            )
            openai_user_configurada = openai_effective.get("source") == "user" and looks_like_openai_api_key(
                openai_effective.get("secret_value")
            )
            openai_system_configurada = (
                openai_effective.get("source") == "system"
                and looks_like_openai_api_key(openai_effective.get("secret_value"))
            ) or openai_system_configurada

            google_effective = credential_repo.resolve_effective_source(
                provider=models.ExternalCredentialProviderEnum.GOOGLE_CSE,
                current_user=user,
                settings=settings,
            )
            google_api_configurada = bool(
                google_effective.get("configured")
                and google_effective.get("secret_value")
                and (google_effective.get("config_json") or {}).get("search_engine_id")
            )
        if lm_studio_configurada:
            openai_system_configurada = True
        openai_api_configurada = bool(
            openai_user_configurada
            or openai_system_configurada
            or openai_company_or_effective_configurada
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

    _SEARCH_PARAM_KEYS = (
        "q",
        "query",
        "search",
        "s",
        "term",
        "keyword",
        "keywords",
        "busca",
    )

    @staticmethod
    def _dedupe(values: List[str]) -> List[str]:
        """Execute dedupe as part of this module workflow."""
        return [v for v in dict.fromkeys(v for v in values if v)]

    @staticmethod
    def _extract_supplier_domain(site_url: Any) -> str:
        """Extract supplier domain from a configured site URL."""
        raw = str(site_url or "").strip()
        if not raw:
            return ""
        normalized = raw if "://" in raw else f"https://{raw}"
        try:
            parsed = urlparse(normalized)
        except Exception:
            return ""
        return (parsed.netloc or "").lower()

    @staticmethod
    def _domain_variants(supplier_domain: str) -> List[str]:
        """Return the supplier domain with and without the leading www when relevant."""
        domain = str(supplier_domain or "").strip().lower()
        if not domain:
            return []
        variants = [domain]
        if domain.startswith("www."):
            variants.append(domain[4:])
        return list(dict.fromkeys(variants))

    @staticmethod
    def _fold_search_text(value: Any) -> str:
        """Fold accented characters and normalize whitespace for web search terms."""
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = text.encode("ascii", "ignore").decode("ascii")
        text = " ".join(text.split())
        return text.strip()
        return (parsed.netloc or "").lower()

    @staticmethod
    def _extract_code_tokens(value: Any) -> List[str]:
        """Execute extract code tokens as part of this module workflow."""
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
        """Execute dynamic text hints as part of this module workflow."""
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

    def _build_supplier_search_terms(
        self,
        *,
        nome_base_clean: str,
        fornecedor_nome: str,
        codigo_original: str,
        sku: str,
        ean_digits: str,
        code_hints: List[str],
        dynamic_hints: Dict[str, str],
    ) -> List[str]:
        """Build compact search terms to search inside the supplier site first."""
        supplier_terms: List[str] = []
        if nome_base_clean:
            supplier_terms.append(nome_base_clean)
            if codigo_original:
                supplier_terms.append(f"{nome_base_clean} {codigo_original}")
            if sku:
                supplier_terms.append(f"{nome_base_clean} {sku}")
            if fornecedor_nome:
                supplier_terms.append(f"{nome_base_clean} {fornecedor_nome}")
            if dynamic_hints["aplicacao"]:
                supplier_terms.append(f"{nome_base_clean} {dynamic_hints['aplicacao']}")
        for code_hint in code_hints[:4]:
            supplier_terms.append(code_hint)
            if nome_base_clean:
                supplier_terms.append(f"{nome_base_clean} {code_hint}")
        if ean_digits:
            supplier_terms.append(ean_digits)
        return self._dedupe([term.strip() for term in supplier_terms if term.strip()])

    def _build_supplier_scoped_queries(
        self,
        *,
        supplier_domain: str,
        supplier_terms: List[str],
        fornecedor_nome: str,
    ) -> List[str]:
        """Restrict early search queries to the supplier domain before broad web search."""
        if not supplier_domain:
            return []
        queries: List[str] = []
        fornecedor_folded = self._fold_search_text(fornecedor_nome)
        for domain_variant in self._domain_variants(supplier_domain):
            for term in supplier_terms[:6]:
                folded_term = self._fold_search_text(term)
                if folded_term:
                    queries.append(f"site:{domain_variant} {folded_term}")
                    queries.append(f"site:{domain_variant} filetype:pdf {folded_term}")
                    if " " in folded_term:
                        queries.append(f'site:{domain_variant} "{folded_term}"')
                        queries.append(f'site:{domain_variant} filetype:pdf "{folded_term}"')
                if fornecedor_folded and fornecedor_folded.lower() not in folded_term.lower():
                    queries.append(f"site:{domain_variant} {folded_term} {fornecedor_folded}")
                    queries.append(
                        f"site:{domain_variant} filetype:pdf {folded_term} {fornecedor_folded}"
                    )
        return self._dedupe(queries)

    def _build_template_context(
        self,
        *,
        term: str,
        nome_base_clean: str,
        sku: str,
        codigo_original: str,
        ean_digits: str,
        supplier_domain: str,
    ) -> Dict[str, str]:
        """Provide the placeholder context used to render supplier search URLs."""
        encoded_term = quote_plus(term)
        return {
            "{query}": term,
            "{query_encoded}": encoded_term,
            "{termo}": term,
            "{termo_encoded}": encoded_term,
            "{nome_base}": nome_base_clean,
            "{nome_base_encoded}": quote_plus(nome_base_clean),
            "{sku}": sku,
            "{sku_encoded}": quote_plus(sku),
            "{codigo_original}": codigo_original,
            "{codigo_original_encoded}": quote_plus(codigo_original),
            "{ean}": ean_digits,
            "{ean_encoded}": quote_plus(ean_digits),
            "{supplier_domain}": supplier_domain,
        }

    def _render_supplier_search_url(
        self,
        *,
        link_busca_padrao: str,
        term: str,
        nome_base_clean: str,
        sku: str,
        codigo_original: str,
        ean_digits: str,
        supplier_domain: str,
    ) -> Optional[str]:
        """Render a direct supplier search URL from either placeholders or a known query param."""
        raw = str(link_busca_padrao or "").strip()
        if not raw:
            return None
        normalized = raw if "://" in raw else f"https://{raw}"
        context = self._build_template_context(
            term=term,
            nome_base_clean=nome_base_clean,
            sku=sku,
            codigo_original=codigo_original,
            ean_digits=ean_digits,
            supplier_domain=supplier_domain,
        )
        rendered = normalized
        used_template = False
        for placeholder, value in context.items():
            if placeholder in rendered:
                rendered = rendered.replace(placeholder, value)
                used_template = True
        if used_template:
            return rendered

        if rendered.endswith("="):
            return f"{rendered}{quote_plus(term)}"

        try:
            parsed = urlparse(rendered)
        except Exception:
            return None

        if not parsed.netloc:
            return None

        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        updated_items: List[tuple[str, str]] = []
        replaced = False
        for key, value in query_items:
            if not replaced and key.lower() in self._SEARCH_PARAM_KEYS and not value:
                updated_items.append((key, term))
                replaced = True
            else:
                updated_items.append((key, value))

        if replaced:
            parts = list(parsed)
            parts[4] = urlencode(updated_items, doseq=True)
            return urlunparse(parts)
        return None

    def _build_supplier_direct_urls(
        self,
        *,
        link_busca_padrao: str,
        supplier_terms: List[str],
        nome_base_clean: str,
        sku: str,
        codigo_original: str,
        ean_digits: str,
        supplier_domain: str,
    ) -> List[str]:
        """Render supplier search URLs when the supplier provides a search endpoint template."""
        direct_urls: List[str] = []
        for term in supplier_terms[:4]:
            rendered = self._render_supplier_search_url(
                link_busca_padrao=link_busca_padrao,
                term=term,
                nome_base_clean=nome_base_clean,
                sku=sku,
                codigo_original=codigo_original,
                ean_digits=ean_digits,
                supplier_domain=supplier_domain,
            )
            if rendered:
                direct_urls.append(rendered)
        return self._dedupe(direct_urls)

    def build_search_plan(
        self,
        *,
        db_produto_obj: Any,
        termos_busca_override: Optional[str],
    ) -> WebEnrichmentSearchPlan:
        """Build a supplier-aware search plan with domain-first queries and optional direct URLs."""
        fornecedor_obj = getattr(db_produto_obj, "fornecedor", None)
        supplier_domain = self._extract_supplier_domain(
            getattr(fornecedor_obj, "site_url", "") if fornecedor_obj else ""
        )
        link_busca_padrao = (
            str(getattr(fornecedor_obj, "link_busca_padrao", "") or "").strip()
            if fornecedor_obj
            else ""
        )

        if termos_busca_override:
            supplier_terms = [termos_busca_override.strip()]
            return WebEnrichmentSearchPlan(
                query_candidates=self._dedupe(
                    self._build_supplier_scoped_queries(
                        supplier_domain=supplier_domain,
                        supplier_terms=supplier_terms,
                        fornecedor_nome=str(getattr(fornecedor_obj, "nome", "") or "").strip(),
                    )
                    + supplier_terms
                ),
                direct_candidate_urls=self._build_supplier_direct_urls(
                    link_busca_padrao=link_busca_padrao,
                    supplier_terms=supplier_terms,
                    nome_base_clean="",
                    sku="",
                    codigo_original="",
                    ean_digits="",
                    supplier_domain=supplier_domain,
                ),
                supplier_domain=supplier_domain,
            )

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
        supplier_terms = self._build_supplier_search_terms(
            nome_base_clean=nome_base_clean,
            fornecedor_nome=fornecedor_nome,
            codigo_original=codigo_original,
            sku=sku,
            ean_digits=ean_digits,
            code_hints=code_hints,
            dynamic_hints=dynamic_hints,
        )
        supplier_queries = self._build_supplier_scoped_queries(
            supplier_domain=supplier_domain,
            supplier_terms=supplier_terms,
            fornecedor_nome=fornecedor_nome,
        )
        direct_candidate_urls = self._build_supplier_direct_urls(
            link_busca_padrao=link_busca_padrao,
            supplier_terms=supplier_terms,
            nome_base_clean=nome_base_clean,
            sku=sku,
            codigo_original=codigo_original,
            ean_digits=ean_digits,
            supplier_domain=supplier_domain,
        )
        return WebEnrichmentSearchPlan(
            query_candidates=self._dedupe(supplier_queries + query_candidates),
            direct_candidate_urls=direct_candidate_urls,
            supplier_domain=supplier_domain,
        )

    def build_candidates(
        self,
        *,
        db_produto_obj: Any,
        termos_busca_override: Optional[str],
    ) -> List[str]:
        """Build candidates from current inputs and configuration."""
        return self.build_search_plan(
            db_produto_obj=db_produto_obj,
            termos_busca_override=termos_busca_override,
        ).query_candidates


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
        usar_ia: Optional[bool] = None,
    ) -> Any:
        """Execute resolve as part of this module workflow."""
        llm_requested = usar_ia is not False
        if status_para_salvar_no_final not in {
            models.StatusEnriquecimentoEnum.EM_PROGRESSO,
            models.StatusEnriquecimentoEnum.FALHOU,
        }:
            return status_para_salvar_no_final

        if dados_coletados_de_fontes_web:
            if llm_requested and not openai_api_configurada:
                return models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
            return models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO

        if urls_a_processar or busca_web_disponivel or (llm_requested and openai_api_configurada):
            return models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        return models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA


class WebEnrichmentFinalizationService:
    """Encapsula aplicacao final de status/log/payload no produto enriquecido."""

    def __init__(
        self,
        *,
        normalize_human_text: Any,
        build_payload_enriquecimento_visivel: Any,
        schemas: Any,
        models: Any,
        product_repository_factory: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Finalization Service."""
        self._normalize_human_text = normalize_human_text
        self._build_payload_enriquecimento_visivel = build_payload_enriquecimento_visivel
        self._schemas = schemas
        self._product_repository_factory = product_repository_factory
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
        """Execute apply as part of this module workflow."""
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
        payload_rejeitado_por_relevancia = next(
            (
                item
                for item in notas_ignoradas
                if str(item).startswith("validacao_relevancia=")
            ),
            None,
        )
        if (
            payload_rejeitado_por_relevancia
            and not notas_campos
            and status_para_salvar_no_final
            in {
                self._models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO,
                self._models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS,
            }
        ):
            status_para_salvar_no_final = (
                self._models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            )
            log_mensagens.append(
                "Conteudo web coletado, mas descartado pelo validador de relevancia. "
                "Status ajustado para NENHUMA_FONTE_ENCONTRADA."
            )
            status_valor_str = status_para_salvar_no_final.value
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
        product_repo = self._product_repository_factory(db)
        product_repo.update_produto(
            db_produto=db_produto_obj,
            produto_update=payload_final_update,
        )
        log_mensagens.append(
            f"Produto ID {db_produto_obj.id} FINALMENTE atualizado com status: {status_valor_str}."
        )
        return status_para_salvar_no_final
