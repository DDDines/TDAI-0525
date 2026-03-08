"""Document web enrichment task service module responsibilities and runtime integration points."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from Backend.application.services.service_container import SessionProviderPort
from Backend.application.services.web_enrichment_components import (
    WebEnrichmentConfigInspector,
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
    WebEnrichmentStatusResolver,
)


class WebEnrichmentTaskRuntime:
    """Represent Web Enrichment Task Runtime and centralize its responsibilities inside this module."""
    RUNTIME_FIELDS = (
        "logger",
        "SQLAlchemyError",
        "user_repository_factory",
        "product_repository_factory",
        "usage_repository_factory",
        "models",
        "schemas",
        "web_extractor",
        "settings",
        "json",
        "normalize_human_text",
        "build_payload_enriquecimento_visivel",
        "extrair_dominio_fornecedor",
        "priorizar_urls_para_enriquecimento",
        "is_meaningful_extracted_text",
        "metadata_has_minimum_signal",
        "is_source_relevant_for_product",
    )

    def __init__(
        self,
        *,
        logger,
        SQLAlchemyError,
        user_repository_factory,
        product_repository_factory,
        usage_repository_factory,
        models,
        schemas,
        web_extractor,
        settings,
        json,
        normalize_human_text,
        build_payload_enriquecimento_visivel,
        extrair_dominio_fornecedor,
        priorizar_urls_para_enriquecimento,
        is_meaningful_extracted_text,
        metadata_has_minimum_signal,
        is_source_relevant_for_product,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Task Runtime."""
        self.logger = logger
        self.SQLAlchemyError = SQLAlchemyError
        self.user_repository_factory = user_repository_factory
        self.product_repository_factory = product_repository_factory
        self.usage_repository_factory = usage_repository_factory
        self.models = models
        self.schemas = schemas
        self.web_extractor = web_extractor
        self.settings = settings
        self.json = json
        self.normalize_human_text = normalize_human_text
        self.build_payload_enriquecimento_visivel = build_payload_enriquecimento_visivel
        self.extrair_dominio_fornecedor = extrair_dominio_fornecedor
        self.priorizar_urls_para_enriquecimento = priorizar_urls_para_enriquecimento
        self.is_meaningful_extracted_text = is_meaningful_extracted_text
        self.metadata_has_minimum_signal = metadata_has_minimum_signal
        self.is_source_relevant_for_product = is_source_relevant_for_product

    def apply_overrides(self, runtime: Any) -> "WebEnrichmentTaskRuntime":
        """Execute apply overrides as part of this module workflow."""
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self


class WebEnrichmentTaskWorkflow:
    """Orquestra o fluxo completo de enriquecimento web com etapas coesas."""

    _KEYWORD_STOPWORDS = {
        "com",
        "para",
        "sem",
        "dos",
        "das",
        "nos",
        "nas",
        "uma",
        "uns",
        "umas",
        "que",
        "por",
        "the",
        "and",
        "item",
        "peca",
        "pecas",
        "produto",
        "produtos",
        "linha",
        "detalhes",
        "detalhado",
        "detalhada",
        "tecnica",
        "tecnicas",
        "ficha",
        "mais",
        "menos",
        "sobre",
        "link",
        "http",
        "https",
    }
    _COMPANY_TIMELINE_HINTS = (
        "iniciou suas atividades",
        "iniciou as atividades",
        "fundada em",
        "fundado em",
        "anos de mercado",
        "no mercado desde",
        "atuando desde",
        "historia da empresa",
    )
    _COMPANY_TIMELINE_PATTERN = re.compile(
        r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades(?:\s+no?\s+ano\s+de\s+(?:19|20)\d{2})?)\b",
        re.IGNORECASE,
    )
    _COMPANY_ENTITY_HINT_PATTERN = re.compile(
        r"\b(?:empresa|marca|fabricante|industria|loja|grupo|nos|nossa|historia|tradicao|mercado)\b",
        re.IGNORECASE,
    )

    def __init__(
        self,
        *,
        logger,
        SQLAlchemyError,
        session_provider: SessionProviderPort,
        user_repository_factory,
        product_repository_factory,
        usage_repository_factory,
        models,
        schemas,
        web_extractor,
        settings,
        json,
        normalize_human_text,
        build_payload_enriquecimento_visivel,
        extrair_dominio_fornecedor,
        priorizar_urls_para_enriquecimento,
        is_meaningful_extracted_text,
        metadata_has_minimum_signal,
        is_source_relevant_for_product,
        runtime: Optional[Any] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Task Workflow."""
        runtime_obj = WebEnrichmentTaskRuntime(
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            user_repository_factory=user_repository_factory,
            product_repository_factory=product_repository_factory,
            usage_repository_factory=usage_repository_factory,
            models=models,
            schemas=schemas,
            web_extractor=web_extractor,
            settings=settings,
            json=json,
            normalize_human_text=normalize_human_text,
            build_payload_enriquecimento_visivel=build_payload_enriquecimento_visivel,
            extrair_dominio_fornecedor=extrair_dominio_fornecedor,
            priorizar_urls_para_enriquecimento=priorizar_urls_para_enriquecimento,
            is_meaningful_extracted_text=is_meaningful_extracted_text,
            metadata_has_minimum_signal=metadata_has_minimum_signal,
            is_source_relevant_for_product=is_source_relevant_for_product,
        )
        if runtime is not None:
            runtime_obj.apply_overrides(runtime)

        self._runtime = runtime_obj
        self._session_provider = session_provider
        self.logger = runtime_obj.logger
        self.SQLAlchemyError = runtime_obj.SQLAlchemyError
        self.user_repository_factory = runtime_obj.user_repository_factory
        self.product_repository_factory = runtime_obj.product_repository_factory
        self.usage_repository_factory = runtime_obj.usage_repository_factory
        self.models = runtime_obj.models
        self.schemas = runtime_obj.schemas
        self.web_extractor = runtime_obj.web_extractor
        self.settings = runtime_obj.settings
        self.json = runtime_obj.json
        self.normalize_human_text = runtime_obj.normalize_human_text
        self.extrair_dominio_fornecedor = runtime_obj.extrair_dominio_fornecedor
        self.priorizar_urls_para_enriquecimento = runtime_obj.priorizar_urls_para_enriquecimento
        self.is_meaningful_extracted_text = runtime_obj.is_meaningful_extracted_text
        self.metadata_has_minimum_signal = runtime_obj.metadata_has_minimum_signal
        self.is_source_relevant_for_product = runtime_obj.is_source_relevant_for_product

        self.config_inspector = WebEnrichmentConfigInspector()
        self.query_planner = WebEnrichmentQueryPlanner()
        self.status_resolver = WebEnrichmentStatusResolver()
        self.finalization_service = WebEnrichmentFinalizationService(
            normalize_human_text=runtime_obj.normalize_human_text,
            build_payload_enriquecimento_visivel=runtime_obj.build_payload_enriquecimento_visivel,
            schemas=runtime_obj.schemas,
            product_repository_factory=runtime_obj.product_repository_factory,
            models=runtime_obj.models,
        )

    @staticmethod
    def _compact_text(value: Any, *, max_len: int = 12000) -> str:
        """Normalize extracted text fragments and constrain maximum length."""
        text = " ".join(str(value or "").strip().split())
        if not text:
            return ""
        return text[:max_len]

    @classmethod
    def _looks_like_company_timeline_claim(cls, text: Any) -> bool:
        """Detect company timeline/history claims that are not product facts."""
        compact = " ".join(str(text or "").strip().split())
        if not compact:
            return False

        lowered = compact.lower()
        if any(hint in lowered for hint in cls._COMPANY_TIMELINE_HINTS):
            return True

        if not cls._COMPANY_TIMELINE_PATTERN.search(compact):
            return False

        return bool(cls._COMPANY_ENTITY_HINT_PATTERN.search(compact))

    @classmethod
    def _sanitize_company_timeline_text(cls, value: Any, *, max_len: int = 12000) -> str:
        """Remove unsupported company-history snippets from free text fields."""
        text = cls._compact_text(value, max_len=max_len)
        if not text:
            return ""

        chunks = re.split(r"(?<=[.!?])\s+|[\n\r]+", text)
        filtered_chunks: List[str] = []
        for chunk in chunks:
            clean = " ".join(str(chunk or "").strip().split())
            if len(clean) < 4:
                continue
            if cls._looks_like_company_timeline_claim(clean):
                continue
            filtered_chunks.append(clean)

        if filtered_chunks:
            return cls._compact_text(" ".join(filtered_chunks), max_len=max_len)
        return text

    def _sanitize_aggregated_payload(self, payload: Dict[str, Any]) -> None:
        """Sanitize aggregated enrichment payload in-place."""
        if not isinstance(payload, dict):
            return

        payload["descricao_curta"] = self._sanitize_company_timeline_text(
            payload.get("descricao_curta"),
            max_len=600,
        )
        payload["descricao_detalhada_seo"] = self._sanitize_company_timeline_text(
            payload.get("descricao_detalhada_seo"),
            max_len=1800,
        )
        payload["texto_relevante_coletado"] = self._sanitize_company_timeline_text(
            payload.get("texto_relevante_coletado"),
            max_len=14000,
        )

        bullets = self._coerce_to_list(payload.get("lista_caracteristicas_beneficios_bullets"))
        if bullets:
            filtered_bullets = [
                item
                for item in bullets
                if not self._looks_like_company_timeline_claim(item)
            ]
            payload["lista_caracteristicas_beneficios_bullets"] = filtered_bullets[:6]

        fontes_web = payload.get("fontes_web_coletadas")
        if isinstance(fontes_web, list):
            normalized_sources: List[Dict[str, Any]] = []
            for source in fontes_web:
                if not isinstance(source, dict):
                    continue
                source_copy = dict(source)
                source_copy["descricao_curta"] = self._sanitize_company_timeline_text(
                    source_copy.get("descricao_curta"),
                    max_len=220,
                )
                normalized_sources.append(source_copy)
            payload["fontes_web_coletadas"] = normalized_sources[:8]

    @classmethod
    def _split_sentences(cls, *, text: str, max_items: int, min_len: int = 24) -> List[str]:
        """Extract sentence-like chunks from arbitrary text payloads."""
        items: List[str] = []
        seen = set()
        for fragment in re.split(r"[\n\r]+|(?<=[.!?])\s+", text or ""):
            clean = " ".join(fragment.strip().split()).strip(" -;,.")
            if len(clean) < min_len:
                continue
            if cls._looks_like_company_timeline_claim(clean):
                continue
            normalized = clean.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            items.append(clean)
            if len(items) >= max_items:
                break
        return items

    def _merge_collected_text(self, *, existing_text: Any, new_text: Any, max_len: int = 14000) -> str:
        """Merge text extracted from multiple URLs while avoiding duplicated blocks."""
        existing = self._sanitize_company_timeline_text(existing_text, max_len=max_len)
        incoming = self._sanitize_company_timeline_text(new_text, max_len=max_len)
        if not incoming:
            return existing
        if not existing:
            return incoming
        if incoming in existing:
            return existing
        if existing in incoming:
            return incoming[:max_len]
        merged = f"{existing}\n\n{incoming}"
        return merged[:max_len]

    def _extract_specs_from_text(self, *, text: str, limit: int = 12) -> Dict[str, str]:
        """Extract lightweight key-value specs from free text content."""
        specs: Dict[str, str] = {}
        if not text:
            return specs

        pattern = re.compile(
            r"([A-Za-z0-9][A-Za-z0-9 /_-]{2,45})\s*[:\-]\s*([^\n;]{2,140})"
        )
        for match in pattern.finditer(text):
            key = self._compact_text(match.group(1), max_len=60).strip(" -:;,.")
            value = self._compact_text(match.group(2), max_len=140).strip(" -:;,.")
            if not key or not value:
                continue
            key_low = key.lower()
            if key_low.startswith("http") or key_low in {"www", "sku", "ean"}:
                continue
            if value.lower().startswith("//"):
                continue
            if key_low in specs:
                continue
            specs[key_low] = value
            if len(specs) >= limit:
                break
        return specs

    def _extract_keywords(self, *, source_texts: List[str], limit: int = 10) -> List[str]:
        """Generate SEO-like keyword hints from text and metadata snippets."""
        score_by_token: Dict[str, int] = {}
        for source_text in source_texts:
            for raw_token in re.findall(r"[A-Za-z0-9][A-Za-z0-9./-]{2,}", source_text or ""):
                token = raw_token.strip(".,;:()[]{}<>\"'").lower()
                if len(token) < 3:
                    continue
                if token in self._KEYWORD_STOPWORDS:
                    continue
                if token.isdigit() and len(token) < 4:
                    continue
                if token.startswith("http"):
                    continue
                score_by_token[token] = score_by_token.get(token, 0) + 1

        ranked = sorted(
            score_by_token.items(),
            key=lambda item: (-item[1], -len(item[0]), item[0]),
        )
        return [token for token, _ in ranked[:limit]]

    @staticmethod
    def _coerce_to_list(value: Any) -> List[str]:
        """Normalize list-like and scalar values to a compact list of strings."""
        if isinstance(value, list):
            values = value
        elif value is None:
            values = []
        else:
            values = [value]

        normalized: List[str] = []
        for item in values:
            text = " ".join(str(item or "").strip().split())
            if text:
                normalized.append(text)
        return normalized

    @staticmethod
    def _has_meaningful_llm_value(value: Any) -> bool:
        """Decide whether a metadata value is worth sending to the LLM."""
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return True

    def _aplicar_enriquecimento_heuristico(
        self,
        *,
        db_produto_obj: Any,
        dados_extraidos_agregados: Dict[str, Any],
        log_mensagens: List[str],
    ) -> None:
        """Fill core enrichment fields heuristically when LLM is unavailable or partial."""
        self._sanitize_aggregated_payload(dados_extraidos_agregados)
        texto_base = self._compact_text(
            dados_extraidos_agregados.get("texto_relevante_coletado"),
            max_len=14000,
        )
        has_signal = any(
            self._has_meaningful_llm_value(value)
            for value in dados_extraidos_agregados.values()
        )
        if not texto_base and not has_signal:
            return

        nome_atual = self._compact_text(
            dados_extraidos_agregados.get("nome")
            or dados_extraidos_agregados.get("nome_sugerido_seo"),
            max_len=255,
        )
        if not nome_atual:
            nome_base = self._compact_text(getattr(db_produto_obj, "nome_base", ""), max_len=180)
            marca = self._compact_text(getattr(db_produto_obj, "marca", ""), max_len=80)
            sku = self._compact_text(getattr(db_produto_obj, "sku", ""), max_len=80)
            nome_fallback = " ".join(part for part in [nome_base, marca, sku] if part)
            nome_fallback = self._compact_text(nome_fallback, max_len=255)
            if nome_fallback:
                dados_extraidos_agregados["nome"] = nome_fallback
                log_mensagens.append(
                    "Nome preenchido heuristica/metadata para fortalecer geracao basica."
                )

        descricao_curta = self._compact_text(
            dados_extraidos_agregados.get("descricao_curta"),
            max_len=600,
        )
        if not descricao_curta and texto_base:
            sentencas = self._split_sentences(text=texto_base, max_items=2, min_len=30)
            resumo = " ".join(sentencas).strip() or self._compact_text(texto_base, max_len=420)
            if resumo:
                dados_extraidos_agregados["descricao_curta"] = resumo
                descricao_curta = resumo
                log_mensagens.append(
                    "Descricao curta criada heuristica a partir do texto coletado."
                )

        specs_existentes = dados_extraidos_agregados.get("especificacoes_tecnicas_dict")
        specs_dict: Dict[str, str] = dict(specs_existentes) if isinstance(specs_existentes, dict) else {}
        specs_extraidos = self._extract_specs_from_text(text=texto_base, limit=10)
        specs_alterado = False
        for key_lower, value in specs_extraidos.items():
            if any(existing_key.lower() == key_lower for existing_key in specs_dict.keys()):
                continue
            specs_dict[key_lower.capitalize()] = value
            specs_alterado = True
        if specs_alterado:
            dados_extraidos_agregados["especificacoes_tecnicas_dict"] = specs_dict
            log_mensagens.append(
                f"Especificacoes tecnicas inferidas heuristica: {len(specs_dict)} chave(s)."
            )

        bullets = self._coerce_to_list(
            dados_extraidos_agregados.get("lista_caracteristicas_beneficios_bullets")
        )
        if len(bullets) < 3 and texto_base:
            for sentenca in self._split_sentences(text=texto_base, max_items=6, min_len=28):
                if sentenca.lower() in {item.lower() for item in bullets}:
                    continue
                bullets.append(sentenca)
                if len(bullets) >= 5:
                    break
        if bullets:
            dados_extraidos_agregados["lista_caracteristicas_beneficios_bullets"] = bullets[:6]

        keywords = self._coerce_to_list(
            dados_extraidos_agregados.get("palavras_chave_seo_relevantes_lista")
        )
        keyword_sources = [
            self._compact_text(getattr(db_produto_obj, "nome_base", ""), max_len=220),
            self._compact_text(getattr(db_produto_obj, "marca", ""), max_len=120),
            self._compact_text(getattr(db_produto_obj, "modelo", ""), max_len=120),
            self._compact_text(getattr(db_produto_obj, "sku", ""), max_len=120),
            self._compact_text(getattr(db_produto_obj, "ean", ""), max_len=32),
            self._compact_text(getattr(db_produto_obj, "categoria_mapeada", ""), max_len=120),
            self._compact_text(getattr(db_produto_obj, "categoria_original", ""), max_len=120),
            texto_base,
            descricao_curta,
            " ".join(bullets[:4]),
            " ".join(f"{k} {v}" for k, v in specs_dict.items()),
        ]
        extracted_keywords = self._extract_keywords(source_texts=keyword_sources, limit=12)
        existing_folded = {item.lower() for item in keywords}
        for token in extracted_keywords:
            if token in existing_folded:
                continue
            keywords.append(token)
            existing_folded.add(token)
            if len(keywords) >= 10:
                break
        if keywords:
            dados_extraidos_agregados["palavras_chave_seo_relevantes_lista"] = keywords[:10]

        descricao_detalhada = self._compact_text(
            dados_extraidos_agregados.get("descricao_detalhada_seo"),
            max_len=1800,
        )
        if not descricao_detalhada:
            partes_descricao = []
            if descricao_curta:
                partes_descricao.append(descricao_curta)
            if bullets:
                partes_descricao.append("Destaques: " + "; ".join(bullets[:3]))
            if specs_dict:
                specs_text = "; ".join(
                    f"{key}: {value}" for key, value in list(specs_dict.items())[:4]
                )
                partes_descricao.append("Especificacoes: " + specs_text)
            descricao_composta = self._compact_text(" ".join(partes_descricao), max_len=1800)
            if descricao_composta:
                dados_extraidos_agregados["descricao_detalhada_seo"] = descricao_composta
                log_mensagens.append(
                    "Descricao detalhada seo composta heuristica para uso na geracao."
                )

    def _build_user_repository(self, *, session: Session) -> Any:
        """Instantiate user repository using the injected factory."""
        return self.user_repository_factory(session)

    def _build_product_repository(self, *, session: Session) -> Any:
        """Instantiate product repository using the injected factory."""
        return self.product_repository_factory(session)

    def _build_usage_repository(self, *, session: Session) -> Any:
        """Instantiate usage repository using the injected factory."""
        return self.usage_repository_factory(session)

    @staticmethod
    def _close_session_quietly(session: Optional[Session]) -> None:
        """Close a session object without raising cleanup errors."""
        if session is None:
            return
        try:
            session.close()
        except Exception:
            return

    def _load_locked_product(self, session: Session, produto_id: int):
        """Execute load locked product as part of this module workflow."""
        product_repo = self._build_product_repository(session=session)
        try:
            return product_repo.get_produto_for_update(produto_id=produto_id)
        except AttributeError:
            return product_repo.get_produto(produto_id=produto_id)

    def _register_config_failure(
        self,
        *,
        session,
        user_id: int,
        produto_id: int,
        resposta: str,
    ) -> None:
        """Execute register config failure as part of this module workflow."""
        usage_repo = self._build_usage_repository(session=session)
        usage_repo.create_registro_uso_ia(
            registro_uso=self.schemas.RegistroUsoIACreate(
                user_id=user_id,
                produto_id=produto_id,
                tipo_acao=self.models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                modelo_ia="N/A",
                provedor_ia=None,
                prompt_utilizado="N/A",
                resposta_ia=resposta,
                creditos_consumidos=0,
                status="FALHA",
            ),
        )

    def _mark_in_progress(
        self,
        *,
        session,
        db_produto_obj,
        log_mensagens: List[str],
        produto_id: int,
    ) -> None:
        """Execute mark in progress as part of this module workflow."""
        log_mensagens.append(
            f"Definindo status do produto ID {produto_id} para EM_PROGRESSO no banco."
        )
        db_produto_obj.status_enriquecimento_web = self.models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens}
        session.commit()
        session.refresh(db_produto_obj)

    async def _buscar_urls(self, *, query_candidates: List[str], busca_web_disponivel: bool, log_mensagens: List[str]) -> List[str]:
        """Execute buscar urls as part of this module workflow."""
        if not busca_web_disponivel:
            log_mensagens.append("Busca web pulada: nenhum provedor de busca disponivel.")
            return []

        for query in query_candidates[:4]:
            log_mensagens.append(f"Termo de busca web: '{query}'")
            urls_tentativa = await self.web_extractor.buscar_urls_google(query=query, num_results=3)
            log_mensagens.append(
                f"Busca web retornou {len(urls_tentativa)} URL(s) para '{query}'."
            )
            if urls_tentativa:
                return urls_tentativa

        if query_candidates:
            log_mensagens.append(
                f"Nenhuma URL encontrada para os termos testados ({len(query_candidates)} tentativa(s))."
            )
        else:
            log_mensagens.append("Nenhum termo de busca valido pode ser montado para este produto.")
        return []

    async def _coletar_de_urls(
        self,
        *,
        db_produto_obj,
        urls_a_processar: List[str],
        dados_extraidos_agregados: Dict[str, Any],
        log_mensagens: List[str],
        busca_web_disponivel: bool,
    ) -> bool:
        """Execute coletar de urls as part of this module workflow."""
        dados_coletados_de_fontes_web = False

        if not urls_a_processar and not busca_web_disponivel:
            log_mensagens.append(
                "Nenhuma URL para processar (busca web indisponivel e sem override)."
            )
        elif not urls_a_processar and busca_web_disponivel:
            log_mensagens.append("Nenhuma URL encontrada ou selecionada para processar.")

        for i, url_processar in enumerate(urls_a_processar):
            log_mensagens.append(
                f"Processando URL {i+1}/{len(urls_a_processar)}: {url_processar}"
            )
            html_content = await self.web_extractor.coletar_conteudo_pagina_playwright(url_processar)
            if not html_content:
                log_mensagens.append(
                    f"Nao foi possivel obter conteudo HTML da URL: {url_processar}"
                )
                continue

            texto_principal = self.web_extractor.extrair_texto_principal_com_trafilatura(
                html_content
            )
            metadados_extruct = self.web_extractor.extrair_metadados_estruturados(
                html_content,
                url_processar,
            )
            metadados_normalizados_pagina = self.web_extractor.normalizar_dados_de_metadados(
                metadados_extruct
            )

            if texto_principal and not self.is_meaningful_extracted_text(texto_principal):
                log_mensagens.append(
                    f"Texto descartado por baixa qualidade/erro de pagina para URL: {url_processar}"
                )
                texto_principal = None

            if metadados_normalizados_pagina and not self.metadata_has_minimum_signal(
                metadados_normalizados_pagina
            ):
                log_mensagens.append(
                    f"Metadados descartados por baixa qualidade para URL: {url_processar}"
                )
                metadados_normalizados_pagina = {}

            if metadados_normalizados_pagina:
                self._sanitize_aggregated_payload(metadados_normalizados_pagina)

            texto_principal = self._sanitize_company_timeline_text(
                texto_principal,
                max_len=14000,
            )

            nome_fonte = metadados_normalizados_pagina.get("nome")
            descricao_fonte = metadados_normalizados_pagina.get("descricao_curta") or (
                texto_principal[:600] if texto_principal else ""
            )
            if not self.is_source_relevant_for_product(
                db_produto_obj,
                source_name=nome_fonte,
                source_desc=descricao_fonte,
                source_url=url_processar,
            ):
                log_mensagens.append(
                    f"URL descartada por baixa relevancia para o produto: {url_processar}"
                )
                continue

            if metadados_normalizados_pagina:
                log_mensagens.append(
                    "Metadados normalizados extraidos da URL "
                    f"{url_processar}: "
                    f"{self.json.dumps(metadados_normalizados_pagina, indent=2, ensure_ascii=False)}"
                )
                dados_extraidos_agregados.update(metadados_normalizados_pagina)
                dados_coletados_de_fontes_web = True

            if texto_principal:
                log_mensagens.append(
                    "Texto principal extraido da URL "
                    f"{url_processar} (primeiros 300 chars): {texto_principal[:300]}"
                )
                dados_extraidos_agregados["texto_relevante_coletado"] = self._merge_collected_text(
                    existing_text=dados_extraidos_agregados.get("texto_relevante_coletado"),
                    new_text=texto_principal,
                    max_len=14000,
                )
                fontes_web = dados_extraidos_agregados.get("fontes_web_coletadas")
                if not isinstance(fontes_web, list):
                    fontes_web = []
                if url_processar not in {str(item.get("url", "")) for item in fontes_web if isinstance(item, dict)}:
                    fontes_web.append(
                        {
                            "url": url_processar,
                            "nome": self._compact_text(
                                metadados_normalizados_pagina.get("nome"),
                                max_len=160,
                            ),
                            "descricao_curta": self._compact_text(
                                metadados_normalizados_pagina.get("descricao_curta"),
                                max_len=220,
                            ),
                        }
                    )
                    dados_extraidos_agregados["fontes_web_coletadas"] = fontes_web[:8]
                dados_coletados_de_fontes_web = True

            if metadados_normalizados_pagina.get("nome") and metadados_normalizados_pagina.get(
                "descricao_curta"
            ):
                log_mensagens.append(
                    f"Dados chave (nome, descricao) encontrados em {url_processar}. "
                    "Considerando suficiente desta URL."
                )
                break

        return dados_coletados_de_fontes_web

    async def _executar_llm(
        self,
        *,
        openai_api_configurada: bool,
        db_produto_obj,
        user,
        dados_extraidos_agregados: Dict[str, Any],
        dados_coletados_de_fontes_web: bool,
        log_mensagens: List[str],
        status_para_salvar_no_final,
    ) -> tuple[bool, Any]:
        """Execute executar llm as part of this module workflow."""
        self._sanitize_aggregated_payload(dados_extraidos_agregados)
        if not openai_api_configurada:
            log_mensagens.append("LLM nao foi chamado pois a API OpenAI nao esta configurada.")
            return dados_coletados_de_fontes_web, status_para_salvar_no_final

        campos_desejados_llm = [
            "nome_sugerido_seo",
            "descricao_detalhada_seo",
            "lista_caracteristicas_beneficios_bullets",
            "especificacoes_tecnicas_dict",
            "palavras_chave_seo_relevantes_lista",
        ]
        texto_para_llm = dados_extraidos_agregados.get("texto_relevante_coletado")
        if not texto_para_llm and isinstance(db_produto_obj.dados_brutos_web, dict):
            texto_para_llm = self.json.dumps(
                db_produto_obj.dados_brutos_web.get(
                    "dados_brutos_originais",
                    db_produto_obj.dados_brutos_web,
                ),
                ensure_ascii=False,
            )

        metadados_para_llm = {
            k: v
            for k, v in dados_extraidos_agregados.items()
            if k != "texto_relevante_coletado" and self._has_meaningful_llm_value(v)
        }

        if not texto_para_llm and not metadados_para_llm:
            log_mensagens.append("Nenhum texto ou metadado suficiente para enviar ao LLM.")
            return dados_coletados_de_fontes_web, status_para_salvar_no_final

        log_mensagens.append("Iniciando extracao/geracao com LLM.")
        dados_do_llm = await self.web_extractor.extrair_dados_produto_com_llm(
            texto_pagina=texto_para_llm,
            metadados_normalizados=metadados_para_llm,
            campos_desejados=campos_desejados_llm,
            produto_nome_base=db_produto_obj.nome_base,
            user=user,
        )
        if not dados_do_llm:
            log_mensagens.append(
                "LLM nao retornou dados ou ocorreu erro nao capturado explicitamente."
            )
            return dados_coletados_de_fontes_web, status_para_salvar_no_final

        log_mensagens.append(
            f"Dados recebidos do LLM: {self.json.dumps(dados_do_llm, indent=2, ensure_ascii=False)}"
        )
        if "erro_llm" in dados_do_llm or "erro_llm_inesperado" in dados_do_llm:
            log_mensagens.append(
                "ERRO do LLM: "
                f"{dados_do_llm.get('erro_llm') or dados_do_llm.get('erro_llm_inesperado')}"
            )
            if not dados_coletados_de_fontes_web:
                status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA
            return dados_coletados_de_fontes_web, status_para_salvar_no_final

        dados_extraidos_agregados.update(dados_do_llm)
        self._sanitize_aggregated_payload(dados_extraidos_agregados)
        return True, status_para_salvar_no_final

    async def run(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        """Execute run as part of this module workflow."""
        db: Optional[Session] = None
        log_mensagens: List[str] = [
            f"INICIANDO tarefa de enriquecimento web (variant=oop) para produto ID: {produto_id}."
        ]

        db_produto_obj = None
        status_original = self.models.StatusEnriquecimentoEnum.PENDENTE
        status_para_salvar_no_final = status_original
        dados_extraidos_agregados: Dict[str, Any] = {}

        try:
            if self._session_provider is None:
                raise ValueError("session_provider is required for WebEnrichmentTaskWorkflow")
            db = self._session_provider.open_session()
            db_produto_obj = self._load_locked_product(db, produto_id)
            if not db_produto_obj:
                log_mensagens.append(
                    f"ERRO FATAL PRECOCE: Produto ID {produto_id} nao encontrado."
                )
                self.logger.error(log_mensagens[-1])
                self._close_session_quietly(db)
                return
            status_original = db_produto_obj.status_enriquecimento_web
        except self.SQLAlchemyError as e_sql_load:
            log_mensagens.append(
                f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}"
            )
            self.logger.error(log_mensagens[-1])
            self._close_session_quietly(db)
            return

        status_para_salvar_no_final = status_original
        if status_original == self.models.StatusEnriquecimentoEnum.EM_PROGRESSO:
            log_mensagens.append(
                "AVISO: Produto "
                f"{produto_id} encontrado como EM_PROGRESSO no inicio. "
                "Considerando como PENDENTE para esta execucao."
            )
            status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.PENDENTE

        if isinstance(db_produto_obj.dados_brutos_web, dict):
            dados_extraidos_agregados = db_produto_obj.dados_brutos_web.copy()
            self._sanitize_aggregated_payload(dados_extraidos_agregados)

        try:
            user_repo = self._build_user_repository(session=db)
            user = user_repo.get_user(user_id=user_id)
            if not user:
                log_mensagens.append(f"ERRO FATAL: Usuario ID {user_id} nao encontrado.")
                status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.FALHOU
                return

            config_snapshot = self.config_inspector.inspect(
                user=user,
                settings=self.settings,
                web_extractor=self.web_extractor,
            )
            openai_api_configurada = config_snapshot.openai_api_configurada
            google_api_configurada = config_snapshot.google_api_configurada
            busca_publica_fallback = config_snapshot.busca_publica_fallback
            busca_web_disponivel = config_snapshot.busca_web_disponivel
            log_mensagens.append(config_snapshot.as_log_line())

            if not openai_api_configurada and not busca_web_disponivel:
                log_mensagens.append(
                    "AVISO CRITICO: Sem OpenAI e sem mecanismo de busca web disponivel. "
                    "Configure OPENAI_API_KEY (ou chave pessoal do usuario) e/ou Google CSE."
                )
                status_para_salvar_no_final = (
                    self.models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
                )
                self._register_config_failure(
                    session=db,
                    user_id=user.id,
                    produto_id=produto_id,
                    resposta="Falha: Configuracoes de API externas ausentes.",
                )
                return

            if not google_api_configurada and busca_publica_fallback:
                log_mensagens.append(
                    "Google CSE nao configurado. Usando fallback de busca publica sem API key."
                )

            if not openai_api_configurada:
                log_mensagens.append(
                    "AVISO: Chave API OpenAI nao configurada. Enriquecimento via LLM sera pulado. "
                    "Outras coletas de dados (Google, metadados) tentarao prosseguir."
                )
                self._register_config_failure(
                    session=db,
                    user_id=user.id,
                    produto_id=produto_id,
                    resposta="Falha Parcial: Chave API OpenAI nao configurada para LLM.",
                )

            self._mark_in_progress(
                session=db,
                db_produto_obj=db_produto_obj,
                log_mensagens=log_mensagens,
                produto_id=produto_id,
            )
            status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.FALHOU

            query_candidates = self.query_planner.build_candidates(
                db_produto_obj=db_produto_obj,
                termos_busca_override=termos_busca_override,
            )
            urls_encontradas_brutas = await self._buscar_urls(
                query_candidates=query_candidates,
                busca_web_disponivel=busca_web_disponivel,
                log_mensagens=log_mensagens,
            )

            fornecedor_domain = self.extrair_dominio_fornecedor(
                db_produto_obj.fornecedor.site_url
                if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url
                else ""
            )
            urls_a_processar, urls_scored = self.priorizar_urls_para_enriquecimento(
                db_produto_obj=db_produto_obj,
                urls_candidatas=urls_encontradas_brutas,
                fornecedor_domain=fornecedor_domain,
                max_urls=4,
            )

            if urls_scored:
                ranking_log = ", ".join([f"{score}:{url}" for url, score in urls_scored[:6]])
                log_mensagens.append(f"Ranking de URLs por relevancia: {ranking_log}")
            elif urls_encontradas_brutas:
                log_mensagens.append(
                    "URLs encontradas, mas descartadas por baixa relevancia/sinal de tracking."
                )

            dados_coletados_de_fontes_web = await self._coletar_de_urls(
                db_produto_obj=db_produto_obj,
                urls_a_processar=urls_a_processar,
                dados_extraidos_agregados=dados_extraidos_agregados,
                log_mensagens=log_mensagens,
                busca_web_disponivel=busca_web_disponivel,
            )
            self._aplicar_enriquecimento_heuristico(
                db_produto_obj=db_produto_obj,
                dados_extraidos_agregados=dados_extraidos_agregados,
                log_mensagens=log_mensagens,
            )

            (
                dados_coletados_de_fontes_web,
                status_para_salvar_no_final,
            ) = await self._executar_llm(
                openai_api_configurada=openai_api_configurada,
                db_produto_obj=db_produto_obj,
                user=user,
                dados_extraidos_agregados=dados_extraidos_agregados,
                dados_coletados_de_fontes_web=dados_coletados_de_fontes_web,
                log_mensagens=log_mensagens,
                status_para_salvar_no_final=status_para_salvar_no_final,
            )

            status_para_salvar_no_final = self.status_resolver.resolve(
                models=self.models,
                status_para_salvar_no_final=status_para_salvar_no_final,
                dados_coletados_de_fontes_web=dados_coletados_de_fontes_web,
                openai_api_configurada=openai_api_configurada,
                busca_web_disponivel=busca_web_disponivel,
                urls_a_processar=urls_a_processar,
            )
            log_mensagens.append(
                "Processamento principal concluido. "
                f"Status determinado internamente: {status_para_salvar_no_final.value}"
            )
        except Exception as e_main_try:
            import traceback

            error_full = traceback.format_exc()
            log_mensagens.append(
                f"ERRO CRITICO INESPERADO NO PROCESSO: {str(e_main_try)}. Trace: {error_full}"
            )
            status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.FALHOU
            self.logger.error(
                "ERRO CRITICO INESPERADO na tarefa de enriquecimento para produto ID %s: %s",
                produto_id,
                error_full,
            )
        finally:
            if db_produto_obj:
                try:
                    status_para_salvar_no_final = self.finalization_service.apply(
                        db=db,
                        db_produto_obj=db_produto_obj,
                        status_para_salvar_no_final=status_para_salvar_no_final,
                        dados_extraidos_agregados=dados_extraidos_agregados,
                        log_mensagens=log_mensagens,
                    )
                    self.logger.info(
                        "INFO (web_enrichment.py _finally_): Produto ID %s status ATUALIZADO PARA %s.",
                        produto_id,
                        status_para_salvar_no_final.value,
                    )
                except Exception as e_final_update:
                    self.logger.error(
                        "ERRO CRITICO ao tentar atualizacao final do produto %s no finally: %s",
                        produto_id,
                        e_final_update,
                    )
                    try:
                        fallback_repo = self._build_product_repository(session=db)
                        fallback_repo.set_web_enrichment_status(
                            produto_id=produto_id,
                            status=self.models.StatusEnriquecimentoEnum.FALHOU,
                            log_message=(
                                "Falha ao persistir status final do enriquecimento: "
                                f"{e_final_update}"
                            ),
                        )
                        status_para_salvar_no_final = self.models.StatusEnriquecimentoEnum.FALHOU
                    except Exception as fallback_exc:
                        self.logger.error(
                            "ERRO CRITICO ao forcar status terminal de falha para produto %s: %s",
                            produto_id,
                            fallback_exc,
                        )

            final_status_value_print = status_para_salvar_no_final.value
            self.logger.info(
                "Finalizando tarefa de enriquecimento (variant=oop) para produto ID: %s. "
                "Status determinado para gravacao: %s",
                produto_id,
                final_status_value_print,
            )
            if db:
                db.close()
class WebEnrichmentTaskService:
    """Service OO para executar enriquecimento web."""

    def __init__(
        self,
        *,
        logger,
        SQLAlchemyError,
        session_provider: SessionProviderPort,
        models,
        schemas,
        web_extractor,
        settings,
        json,
        re,
        normalize_human_text,
        build_payload_enriquecimento_visivel,
        extrair_dominio_fornecedor,
        priorizar_urls_para_enriquecimento,
        is_meaningful_extracted_text,
        metadata_has_minimum_signal,
        is_source_relevant_for_product,
        user_repository_factory,
        product_repository_factory,
        usage_repository_factory,
    ):
        """Initialize injected dependencies and runtime configuration for Web Enrichment Task Service."""
        self._deps = {
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "session_provider": session_provider,
            "user_repository_factory": user_repository_factory,
            "product_repository_factory": product_repository_factory,
            "usage_repository_factory": usage_repository_factory,
            "models": models,
            "schemas": schemas,
            "web_extractor": web_extractor,
            "settings": settings,
            "json": json,
            "normalize_human_text": normalize_human_text,
            "build_payload_enriquecimento_visivel": build_payload_enriquecimento_visivel,
            "extrair_dominio_fornecedor": extrair_dominio_fornecedor,
            "priorizar_urls_para_enriquecimento": priorizar_urls_para_enriquecimento,
            "is_meaningful_extracted_text": is_meaningful_extracted_text,
            "metadata_has_minimum_signal": metadata_has_minimum_signal,
            "is_source_relevant_for_product": is_source_relevant_for_product,
        }

    async def execute(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ):
        """Execute execute as part of this module workflow."""
        workflow = WebEnrichmentTaskWorkflow(**self._deps)
        await workflow.run(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )
