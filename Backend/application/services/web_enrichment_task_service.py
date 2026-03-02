"""Module web enrichment task service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from Backend.application.services.web_enrichment_components import (
    WebEnrichmentConfigInspector,
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
    WebEnrichmentStatusResolver,
)


class WebEnrichmentTaskRuntime:
    """Class WebEnrichmentTaskRuntime.

    Encapsulates one responsibility in the backend architecture.
    """
    RUNTIME_FIELDS = (
        "logger",
        "SQLAlchemyError",
        "user_repository",
        "product_repository",
        "usage_repository",
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
        user_repository,
        product_repository,
        usage_repository,
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
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.logger = logger
        self.SQLAlchemyError = SQLAlchemyError
        self.user_repository = user_repository
        self.product_repository = product_repository
        self.usage_repository = usage_repository
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
        """Execute apply_overrides.

        This callable is documented to make behavior explicit for readers.
        """
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self


class WebEnrichmentTaskWorkflow:
    """Orquestra o fluxo completo de enriquecimento web com etapas coesas."""

    def __init__(
        self,
        *,
        logger,
        SQLAlchemyError,
        db_session_factory,
        user_repository,
        product_repository,
        usage_repository,
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
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        runtime_obj = WebEnrichmentTaskRuntime(
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            user_repository=user_repository,
            product_repository=product_repository,
            usage_repository=usage_repository,
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
        self._db_session_factory = db_session_factory
        self.logger = runtime_obj.logger
        self.SQLAlchemyError = runtime_obj.SQLAlchemyError
        self.user_repository = runtime_obj.user_repository
        self.product_repository = runtime_obj.product_repository
        self.usage_repository = runtime_obj.usage_repository
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
            product_repository=runtime_obj.product_repository,
            models=runtime_obj.models,
        )

    @staticmethod
    def _resolve_repo(repo_or_cls: Any, session: Session) -> Any:
        """Execute _resolve_repo.

        This callable is documented to make behavior explicit for readers.
        """
        if repo_or_cls is None:
            raise ValueError("repository provider is required")
        if callable(repo_or_cls):
            return repo_or_cls(session)
        return repo_or_cls

    def _load_locked_product(self, session: Session, produto_id: int):
        """Execute _load_locked_product.

        This callable is documented to make behavior explicit for readers.
        """
        product_repo = self._resolve_repo(self.product_repository, session)
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
        """Execute _register_config_failure.

        This callable is documented to make behavior explicit for readers.
        """
        usage_repo = self._resolve_repo(self.usage_repository, session)
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
        """Execute _mark_in_progress.

        This callable is documented to make behavior explicit for readers.
        """
        log_mensagens.append(
            f"Definindo status do produto ID {produto_id} para EM_PROGRESSO no banco."
        )
        db_produto_obj.status_enriquecimento_web = self.models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens}
        session.commit()
        session.refresh(db_produto_obj)

    async def _buscar_urls(self, *, query_candidates: List[str], busca_web_disponivel: bool, log_mensagens: List[str]) -> List[str]:
        """Execute _buscar_urls.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute _coletar_de_urls.

        This callable is documented to make behavior explicit for readers.
        """
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
                if "texto_relevante_coletado" not in dados_extraidos_agregados:
                    dados_extraidos_agregados["texto_relevante_coletado"] = texto_principal
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
        """Execute _executar_llm.

        This callable is documented to make behavior explicit for readers.
        """
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
            if k != "texto_relevante_coletado"
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
        return True, status_para_salvar_no_final

    async def run(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        """Execute run.

        This callable is documented to make behavior explicit for readers.
        """
        db: Optional[Session] = None
        log_mensagens: List[str] = [
            f"INICIANDO tarefa de enriquecimento web (variant=oop) para produto ID: {produto_id}."
        ]

        db_produto_obj = None
        status_original = self.models.StatusEnriquecimentoEnum.PENDENTE
        status_para_salvar_no_final = status_original
        dados_extraidos_agregados: Dict[str, Any] = {}

        try:
            if self._db_session_factory is None:
                raise ValueError("db_session_factory is required for WebEnrichmentTaskWorkflow")
            db = self._db_session_factory()
            db_produto_obj = self._load_locked_product(db, produto_id)
            if not db_produto_obj:
                log_mensagens.append(
                    f"ERRO FATAL PRECOCE: Produto ID {produto_id} nao encontrado."
                )
                self.logger.error(log_mensagens[-1])
                return
            status_original = db_produto_obj.status_enriquecimento_web
        except self.SQLAlchemyError as e_sql_load:
            log_mensagens.append(
                f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}"
            )
            self.logger.error(log_mensagens[-1])
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

        try:
            user_repo = self._resolve_repo(self.user_repository, db)
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
        db_session_factory,
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
        user_repository,
        product_repository,
        usage_repository,
    ):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._deps = {
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "db_session_factory": db_session_factory,
            "user_repository": user_repository,
            "product_repository": product_repository,
            "usage_repository": usage_repository,
            "models": models,
            "schemas": schemas,
            "web_extractor": web_extractor,
            "settings": settings,
            "json": json,
            "re": re,
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
        """Execute execute.

        This callable is documented to make behavior explicit for readers.
        """
        workflow = WebEnrichmentTaskWorkflow(**self._deps)
        await workflow.run(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )
