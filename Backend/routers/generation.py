# tdai_project/Backend/routers/generation.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

import crud 
import models 
import Project.Backend.schemas as schemas 
from database import get_db, SessionLocal 
from core.config import settings 

from .auth_utils import get_current_active_user 
from services import ia_generation_service, limit_service 

router = APIRouter(
    prefix="/geracao",
    tags=["Geração de Conteúdo com IA"],
    dependencies=[Depends(get_current_active_user)]
)

async def _tarefa_processar_geracao_e_registrar_uso(
    db_session_factory,
    user_id: int,
    produto_id: int,
    tipo_geracao_principal: str, # "titulo" ou "descricao"
    tipo_geracao_registro_uso: str, # ex: "titulo_openai_produto"
    modelo_ia_usado_base: str,
    funcao_geracao_ia,
    **kwargs_geracao
):
    db: Session = db_session_factory()
    db_produto: Optional[models.Produto] = None
    # Determina qual campo de status IA será atualizado
    status_field_to_update = None
    if tipo_geracao_principal == "titulo":
        status_field_to_update = "status_titulo_ia"
    elif tipo_geracao_principal == "descricao":
        status_field_to_update = "status_descricao_ia"

    try:
        user = crud.get_user(db, user_id)
        if not user:
            print(f"Tarefa de Geração: Usuário {user_id} não encontrado.")
            # Não podemos atualizar o status do produto se o usuário não for encontrado
            return

        db_produto = crud.get_produto(db, produto_id=produto_id)
        if not db_produto:
            print(f"Tarefa de Geração: Produto {produto_id} não encontrado.")
            return
        
        if db_produto.user_id != user.id and not user.is_superuser:
            print(f"Tarefa de Geração: Usuário {user_id} não autorizado para produto {produto_id}.")
            return

        # Atualizar status para EM_PROGRESSO antes de iniciar
        if status_field_to_update:
            update_data_progresso = {status_field_to_update: models.StatusGeracaoIAEnum.EM_PROGRESSO}
            log_progresso = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
            if not isinstance(log_progresso.get("historico_mensagens"), list): log_progresso["historico_mensagens"] = []
            log_progresso["historico_mensagens"].append(f"IA {tipo_geracao_principal}: Iniciando geração. Status: EM_PROGRESSO.")
            update_data_progresso["log_enriquecimento_web"] = log_progresso
            
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_progresso))
            # db.refresh(db_produto) # Opcional, se precisarmos dos dados atualizados imediatamente na tarefa

        dados_produto_prompt = {
            "nome_base": db_produto.nome_base,
            "marca": db_produto.marca,
            "categoria_original": db_produto.categoria_original,
            "dados_brutos": db_produto.dados_brutos
        }
        
        api_key_para_usar = user.chave_openai_pessoal or settings.OPENAI_API_KEY
        modelo_ia_final = modelo_ia_usado_base
        
        if "openai" in modelo_ia_usado_base.lower() and not api_key_para_usar:
            print(f"Tarefa de Geração: Chave API OpenAI não disponível para usuário {user_id} para produto {produto_id}.")
            if db_produto and status_field_to_update:
                 log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
                 if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
                 log_atual["historico_mensagens"].append(f"IA {tipo_geracao_principal}: ERRO. Chave API OpenAI não configurada.")
                 update_data_falha_config = {
                     status_field_to_update: models.StatusGeracaoIAEnum.FALHA_CONFIGURACAO_IA,
                     "log_enriquecimento_web": log_atual
                 }
                 crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_config))
            return

        print(f"Tarefa de Geração: Chamando IA para produto {produto_id}, tipo: {tipo_geracao_principal}")
        resultado_ia = await funcao_geracao_ia(
            dados_produto=dados_produto_prompt,
            user_api_key=api_key_para_usar,
            idioma=user.idioma_preferido or "pt-BR",
            **kwargs_geracao
        )
        print(f"Tarefa de Geração: Resultado IA para produto {produto_id} (truncado): {str(resultado_ia)[:200]}...")

        uso_ia_schema_data = {
            "produto_id": produto_id,
            "tipo_geracao": tipo_geracao_registro_uso,
            "modelo_ia_usado": modelo_ia_final,
            "resultado_gerado": str(resultado_ia),
            "prompt_utilizado": kwargs_geracao.get("prompt_completo_debug") # Pode ser grande, considerar truncar ou remover
        }
        
        uso_ia_obj_para_criar = schemas.UsoIACreate(**uso_ia_schema_data)
        crud.create_uso_ia(db=db, uso_ia=uso_ia_obj_para_criar, user_id=user.id)

        # Preparar dados para atualização final do produto
        update_data_final_dict: Dict[str, Any] = {}
        if tipo_geracao_principal == "titulo" and isinstance(resultado_ia, list) and resultado_ia: # Garante que não é lista vazia
            update_data_final_dict["titulos_sugeridos"] = resultado_ia
            if status_field_to_update: update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        elif tipo_geracao_principal == "descricao" and isinstance(resultado_ia, str) and resultado_ia.strip() and "Não foi possível gerar" not in resultado_ia :
            update_data_final_dict["descricao_principal_gerada"] = resultado_ia
            if status_field_to_update: update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        else: # Se resultado_ia for vazio, None, ou mensagem de erro padrão
            if status_field_to_update: update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.FALHOU
            print(f"Tarefa de Geração: IA não retornou resultado válido para produto {produto_id}, tipo: {tipo_geracao_principal}.")
        
        log_final = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
        if not isinstance(log_final.get("historico_mensagens"), list): log_final["historico_mensagens"] = []
        status_final_log = update_data_final_dict.get(status_field_to_update, models.StatusGeracaoIAEnum.FALHOU)
        log_final["historico_mensagens"].append(f"IA {tipo_geracao_principal}: Geração concluída. Status: {status_final_log.value}. Resultado (início): {str(resultado_ia)[:100]}...")
        update_data_final_dict["log_enriquecimento_web"] = log_final

        if update_data_final_dict and db_produto:
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_final_dict))
        
        print(f"Tarefa de Geração: Produto {produto_id} atualizado com resultado e status final da IA.")

    except ValueError as ve: # Erros levantados pelo ia_generation_service ou limit_service (embora limite seja síncrono)
        print(f"Tarefa de Geração: Erro de valor para produto {produto_id}: {ve}")
        if db_produto and status_field_to_update:
             log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
             if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
             log_atual["historico_mensagens"].append(f"IA {tipo_geracao_principal}: ERRO (ValueError): {str(ve)}")
             update_data_falha_valor = {
                 status_field_to_update: models.StatusGeracaoIAEnum.FALHOU, # Ou um status mais específico
                 "log_enriquecimento_web": log_atual
             }
             crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_valor))
    except Exception as e:
        import traceback
        print(f"Tarefa de Geração: Erro inesperado para produto {produto_id}: {traceback.format_exc()}")
        if db_produto and status_field_to_update:
             log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
             if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
             log_atual["historico_mensagens"].append(f"IA {tipo_geracao_principal}: ERRO CRÍTICO INESPERADO: {str(e)}")
             update_data_falha_critica = {
                 status_field_to_update: models.StatusGeracaoIAEnum.FALHOU,
                 "log_enriquecimento_web": log_atual
             }
             crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_critica))
    finally:
        print(f"Finalizando tarefa de geração IA para produto ID: {produto_id}")
        db.close()


@router.post("/titulos/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, summary="Gerar Títulos com OpenAI (Background)")
async def agendar_geracao_novos_titulos_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    # Verifica o limite ANTES de agendar a tarefa
    try:
        limit_service.verificar_limite_uso(db=db, user=current_user, tipo_geracao_principal="titulo")
    except HTTPException as e_limit: # Se o limite for atingido, a exceção é levantada aqui
        # Atualizar o status do produto para LIMITE_ATINGIDO
        log_limite = db_produto_check.log_enriquecimento_web or {"historico_mensagens": []}
        if not isinstance(log_limite.get("historico_mensagens"), list): log_limite["historico_mensagens"] = []
        log_limite["historico_mensagens"].append(f"IA Títulos: Falha ao iniciar. Limite de uso mensal atingido.")
        update_data_limite = {
            "status_titulo_ia": models.StatusGeracaoIAEnum.LIMITE_ATINGIDO,
            "log_enriquecimento_web": log_limite
        }
        crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_limite))
        raise e_limit # Relança a exceção para o cliente ser informado

    # Se passou pela verificação de limite, agenda a tarefa
    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="titulo",
        tipo_geracao_registro_uso="titulo_openai_produto",
        modelo_ia_usado_base="openai_gpt-3.5-turbo", 
        funcao_geracao_ia=ia_generation_service.gerar_titulos_produto_openai,
        quantidade=5 
    )
    return {"message": f"Geração de títulos para o produto ID {produto_id} agendada."}


@router.post("/descricao/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, summary="Gerar Descrição com OpenAI (Background)")
async def agendar_geracao_nova_descricao_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    try:
        limit_service.verificar_limite_uso(db=db, user=current_user, tipo_geracao_principal="descricao")
    except HTTPException as e_limit:
        log_limite = db_produto_check.log_enriquecimento_web or {"historico_mensagens": []}
        if not isinstance(log_limite.get("historico_mensagens"), list): log_limite["historico_mensagens"] = []
        log_limite["historico_mensagens"].append(f"IA Descrição: Falha ao iniciar. Limite de uso mensal atingido.")
        update_data_limite = {
            "status_descricao_ia": models.StatusGeracaoIAEnum.LIMITE_ATINGIDO,
            "log_enriquecimento_web": log_limite
        }
        crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_limite))
        raise e_limit

    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="descricao",
        tipo_geracao_registro_uso="descricao_openai_produto",
        modelo_ia_usado_base="openai_gpt-3.5-turbo", 
        funcao_geracao_ia=ia_generation_service.gerar_descricao_produto_openai
    )
    return {"message": f"Geração de descrição para o produto ID {produto_id} agendada."}