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
    status_final_a_ser_aplicado: models.StatusEnriquecimentoEnum = models.StatusEnriquecimentoEnum.FALHOU # Default inicial
    
    try:
        db_produto_obj = db.query(models.Produto).filter(models.Produto.id == produto_id).with_for_update().first()
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} não encontrado.")
            print(log_mensagens[-1])
            # Não há produto para atualizar no finally se não foi encontrado aqui.
            db.close()
            return
    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}")
        print(log_mensagens[-1])
        db.close()
        return

    # Se o produto foi carregado, definimos status_final_a_ser_aplicado com o status atual
    # para o caso de exceções não tratadas antes da lógica principal de determinação de status.
    # Mas, para a lógica de enriquecimento, começamos com FALHOU como default se algo der errado.
    status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos.copy() if isinstance(db_produto_obj.dados_brutos, dict) else {}
    
    try:
        user = crud.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado.")
            # status_final_a_ser_aplicado já é FALHOU
            return # O finally cuidará da atualização do produto

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
                prompt_utilizado="N/A - Config OpenAI pendente"
            ), user_id=user.id)
            log_mensagens.append("INFO: Falha por config OpenAI registrada no histórico de uso da IA.")
        else: 
            # ... (Lógica de busca Google e processamento de URLs como na sua última versão)
            # IMPORTANTE: Dentro desta lógica, quando definir status_final_a_ser_aplicado,
            # use sempre o objeto enum, ex: status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
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
                status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            else:
                # ... (loop e lógica de processamento de URL e LLM como antes) ...
                # ... (ao final do loop, defina status_final_a_ser_aplicado para CONCLUIDO_SUCESSO, etc.) ...
                # Esta parte da lógica interna de determinação de status é crucial.
                # Por exemplo:
                pelo_menos_uma_url_processada_com_sucesso_llm = False # Assumindo flags
                pelo_menos_uma_url_com_metadados = False # Assumindo flags
                # (Após o loop de processamento das URLs)
                if status_final_a_ser_aplicado not in [models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA, models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA]:
                    if pelo_menos_uma_url_processada_com_sucesso_llm or (pelo_menos_uma_url_com_metadados and dados_coletados_nesta_tarefa):
                        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                    elif dados_coletados_nesta_tarefa:
                        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS
                    elif urls_a_processar: # Processou URLs mas nada foi coletado
                         status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA

        log_mensagens.append(f"Processamento principal concluído. Status determinado internamente: {status_final_a_ser_aplicado.value}")

    except Exception as e_main_try:
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRÍTICO INESPERADO NO PROCESSO: {str(e_main_try)}. Trace: {error_full}")
        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU 
        print(f"ERRO CRÍTICO INESPERADO na tarefa de enriquecimento para produto ID {produto_id}: {error_full}")
    
    finally:
        if db_produto_obj: # Garante que db_produto_obj existe
            try:
                db.refresh(db_produto_obj) # Pega o estado mais recente do banco
                
                # Se a tarefa definiu explicitamente um status final, usa ele.
                # Se a tarefa falhou e status_final_a_ser_aplicado não foi mudado do default FALHOU (ou ficou EM_PROGRESSO),
                # ele será FALHOU.
                # A principal garantia é que, se o status no banco ainda for EM_PROGRESSO,
                # e a tarefa está finalizando, ele não deve permanecer EM_PROGRESSO.
                if db_produto_obj.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
                    if status_final_a_ser_aplicado == models.StatusEnriquecimentoEnum.EM_PROGRESSO: # Segurança
                        status_final_a_ser_aplicado = models.StatusEnriquecimentoEnum.FALHOU
                        log_mensagens.append("ALERTA FINALLY: Status final ainda era EM_PROGRESSO, forçando para FALHOU.")
                
                # **** ALTERAÇÃO CRUCIAL AQUI ****
                # Ao criar o ProdutoUpdate, passamos o VALOR do enum (string)
                status_valor_str = status_final_a_ser_aplicado.value if isinstance(status_final_a_ser_aplicado, models.StatusEnriquecimentoEnum) else str(status_final_a_ser_aplicado)

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
                # Se mesmo a atualização final falhar, não há muito mais a fazer na tarefa
        
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