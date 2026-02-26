from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from Backend.application.services.web_enrichment_components import (
    WebEnrichmentConfigInspector,
    WebEnrichmentFinalizationService,
    WebEnrichmentQueryPlanner,
    WebEnrichmentStatusResolver,
)
from Backend.application.services.shadow_result_comparator import ShadowResultComparator


_shadow_result_comparator = ShadowResultComparator()


async def run_web_enrichment_task(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None,
    *,
    logger,
    SQLAlchemyError,
    crud_users,
    crud_produtos,
    crud,
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
    pipeline_variant: str = "unknown",
):
    config_inspector = WebEnrichmentConfigInspector()
    query_planner = WebEnrichmentQueryPlanner()
    status_resolver = WebEnrichmentStatusResolver()
    finalization_service = WebEnrichmentFinalizationService(
        normalize_human_text=normalize_human_text,
        build_payload_enriquecimento_visivel=build_payload_enriquecimento_visivel,
        schemas=schemas,
        crud_produtos=crud_produtos,
        models=models,
    )

    db: Optional[Session] = None
    log_mensagens: List[str] = [
        f"INICIANDO tarefa de enriquecimento web (variant={pipeline_variant}) para produto ID: {produto_id}."
    ]
    
    db_produto_obj: Optional[models.Produto] = None
    status_original_do_produto_no_inicio_da_tarefa: models.StatusEnriquecimentoEnum = (
        models.StatusEnriquecimentoEnum.PENDENTE
    )

    try:
        db = db_session_factory()
        query = db.query(models.Produto).filter(models.Produto.id == produto_id)
        engine = db.get_bind()
        dialect_name = engine.dialect.name if engine and engine.dialect else None
        if dialect_name == "sqlite":
            db_produto_obj = query.first()
        else:
            db_produto_obj = query.with_for_update().first()
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} nao encontrado.")
            logger.error(log_mensagens[-1])
            return
        
        status_original_do_produto_no_inicio_da_tarefa = db_produto_obj.status_enriquecimento_web
        # Nao mudamos o status para EM_PROGRESSO aqui ainda.

    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(
            f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}"
        )
        logger.error(log_mensagens[-1])
        return

    # Esta sera a variavel que controlara o status a ser salvo no final.
    # Inicializa com o status que o produto tinha antes da tarefa comecar,
    # ou FALHOU se algo der muito errado antes mesmo de verificarmos as APIs.
    status_para_salvar_no_final: models.StatusEnriquecimentoEnum = status_original_do_produto_no_inicio_da_tarefa
    
    # Se o status original ja era EM_PROGRESSO por algum motivo (ex: tarefa anterior falhou ao limpar),
    # e melhor considera-lo como PENDENTE para esta nova execucao ou FALHOU para evitar loops.
    # Para simplificar, se estava EM_PROGRESSO, vamos reverter para PENDENTE como base para esta tentativa.
    if status_original_do_produto_no_inicio_da_tarefa == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
        log_mensagens.append(f"AVISO: Produto {produto_id} encontrado como EM_PROGRESSO no inicio. Considerando como PENDENTE para esta execucao.")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.PENDENTE


    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos_web.copy() if isinstance(db_produto_obj.dados_brutos_web, dict) else {}
    
    try:
        user = crud_users.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuario ID {user_id} nao encontrado.")
            # Define um status de falha se o usuario nao for encontrado.
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
            return # O finally cuidara da atualizacao do produto

        # Verifica configuracoes criticas ANTES de mudar para EM_PROGRESSO
        config_snapshot = config_inspector.inspect(
            user=user,
            settings=settings,
            web_extractor=web_extractor,
        )
        openai_api_configurada = config_snapshot.openai_api_configurada
        google_api_configurada = config_snapshot.google_api_configurada
        busca_publica_fallback = config_snapshot.busca_publica_fallback
        busca_web_disponivel = config_snapshot.busca_web_disponivel
        log_mensagens.append(config_snapshot.as_log_line())

        # Sem OpenAI e sem mecanismo de busca web, nao ha como enriquecer.
        if not openai_api_configurada and not busca_web_disponivel:
            log_mensagens.append(
                "AVISO CRITICO: Sem OpenAI e sem mecanismo de busca web disponivel. "
                "Configure OPENAI_API_KEY (ou chave pessoal do usuario) e/ou Google CSE."
            )
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            # Opcional: Registrar uso da IA para falha de configuracao
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A",
                    resposta_ia="Falha: Configuracoes de API externas ausentes.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            return # Vai para o finally para salvar este status

        if not google_api_configurada and busca_publica_fallback:
            log_mensagens.append(
                "Google CSE nao configurado. Usando fallback de busca publica sem API key."
            )

        # Se especificamente a OpenAI nao esta configurada, mas a Google pode estar.
        # O enriquecimento LLM nao sera possivel, mas a busca e extracao de metadados sim.
        if not openai_api_configurada:
            log_mensagens.append("AVISO: Chave API OpenAI nao configurada. Enriquecimento via LLM sera pulado. Outras coletas de dados (Google, metadados) tentarao prosseguir.")
            # Nao definimos status_para_salvar_no_final como FALHA_CONFIGURACAO_API_EXTERNA ainda,
            # pois a busca Google e extracao de metadados podem funcionar.
            # O status final dependera se essas outras etapas coletam algo.
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A - Config OpenAI pendente para LLM",
                    resposta_ia="Falha Parcial: Chave API OpenAI nao configurada para LLM.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            # A tarefa continua para tentar coletar dados de outras fontes

        # ----- AGORA, definimos o status para EM_PROGRESSO no banco -----
        # Isso sinaliza que as verificacoes iniciais passaram e o trabalho real comecou.
        log_mensagens.append(f"Definindo status do produto ID {produto_id} para EM_PROGRESSO no banco.")
        db_produto_obj.status_enriquecimento_web = models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens} # Salva o log inicial
        db.commit()
        db.refresh(db_produto_obj)
        
        # O status_para_salvar_no_final sera o que resultar do processamento.
        # Se tudo correr bem, sera CONCLUIDO_SUCESSO. Se houver problemas, sera outro.
        # Por default, se nada mudar, consideramos uma falha generica ao final do try.
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        
        # ----- Inicio do Processamento Principal -----
        query_candidates = query_planner.build_candidates(
            db_produto_obj=db_produto_obj,
            termos_busca_override=termos_busca_override,
        )

        urls_encontradas_brutas: List[str] = []
        if busca_web_disponivel:
            for query in query_candidates[:4]:
                log_mensagens.append(f"Termo de busca web: '{query}'")
                urls_tentativa = await web_extractor.buscar_urls_google(query=query, num_results=3)
                log_mensagens.append(
                    f"Busca web retornou {len(urls_tentativa)} URL(s) para '{query}'."
                )
                if urls_tentativa:
                    urls_encontradas_brutas = urls_tentativa
                    break

            if not urls_encontradas_brutas:
                if query_candidates:
                    log_mensagens.append(
                        f"Nenhuma URL encontrada para os termos testados ({len(query_candidates)} tentativa(s))."
                    )
                else:
                    log_mensagens.append(
                        "Nenhum termo de busca valido pode ser montado para este produto."
                    )
        else:
            log_mensagens.append("Busca web pulada: nenhum provedor de busca disponivel.")
        fornecedor_domain = extrair_dominio_fornecedor(
            db_produto_obj.fornecedor.site_url
            if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url
            else ""
        )
        urls_a_processar, urls_scored = priorizar_urls_para_enriquecimento(
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
        dados_coletados_de_fontes_web = False # Flag para saber se algo foi coletado da web

        if not urls_a_processar and not busca_web_disponivel:
            log_mensagens.append("Nenhuma URL para processar (busca web indisponivel e sem override).")
            # Sem busca web, o LLM ainda pode tentar com dados brutos.
        elif not urls_a_processar and busca_web_disponivel:
            log_mensagens.append("Nenhuma URL encontrada ou selecionada para processar.")
            # Mesmo sem URLs, o LLM ainda pode tentar com dados brutos.

        for i, url_processar in enumerate(urls_a_processar):
            log_mensagens.append(f"Processando URL {i+1}/{len(urls_a_processar)}: {url_processar}")
            html_content = await web_extractor.coletar_conteudo_pagina_playwright(url_processar)
            if not html_content:
                log_mensagens.append(f"Nao foi possivel obter conteudo HTML da URL: {url_processar}")
                continue # Tenta a proxima URL

            texto_principal = web_extractor.extrair_texto_principal_com_trafilatura(html_content)
            metadados_extruct = web_extractor.extrair_metadados_estruturados(html_content, url_processar)
            metadados_normalizados_pagina = web_extractor._normalizar_dados_de_metadados(metadados_extruct)

            if texto_principal and not is_meaningful_extracted_text(texto_principal):
                log_mensagens.append(
                    f"Texto descartado por baixa qualidade/erro de pagina para URL: {url_processar}"
                )
                texto_principal = None

            if metadados_normalizados_pagina and not metadata_has_minimum_signal(metadados_normalizados_pagina):
                log_mensagens.append(
                    f"Metadados descartados por baixa qualidade para URL: {url_processar}"
                )
                metadados_normalizados_pagina = {}

            nome_fonte = metadados_normalizados_pagina.get("nome")
            descricao_fonte = metadados_normalizados_pagina.get("descricao_curta") or (texto_principal[:600] if texto_principal else "")
            if not is_source_relevant_for_product(
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
                log_mensagens.append(f"Metadados normalizados extraidos da URL {url_processar}: {json.dumps(metadados_normalizados_pagina, indent=2, ensure_ascii=False)}")
                dados_extraidos_agregados.update(metadados_normalizados_pagina) # Atualiza com prioridade para novos dados
                dados_coletados_de_fontes_web = True
            
            if texto_principal:
                log_mensagens.append(f"Texto principal extraido da URL {url_processar} (primeiros 300 chars): {texto_principal[:300]}")
                # Guarda o texto da primeira pagina processada com sucesso para possivel uso pelo LLM
                if "texto_relevante_coletado" not in dados_extraidos_agregados:
                    dados_extraidos_agregados["texto_relevante_coletado"] = texto_principal
                dados_coletados_de_fontes_web = True
            
            # Se ja temos dados suficientes de metadados e texto, podemos parar antes
            if metadados_normalizados_pagina.get("nome") and metadados_normalizados_pagina.get("descricao_curta"):
                log_mensagens.append(f"Dados chave (nome, descricao) encontrados em {url_processar}. Considerando suficiente desta URL.")
                break 
        
        # Etapa de enriquecimento com LLM, se configurado
        if openai_api_configurada:
            campos_desejados_llm = [
                "nome_sugerido_seo", "descricao_detalhada_seo", "lista_caracteristicas_beneficios_bullets",
                "especificacoes_tecnicas_dict", "palavras_chave_seo_relevantes_lista"
            ]
            texto_para_llm = dados_extraidos_agregados.get("texto_relevante_coletado") # Usa o texto coletado
            if not texto_para_llm and isinstance(db_produto_obj.dados_brutos_web, dict): # Fallback para dados brutos se nenhum texto web
                texto_para_llm = json.dumps(db_produto_obj.dados_brutos_web.get("dados_brutos_originais", db_produto_obj.dados_brutos_web), ensure_ascii=False)
            
            metadados_para_llm = {k: v for k, v in dados_extraidos_agregados.items() if k != "texto_relevante_coletado"}

            if texto_para_llm or metadados_para_llm:
                log_mensagens.append("Iniciando extracao/geracao com LLM.")
                dados_do_llm = await web_extractor.extrair_dados_produto_com_llm(
                    texto_pagina=texto_para_llm,
                    metadados_normalizados=metadados_para_llm,
                    campos_desejados=campos_desejados_llm,
                    produto_nome_base=db_produto_obj.nome_base,
                    user=user
                )
                if dados_do_llm:
                    log_mensagens.append(f"Dados recebidos do LLM: {json.dumps(dados_do_llm, indent=2, ensure_ascii=False)}")
                    if "erro_llm" in dados_do_llm or "erro_llm_inesperado" in dados_do_llm:
                        log_mensagens.append(f"ERRO do LLM: {dados_do_llm.get('erro_llm') or dados_do_llm.get('erro_llm_inesperado')}")
                        # Nao necessariamente uma falha total do enriquecimento se outros dados foram coletados
                        if not dados_coletados_de_fontes_web: # Se LLM era a unica esperanca e falhou
                            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA
                    else:
                        dados_extraidos_agregados.update(dados_do_llm)
                        dados_coletados_de_fontes_web = True # Se o LLM produziu algo, consideramos coleta
                else:
                    log_mensagens.append("LLM nao retornou dados ou ocorreu erro nao capturado explicitamente.")
            else:
                log_mensagens.append("Nenhum texto ou metadado suficiente para enviar ao LLM.")
        else: # openai_api_configurada e False
            log_mensagens.append("LLM nao foi chamado pois a API OpenAI nao esta configurada.")

        # Determinação do status final com base no que foi coletado
        status_para_salvar_no_final = status_resolver.resolve(
            models=models,
            status_para_salvar_no_final=status_para_salvar_no_final,
            dados_coletados_de_fontes_web=dados_coletados_de_fontes_web,
            openai_api_configurada=openai_api_configurada,
            busca_web_disponivel=busca_web_disponivel,
            urls_a_processar=urls_a_processar,
        )

        log_mensagens.append(f"Processamento principal concluído. Status determinado internamente: {status_para_salvar_no_final.value}")
    except Exception as e_main_try:
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRITICO INESPERADO NO PROCESSO: {str(e_main_try)}. Trace: {error_full}")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        logger.error(
            "ERRO CRITICO INESPERADO na tarefa de enriquecimento para produto ID %s: %s",
            produto_id,
            error_full,
        )
    
    finally:
        if db_produto_obj:
            try:
                status_para_salvar_no_final = finalization_service.apply(
                    db=db,
                    db_produto_obj=db_produto_obj,
                    status_para_salvar_no_final=status_para_salvar_no_final,
                    dados_extraidos_agregados=dados_extraidos_agregados,
                    log_mensagens=log_mensagens,
                )
                logger.info(
                    "INFO (web_enrichment.py _finally_): Produto ID %s status ATUALIZADO PARA %s.",
                    produto_id,
                    status_para_salvar_no_final.value,
                )
            except Exception as e_final_update:
                logger.error(
                    "ERRO CRITICO ao tentar atualizacao final do produto %s no finally: %s",
                    produto_id,
                    e_final_update,
                )
        
        final_status_value_print = status_para_salvar_no_final.value
        logger.info(
            "Finalizando tarefa de enriquecimento (variant=%s) para produto ID: %s. Status determinado para gravacao: %s",
            pipeline_variant,
            produto_id,
            final_status_value_print,
        )
        _shadow_result_comparator.record_result(
            context="web_enrichment.start",
            entity_id=produto_id,
            variant=pipeline_variant,
            payload={
                "status": final_status_value_print,
                "has_nome": bool(dados_extraidos_agregados.get("nome")),
                "has_descricao_curta": bool(
                    dados_extraidos_agregados.get("descricao_curta")
                ),
                "has_texto_relevante": bool(
                    dados_extraidos_agregados.get("texto_relevante_coletado")
                ),
                "log_lines": len(log_mensagens),
            },
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
        crud_users,
        crud_produtos,
        crud,
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
        pipeline_variant: str = "unknown",
    ):
        self._deps = {
            "logger": logger,
            "SQLAlchemyError": SQLAlchemyError,
            "crud_users": crud_users,
            "crud_produtos": crud_produtos,
            "crud": crud,
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
            "pipeline_variant": pipeline_variant,
        }

    async def execute(
        self,
        *,
        db_session_factory,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ):
        await run_web_enrichment_task(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
            **self._deps,
        )





