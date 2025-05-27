# tdai_project/Backend/routers/web_enrichment.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError # Para capturar exceções do SQLAlchemy
from typing import List, Dict, Any, Optional
import asyncio
import json

import crud
import models
import schemas
from database import get_db, SessionLocal

from .auth_utils import get_current_active_user

from services import web_data_extractor_service as web_extractor
from core.config import settings

router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(get_current_active_user)]
)

async def _tarefa_enriquecer_produto_web(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None
):
    db: Session = db_session_factory()
    log_mensagens: List[str] = [f"INICIANDO tarefa de enriquecimento web para produto ID: {produto_id}."]
    
    db_produto_obj: Optional[models.Produto] = None
    # Tenta carregar o produto. Se não existir, não há o que fazer.
    try:
        db_produto_obj = db.query(models.Produto).filter(models.Produto.id == produto_id).with_for_update().first() # Adiciona with_for_update para lock
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} não encontrado ao iniciar a tarefa.")
            print(log_mensagens[-1])
            return
    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}")
        print(log_mensagens[-1])
        return # Não pode prosseguir
    finally:
        if not db_produto_obj: # Se o produto não foi carregado, fecha a sessão
            db.close()

    # Se o produto foi carregado com sucesso:
    status_antes_da_tarefa = db_produto_obj.status_enriquecimento_web # Guarda o status original da tentativa
    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}
    
    # Define status_final_produto como FALHOU por padrão. Será alterado se houver sucesso ou erro específico.
    status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
    
    try:
        user = crud.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado. Tarefa abortada.")
            # status_final_a_ser_aplicado já é FALHOU
            return 

        # Marca como EM_PROGRESSO e commita imediatamente.
        log_mensagens.append(f"Definindo status do produto ID {produto_id} para EM_PROGRESSO.")
        db_produto_obj.status_enriquecimento_web = models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens}
        db.commit()
        db.refresh(db_produto_obj)
        
        # ----- Início do Processamento Principal -----
        google_api_configurada = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID)
        openai_api_configurada = bool(user.chave_openai_pessoal or settings.OPENAI_API_KEY)

        if not openai_api_configurada:
            log_mensagens.append("AVISO CRÍTICO: Chave API OpenAI não configurada. Enriquecimento LLM não pode ser executado.")
            status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            crud.create_uso_ia(db=db, uso_ia=schemas.UsoIACreate(
                produto_id=produto_id, tipo_geracao="enriquecimento_config_faltante_openai", modelo_ia_usado="N/A",
                resultado_gerado="Falha: Chave API OpenAI não configurada.",
                prompt_utilizado="N/A - Configuração OpenAI pendente"
            ), user_id=user.id)
            log_mensagens.append("INFO: Falha por config OpenAI registrada no histórico de uso da IA.")
            # A tarefa continua para o finally para garantir a atualização do status do produto.
        else: # OpenAI está configurada, prossegue com a lógica principal
            query_parts = [db_produto_obj.nome_base]
            if db_produto_obj.marca: query_parts.append(db_produto_obj.marca)
            if isinstance(db_produto_obj.dados_brutos, dict):
                codigo_original = db_produto_obj.dados_brutos.get("codigo_original") or db_produto_obj.dados_brutos.get("sku_original")
                if codigo_original: query_parts.append(str(codigo_original))
            query = termos_busca_override or (" ".join(query_parts) + " especificações técnicas detalhadas")
            log_mensagens.append(f"Termo de busca Google: '{query}'")

            urls_encontradas_brutas = []
            if google_api_configurada:
                urls_encontradas_brutas = await web_extractor.buscar_urls_google(query=query, num_results=3)
                log_mensagens.append(f"Google Search retornou {len(urls_encontradas_brutas)} URLs.")
            else:
                log_mensagens.append("Busca Google pulada devido à falta de configuração de API Google CSE.")
            
            urls_priorizadas = []
            # ... (lógica de priorização como antes) ...
            if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url:
                try:
                    site_fornecedor_str = str(db_produto_obj.fornecedor.site_url)
                    site_fornecedor_domain = site_fornecedor_str.split("//")[-1].split("/")[0].lower()
                    for url_g in urls_encontradas_brutas:
                        if site_fornecedor_domain in url_g.lower(): urls_priorizadas.insert(0, url_g)
                        else: urls_priorizadas.append(url_g)
                except Exception as e_url_forn:
                    log_mensagens.append(f"AVISO: Erro ao processar URL do fornecedor para priorização: {e_url_forn}")
                    urls_priorizadas = urls_encontradas_brutas
            else: urls_priorizadas = urls_encontradas_brutas
            urls_a_processar = urls_priorizadas[:2]

            dados_coletados_nesta_tarefa = False

            if not urls_a_processar:
                log_mensagens.append(f"Nenhuma URL relevante encontrada ou selecionada para '{query}'.")
                # Se OpenAI está configurada, mas não há URLs, o status é NENHUMA_FONTE
                status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            else:
                log_mensagens.append(f"URLs selecionadas para processamento: {urls_a_processar}")
                pelo_menos_uma_url_processada_com_sucesso_llm = False
                pelo_menos_uma_url_com_metadados = False

                for url_idx, url in enumerate(urls_a_processar):
                    # ... (lógica de coleta de HTML, extração de metadados, trafilatura) ...
                    log_mensagens.append(f"Processando URL ({url_idx+1}/{len(urls_a_processar)}): {url}")
                    html_content = await web_extractor.coletar_conteudo_pagina_playwright(url)
                    if not html_content: log_mensagens.append(f"AVISO: Falha ao coletar HTML da URL: {url}"); continue
                    
                    metadados_brutos = web_extractor.extrair_metadados_estruturados(html_content, url=url)
                    metadados_normalizados = {}
                    if metadados_brutos:
                        metadados_normalizados = web_extractor._normalizar_dados_de_metadados(metadados_brutos)
                        if metadados_normalizados: # Se algo foi normalizado
                            pelo_menos_uma_url_com_metadados = True
                            dados_coletados_nesta_tarefa = True # Mesmo que só metadados
                            for k_meta, v_meta in metadados_normalizados.items(): dados_extraidos_agregados[f"meta_{k_meta}"] = v_meta
                    
                    texto_pagina = web_extractor.extrair_texto_principal_com_trafilatura(html_content)
                    resultado_extracao_llm_str = "LLM não utilizada (conteúdo insuficiente ou OpenAI não chamada)."
                    modelo_ia_usado_extracao = "N/A"

                    if (texto_pagina and len(texto_pagina) >= 50) or metadados_normalizados:
                        log_mensagens.append(f"INFO: Tentando extração com LLM para {url}")
                        modelo_ia_usado_extracao = "openai_gpt-3.5-turbo"
                        dados_da_pagina_llm = await web_extractor.extrair_dados_produto_com_llm(
                            # ... (args)
                            texto_pagina=texto_pagina, metadados_normalizados=metadados_normalizados.copy(),
                            campos_desejados=["nome_completo_produto", "marca_identificada", "modelo_especifico", "sku_codigo","descricao_detalhada_paragrafos", "lista_caracteristicas_beneficios_bullets","especificacoes_tecnicas_dict", "categoria_sugerida_hierarquia","cor_principal", "material_predominante"],
                            produto_nome_base=db_produto_obj.nome_base, user=user
                        )
                        if dados_da_pagina_llm and not dados_da_pagina_llm.get("erro_llm"):
                            dados_coletados_nesta_tarefa = True; pelo_menos_uma_url_processada_com_sucesso_llm = True
                            # ... (atualiza dados_extraidos_agregados)
                            for k_llm, v_llm in dados_da_pagina_llm.items(): dados_extraidos_agregados[f"llm_{k_llm}"] = v_llm
                            resultado_extracao_llm_str = json.dumps(dados_da_pagina_llm)
                        elif dados_da_pagina_llm and dados_da_pagina_llm.get("erro_llm"):
                            resultado_extracao_llm_str = f"Falha na extração LLM: {dados_da_pagina_llm['erro_llm']}"
                            # Aqui, status_final_a_ser_aplicado poderia ser FALHA_API_EXTERNA se este erro for crítico
                            # e não houver outros sucessos.
                            if not pelo_menos_uma_url_processada_com_sucesso_llm and not pelo_menos_uma_url_com_metadados: # Se é a primeira falha e nada antes
                                status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA
                        
                        crud.create_uso_ia(db=db, uso_ia=schemas.UsoIACreate(
                            produto_id=produto_id, tipo_geracao=f"extracao_dados_web_openai_url",
                            modelo_ia_usado=modelo_ia_usado_extracao, resultado_gerado=resultado_extracao_llm_str[:10000],
                            prompt_utilizado=f"Extração de dados da URL: {url}"
                        ), user_id=user.id)
                        log_mensagens.append(f"INFO: Tentativa de extração LLM para {url} registrada.")
                    if url_idx < len(urls_a_processar) - 1: await asyncio.sleep(1)
                
                # Após o loop de URLs, define o status final baseado nos resultados
                if status_final_a_ser_aplicado not in [models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA, models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA]:
                    if pelo_menos_uma_url_processada_com_sucesso_llm or (pelo_menos_uma_url_com_metadados and dados_coletados_nesta_tarefa):
                        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                    elif dados_coletados_nesta_tarefa: # Coletou algo (metadados), mas talvez LLM não teve sucesso total
                        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
                    elif urls_a_processar: # Processou URLs mas nada foi coletado
                         status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA

        # Se chegamos aqui e status_final_a_ser_aplicado ainda é FALHOU (o default inicial do try),
        # e não foi um erro de config OpenAI (tratado antes), mantemos FALHOU.
        # Se foi NENHUMA_FONTE_ENCONTRADA, CONCLUIDO_SUCESSO, etc., esses valores serão usados.
        log_mensagens.append(f"Processamento principal concluído. Status determinado: {status_final_a_ser_aplicado.value}")

    except SQLAlchemyError as e_sql: # Captura erros do SQLAlchemy
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO SQL DURANTE O PROCESSO: {str(e_sql)}. Trace: {error_full}")
        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
        print(f"ERRO SQL na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
    except Exception as e: # Captura qualquer outra exceção não prevista
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRÍTICO INESPERADO NO PROCESSO: {str(e)}. Trace: {error_full}")
        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
        print(f"ERRO CRÍTICO INESPERADO na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
    
    finally:
        if db_produto_obj: # Só atualiza se o produto foi carregado
            # Se a tarefa definiu um status de EM_PROGRESSO, mas está finalizando
            # e o status_final_a_ser_aplicado não foi atualizado para um estado final,
            # força para FALHOU. Isso acontece se uma exceção ocorrer após
            # EM_PROGRESSO mas antes de status_final_a_ser_aplicado ser mudado.
            if db_produto_obj.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO and \
               status_final_a_ser_aplicado == models.StatusEnriquecimentoEnum.EM_PROGRESSO: # Se por algum motivo ficou EM_PROGRESSO
                status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
                log_mensagens.append("ALERTA: Status final da tarefa era EM_PROGRESSO, forçando para FALHOU.")
            
            try:
                crud.update_produto(db, db_produto=db_produto_obj, produto_update=schemas.ProdutoUpdate(
                    dados_brutos=dados_extraidos_agregados,
                    status_enriquecimento_web=status_final_a_ser_aplicado,
                    log_enriquecimento_web={"historico_mensagens": log_mensagens}
                ))
                print_status = status_final_a_ser_aplicado.value if isinstance(status_final_a_ser_aplicado, models.StatusEnriquecimentoEnum) else str(status_final_a_ser_aplicado)
                log_mensagens.append(f"Produto ID {produto_id} FINALMENTE atualizado com status: {print_status}.")
                print(f"INFO (web_enrichment.py _finally_): Produto ID {produto_id} status ATUALIZADO PARA {print_status}.")
            except Exception as e_final_update:
                # Se a atualização final falhar, não há muito mais a fazer aqui na tarefa de background
                log_mensagens.append(f"ERRO CRÍTICO ao tentar atualização final do produto {produto_id} no finally: {e_final_update}")
                print(f"ERRO CRÍTICO ao tentar atualização final do produto {produto_id} no finally: {e_final_update}")
        
        final_status_value_print = status_final_a_ser_aplicado.value if isinstance(status_final_a_ser_aplicado, models.StatusEnriquecimentoEnum) else str(status_final_a_ser_aplicado)
        print(f"Finalizando tarefa de enriquecimento para produto ID: {produto_id}. Status determinado para gravação: {final_status_value_print}")
        
        db.close()


# O endpoint @router.post permanece o mesmo
@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(None, description="Opcional: Termos de busca específicos para o Google Search."),
):
    db_temp = SessionLocal()
    try:
        db_produto_check = crud.get_produto(db_temp, produto_id=produto_id)
        if not db_produto_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
        if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a enriquecer este produto")
        
        if db_produto_check.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Processo de enriquecimento já está em andamento para este produto.")
    finally:
        db_temp.close()

    background_tasks.add_task(
        _tarefa_enriquecer_produto_web,
        db_session_factory=SessionLocal,
        produto_id=produto_id,
        user_id=current_user.id,
        termos_busca_override=termos_busca_override
    )
    return {"message": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."}