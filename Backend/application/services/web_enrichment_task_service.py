from __future__ import annotations

from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session


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
):
    db: Optional[Session] = None
    log_mensagens: List[str] = [
        f"INICIANDO tarefa de enriquecimento web para produto ID: {produto_id}."
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
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} não encontrado.")
            logger.error(log_mensagens[-1])
            return
        
        status_original_do_produto_no_inicio_da_tarefa = db_produto_obj.status_enriquecimento_web
        # Não mudamos o status para EM_PROGRESSO aqui ainda.

    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(
            f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}"
        )
        logger.error(log_mensagens[-1])
        return

    # Esta será a variável que controlará o status a ser salvo no final.
    # Inicializa com o status que o produto tinha antes da tarefa começar,
    # ou FALHOU se algo der muito errado antes mesmo de verificarmos as APIs.
    status_para_salvar_no_final: models.StatusEnriquecimentoEnum = status_original_do_produto_no_inicio_da_tarefa
    
    # Se o status original já era EM_PROGRESSO por algum motivo (ex: tarefa anterior falhou ao limpar),
    # é melhor considerá-lo como PENDENTE para esta nova execução ou FALHOU para evitar loops.
    # Para simplificar, se estava EM_PROGRESSO, vamos reverter para PENDENTE como base para esta tentativa.
    if status_original_do_produto_no_inicio_da_tarefa == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
        log_mensagens.append(f"AVISO: Produto {produto_id} encontrado como EM_PROGRESSO no início. Considerando como PENDENTE para esta execução.")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.PENDENTE


    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos_web.copy() if isinstance(db_produto_obj.dados_brutos_web, dict) else {}
    
    try:
        user = crud_users.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado.")
            # Define um status de falha se o usuário não for encontrado.
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
            return # O finally cuidará da atualização do produto

        # Verifica configurações críticas ANTES de mudar para EM_PROGRESSO
        openai_user_configurada = bool(user.chave_openai_pessoal)
        openai_system_configurada = bool(settings.OPENAI_API_KEY)
        openai_api_configurada = bool(openai_user_configurada or openai_system_configurada)
        google_api_configurada = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID)
        busca_publica_fallback = bool(getattr(web_extractor, "busca_publica_disponivel", lambda: False)())
        busca_web_disponivel = google_api_configurada or busca_publica_fallback
        log_mensagens.append(
            "Config API: "
            f"openai_user={'sim' if openai_user_configurada else 'não'}, "
            f"openai_sistema={'sim' if openai_system_configurada else 'não'}, "
            f"google_cse={'sim' if google_api_configurada else 'não'}, "
            f"busca_publica={'sim' if busca_publica_fallback else 'não'}."
        )

        # Sem OpenAI e sem mecanismo de busca web, não há como enriquecer.
        if not openai_api_configurada and not busca_web_disponivel:
            log_mensagens.append(
                "AVISO CRÍTICO: Sem OpenAI e sem mecanismo de busca web disponível. "
                "Configure OPENAI_API_KEY (ou chave pessoal do usuário) e/ou Google CSE."
            )
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            # Opcional: Registrar uso da IA para falha de configuração
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A",
                    resposta_ia="Falha: Configurações de API externas ausentes.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            return # Vai para o finally para salvar este status

        if not google_api_configurada and busca_publica_fallback:
            log_mensagens.append(
                "Google CSE não configurado. Usando fallback de busca pública sem API key."
            )

        # Se especificamente a OpenAI não está configurada, mas a Google pode estar.
        # O enriquecimento LLM não será possível, mas a busca e extração de metadados sim.
        if not openai_api_configurada:
            log_mensagens.append("AVISO: Chave API OpenAI não configurada. Enriquecimento via LLM será pulado. Outras coletas de dados (Google, metadados) tentarão prosseguir.")
            # Não definimos status_para_salvar_no_final como FALHA_CONFIGURACAO_API_EXTERNA ainda,
            # pois a busca Google e extração de metadados podem funcionar.
            # O status final dependerá se essas outras etapas coletam algo.
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A - Config OpenAI pendente para LLM",
                    resposta_ia="Falha Parcial: Chave API OpenAI não configurada para LLM.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            # A tarefa continua para tentar coletar dados de outras fontes

        # ----- AGORA, definimos o status para EM_PROGRESSO no banco -----
        # Isso sinaliza que as verificações iniciais passaram e o trabalho real começou.
        log_mensagens.append(f"Definindo status do produto ID {produto_id} para EM_PROGRESSO no banco.")
        db_produto_obj.status_enriquecimento_web = models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens} # Salva o log inicial
        db.commit()
        db.refresh(db_produto_obj)
        
        # O status_para_salvar_no_final será o que resultar do processamento.
        # Se tudo correr bem, será CONCLUIDO_SUCESSO. Se houver problemas, será outro.
        # Por default, se nada mudar, consideramos uma falha genérica ao final do try.
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        
        # ----- Início do Processamento Principal -----
        query_parts = [db_produto_obj.nome_base]
        if db_produto_obj.sku:
            query_parts.append(db_produto_obj.sku)
        ean_raw = str(db_produto_obj.ean or "").strip()
        ean_digits = re.sub(r"\D", "", ean_raw)
        if ean_digits and 8 <= len(ean_digits) <= 14:
            query_parts.append(ean_digits)

        query_base = " ".join([str(part).strip() for part in query_parts if str(part).strip()])

        query_candidates: List[str] = []
        if termos_busca_override:
            query_candidates.append(termos_busca_override.strip())
        else:
            nome_base_clean = str(db_produto_obj.nome_base or "").strip()
            fornecedor_nome = (
                str(db_produto_obj.fornecedor.nome or "").strip()
                if db_produto_obj.fornecedor and db_produto_obj.fornecedor.nome
                else ""
            )
            codigo_original = ""
            if isinstance(db_produto_obj.dados_brutos_web, dict):
                codigo_original = str(
                    db_produto_obj.dados_brutos_web.get("codigo_original")
                    or db_produto_obj.dados_brutos_web.get("sku_original")
                    or ""
                ).strip()

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

        # Deduplicar preservando ordem.
        query_candidates = [q for q in dict.fromkeys(q for q in query_candidates if q)]

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
                        "Nenhum termo de busca válido pode ser montado para este produto."
                    )
        else:
            log_mensagens.append("Busca web pulada: nenhum provedor de busca disponível.")
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
            log_mensagens.append(f"Ranking de URLs por relevância: {ranking_log}")
        elif urls_encontradas_brutas:
            log_mensagens.append(
                "URLs encontradas, mas descartadas por baixa relevância/sinal de tracking."
            )
        dados_coletados_de_fontes_web = False # Flag para saber se algo foi coletado da web

        if not urls_a_processar and not busca_web_disponivel:
            log_mensagens.append("Nenhuma URL para processar (busca web indisponível e sem override).")
            # Sem busca web, o LLM ainda pode tentar com dados brutos.
        elif not urls_a_processar and busca_web_disponivel:
            log_mensagens.append("Nenhuma URL encontrada ou selecionada para processar.")
            # Mesmo sem URLs, o LLM ainda pode tentar com dados brutos.

        for i, url_processar in enumerate(urls_a_processar):
            log_mensagens.append(f"Processando URL {i+1}/{len(urls_a_processar)}: {url_processar}")
            html_content = await web_extractor.coletar_conteudo_pagina_playwright(url_processar)
            if not html_content:
                log_mensagens.append(f"Não foi possível obter conteúdo HTML da URL: {url_processar}")
                continue # Tenta a próxima URL

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
                log_mensagens.append(f"Metadados normalizados extraídos da URL {url_processar}: {json.dumps(metadados_normalizados_pagina, indent=2, ensure_ascii=False)}")
                dados_extraidos_agregados.update(metadados_normalizados_pagina) # Atualiza com prioridade para novos dados
                dados_coletados_de_fontes_web = True
            
            if texto_principal:
                log_mensagens.append(f"Texto principal extraído da URL {url_processar} (primeiros 300 chars): {texto_principal[:300]}")
                # Guarda o texto da primeira página processada com sucesso para possível uso pelo LLM
                if "texto_relevante_coletado" not in dados_extraidos_agregados:
                    dados_extraidos_agregados["texto_relevante_coletado"] = texto_principal
                dados_coletados_de_fontes_web = True
            
            # Se já temos dados suficientes de metadados e texto, podemos parar antes
            if metadados_normalizados_pagina.get("nome") and metadados_normalizados_pagina.get("descricao_curta"):
                log_mensagens.append(f"Dados chave (nome, descrição) encontrados em {url_processar}. Considerando suficiente desta URL.")
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
                log_mensagens.append("Iniciando extração/geração com LLM.")
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
                        # Não necessariamente uma falha total do enriquecimento se outros dados foram coletados
                        if not dados_coletados_de_fontes_web: # Se LLM era a única esperança e falhou
                            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA
                    else:
                        dados_extraidos_agregados.update(dados_do_llm)
                        dados_coletados_de_fontes_web = True # Se o LLM produziu algo, consideramos coleta
                else:
                    log_mensagens.append("LLM não retornou dados ou ocorreu erro não capturado explicitamente.")
            else:
                log_mensagens.append("Nenhum texto ou metadado suficiente para enviar ao LLM.")
        else: # openai_api_configurada é False
            log_mensagens.append("LLM não foi chamado pois a API OpenAI não está configurada.")

        # Determinação do status final com base no que foi coletado
        if status_para_salvar_no_final == models.StatusEnriquecimentoEnum.EM_PROGRESSO or status_para_salvar_no_final == models.StatusEnriquecimentoEnum.FALHOU : # Se não houve falha crítica antes
            if dados_coletados_de_fontes_web:
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                if not openai_api_configurada: # Se coletou dados web mas LLM não rodou por config
                    status_para_salvar_no_final = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS # Ou um novo status como "CONCLUIDO_SEM_LLM"
            elif urls_a_processar: # Tentou processar URLs mas nada foi efetivamente coletado
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            elif busca_web_disponivel and not urls_a_processar:
                # Busca disponivel, mas nenhum link elegivel foi retornado.
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            elif not busca_web_disponivel and not openai_api_configurada: # Se nenhuma API/fallback estava ativa e não havia URLs override
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            elif not busca_web_disponivel and openai_api_configurada and not dados_coletados_de_fontes_web: # Busca off, OpenAI on mas não produziu nada
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            else: # Caso geral se não se encaixar acima, mas o processo "correu"
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU

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
                # O status atual no db_produto_obj pode ser EM_PROGRESSO se chegou a commitar.
                # status_para_salvar_no_final contém o status que REALMENTE deve ser salvo.
                
                # Se o status no banco ainda é EM_PROGRESSO (porque foi commitado),
                # mas o status_para_salvar_no_final também ficou EM_PROGRESSO (indicando que talvez a lógica de determinação final não pegou todos os casos),
                # então forçamos para FALHOU para não deixar o produto preso em EM_PROGRESSO.
                if db_produto_obj.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO and \
                   status_para_salvar_no_final == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
                    status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
                    log_mensagens.append("ALERTA FINALLY: Status final e do DB eram EM_PROGRESSO, forçando para FALHOU.")
                
                status_valor_str = status_para_salvar_no_final.value

                (
                    campos_visiveis_update,
                    notas_campos,
                    notas_ignoradas,
                ) = build_payload_enriquecimento_visivel(
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
                    normalized_message = normalize_human_text(message)
                    if normalized_message:
                        log_mensagens_normalizadas.append(normalized_message)

                payload_final_update = schemas.ProdutoUpdate(
                    **campos_visiveis_update,
                    dados_brutos_web=dados_extraidos_agregados,
                    status_enriquecimento_web=status_valor_str, # Passa a string (valor do enum)
                    log_enriquecimento_web={
                        "historico_mensagens": log_mensagens_normalizadas,
                        "resumo_aplicacao": resumo_aplicacao,
                    }
                )
                crud_produtos.update_produto(db, db_produto=db_produto_obj, produto_update=payload_final_update)
                log_mensagens.append(f"Produto ID {produto_id} FINALMENTE atualizado com status: {status_valor_str}.")
                logger.info(
                    "INFO (web_enrichment.py _finally_): Produto ID %s status ATUALIZADO PARA %s.",
                    produto_id,
                    status_valor_str,
                )
            except Exception as e_final_update:
                logger.error(
                    "ERRO CRITICO ao tentar atualizacao final do produto %s no finally: %s",
                    produto_id,
                    e_final_update,
                )
        
        final_status_value_print = status_para_salvar_no_final.value
        logger.info(
            "Finalizando tarefa de enriquecimento para produto ID: %s. Status determinado para gravação: %s",
            produto_id,
            final_status_value_print,
        )
        
        if db:
            db.close()
