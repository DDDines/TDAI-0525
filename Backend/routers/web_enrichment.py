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
    status_original_do_produto_no_inicio_da_tarefa: models.StatusEnriquecimentoEnum = models.StatusEnriquecimentoEnum.PENDENTE
    
    try:
        db_produto_obj = db.query(models.Produto).filter(models.Produto.id == produto_id).with_for_update().first()
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} não encontrado.")
            print(log_mensagens[-1])
            db.close()
            return
        
        status_original_do_produto_no_inicio_da_tarefa = db_produto_obj.status_enriquecimento_web
        # Não mudamos o status para EM_PROGRESSO aqui ainda.

    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}")
        print(log_mensagens[-1])
        db.close()
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


    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}
    
    try:
        user = crud.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado.")
            # Define um status de falha se o usuário não for encontrado.
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
            return # O finally cuidará da atualização do produto

        # Verifica configurações críticas ANTES de mudar para EM_PROGRESSO
        openai_api_configurada = bool(user.chave_openai_pessoal or settings.OPENAI_API_KEY)
        google_api_configurada = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID)

        # Se NENHUMA das APIs principais (OpenAI E Google) estiver configurada, não há muito o que fazer.
        if not openai_api_configurada and not google_api_configurada:
            log_mensagens.append("AVISO CRÍTICO: Nem OpenAI nem Google API configuradas. Enriquecimento web não pode prosseguir efetivamente.")
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            # Opcional: Registrar uso da IA para falha de configuração
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoIAEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A",
                    resposta_ia="Falha: Configurações de API (OpenAI e Google) ausentes.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            return # Vai para o finally para salvar este status

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
                    tipo_acao=models.TipoAcaoIAEnum.ENRIQUECIMENTO_WEB_PRODUTO,
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
        if db_produto_obj.marca: query_parts.append(db_produto_obj.marca)
        if isinstance(db_produto_obj.dados_brutos, dict):
            codigo_original = db_produto_obj.dados_brutos.get("codigo_original") or db_produto_obj.dados_brutos.get("sku_original")
            if codigo_original: query_parts.append(str(codigo_original))
        query_base = " ".join(query_parts)
        query = termos_busca_override or (query_base + " especificações técnicas detalhadas")
        log_mensagens.append(f"Termo de busca Google: '{query}'")

        urls_encontradas_brutas = []
        if google_api_configurada:
            urls_encontradas_brutas = await web_extractor.buscar_urls_google(query=query, num_results=3)
            log_mensagens.append(f"Google Search retornou {len(urls_encontradas_brutas)} URLs.")
            if not urls_encontradas_brutas:
                log_mensagens.append(f"Nenhuma URL encontrada pelo Google para '{query}'.")
                # Não definimos NENHUMA_FONTE_ENCONTRADA ainda, pois o LLM pode tentar com dados existentes
        else:
            log_mensagens.append("Busca Google pulada devido à falta de configuração de API Google CSE.")

        urls_priorizadas = []
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
        
        urls_a_processar = urls_priorizadas[:2] # Limita a 2 URLs para processamento
        dados_coletados_de_fontes_web = False # Flag para saber se algo foi coletado da web

        if not urls_a_processar and not google_api_configurada:
            log_mensagens.append(f"Nenhuma URL para processar (Google desabilitado e sem override).")
            # Se o Google está desabilitado e não há URLs, o LLM ainda pode tentar só com dados brutos.
        elif not urls_a_processar and google_api_configurada:
            log_mensagens.append(f"Nenhuma URL encontrada ou selecionada para processar via Google para '{query}'.")
            # Se o Google funcionou mas não retornou nada, o LLM ainda pode tentar só com dados brutos.

        for i, url_processar in enumerate(urls_a_processar):
            log_mensagens.append(f"Processando URL {i+1}/{len(urls_a_processar)}: {url_processar}")
            html_content = await web_extractor.coletar_conteudo_pagina_playwright(url_processar)
            if not html_content:
                log_mensagens.append(f"Não foi possível obter conteúdo HTML da URL: {url_processar}")
                continue # Tenta a próxima URL

            texto_principal = web_extractor.extrair_texto_principal_com_trafilatura(html_content)
            metadados_extruct = web_extractor.extrair_metadados_estruturados(html_content, url_processar)
            metadados_normalizados_pagina = web_extractor._normalizar_dados_de_metadados(metadados_extruct)

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
            if not texto_para_llm and isinstance(db_produto_obj.dados_brutos, dict): # Fallback para dados brutos se nenhum texto web
                texto_para_llm = json.dumps(db_produto_obj.dados_brutos.get("dados_brutos_originais", db_produto_obj.dados_brutos), ensure_ascii=False)
            
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
            elif not google_api_configurada and not openai_api_configurada: # Se nenhuma API estava ativa e não havia URLs override
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            elif not google_api_configurada and openai_api_configurada and not dados_coletados_de_fontes_web: # Google off, OpenAI on mas não produziu nada (ex: sem texto)
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            else: # Caso geral se não se encaixar acima, mas o processo "correu"
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU

        log_mensagens.append(f"Processamento principal concluído. Status determinado internamente: {status_para_salvar_no_final.value}")

    except Exception as e_main_try:
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRÍTICO INESPERADO NO PROCESSO: {str(e_main_try)}. Trace: {error_full}")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        print(f"ERRO CRÍTICO INESPERADO na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
    
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

                payload_final_update = schemas.ProdutoUpdate(
                    dados_brutos=dados_extraidos_agregados,
                    status_enriquecimento_web=status_valor_str, # Passa a string (valor do enum)
                    log_enriquecimento_web={"historico_mensagens": log_mensagens}
                )
                crud.update_produto(db, db_produto=db_produto_obj, produto_update=payload_final_update)
                log_mensagens.append(f"Produto ID {produto_id} FINALMENTE atualizado com status: {status_valor_str}.")
                print(f"INFO (web_enrichment.py _finally_): Produto ID {produto_id} status ATUALIZADO PARA {status_valor_str}.")
            except Exception as e_final_update:
                print(f"ERRO CRÍTICO ao tentar atualização final do produto {produto_id} no finally: {e_final_update}")
        
        final_status_value_print = status_para_salvar_no_final.value
        print(f"Finalizando tarefa de enriquecimento para produto ID: {produto_id}. Status determinado para gravação: {final_status_value_print}")
        
        db.close()

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