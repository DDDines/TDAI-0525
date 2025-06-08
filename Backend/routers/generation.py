# Backend/routers/generation.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging # <-- ADICIONADO

from . import auth_utils
from Backend import crud_users
from Backend import crud_produtos
from Backend import models
from Backend import schemas
from Backend.database import get_db, SessionLocal
from Backend.services import ia_generation_service, limit_service
from .auth_utils import get_current_active_user

# Configuração do logger para este módulo
logger = logging.getLogger(__name__) # <-- ADICIONADO

router = APIRouter(
    prefix="/geracao",
    tags=["Geração de Conteúdo com IA"],
    dependencies=[Depends(get_current_active_user)],
)

# Função auxiliar adaptada do seu original para processar em background
async def _tarefa_processar_geracao_e_registrar_uso(
    db_session_factory,
    user_id: int,
    produto_id: int,
    tipo_geracao_principal: str, # "titulo" ou "descricao"
    funcao_geracao_ia_no_servico,
    **kwargs_para_funcao_servico
):
    """
    Tarefa de fundo para executar a geração de conteúdo com IA,
    atualizar o produto e registrar o uso da IA no banco de dados.
    """
    db: Session = db_session_factory()
    db_produto: Optional[models.Produto] = None
    status_field_to_update: Optional[str] = None
    campo_produto_para_atualizar_com_resultado: Optional[str] = None

    if tipo_geracao_principal == "titulo":
        status_field_to_update = "status_titulo_ia"
        campo_produto_para_atualizar_com_resultado = "titulos_sugeridos"
    elif tipo_geracao_principal == "descricao":
        status_field_to_update = "status_descricao_ia"
        campo_produto_para_atualizar_com_resultado = "descricao_principal_gerada"
    else:
        logger.error(f"Tarefa Background: Tipo de geração principal '{tipo_geracao_principal}' desconhecido.")
        db.close()
        return

    log_entry_prefix = f"IA {tipo_geracao_principal.capitalize()}"

    try:
        user = crud_users.get_user(db, user_id=user_id)
        if not user:
            logger.error(f"Tarefa Background {log_entry_prefix}: Usuário {user_id} não encontrado.")
            db.close()
            return

        db_produto = crud_produtos.get_produto(db, produto_id=produto_id)
        if not db_produto:
            logger.error(f"Tarefa Background {log_entry_prefix}: Produto {produto_id} não encontrado.")
            db.close()
            return
        
        if db_produto.user_id != user.id and not user.is_superuser:
            logger.warning(f"Tarefa Background {log_entry_prefix}: Usuário {user_id} não autorizado para produto {produto_id}.")
            db.close()
            return

        # Atualizar status para EM_PROGRESSO
        if status_field_to_update:
            update_data_progresso = {status_field_to_update: models.StatusGeracaoIAEnum.EM_PROGRESSO}
            log_atual_obj = list(db_produto.log_processamento or [])
            log_atual_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Geração com Gemini iniciada."})
            update_data_progresso["log_processamento"] = log_atual_obj
            crud_produtos.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_progresso))

        logger.info(f"Tarefa Background {log_entry_prefix}: Chamando serviço Gemini para produto {produto_id}.")
        
        # Chama a função de serviço Gemini correspondente
        resultado_ia = await funcao_geracao_ia_no_servico(
            db=db,
            produto_id=produto_id,
            user=user,
            **kwargs_para_funcao_servico
        )
        
        logger.info(f"Tarefa Background {log_entry_prefix}: Resultado Gemini para produto {produto_id} (truncado): {str(resultado_ia)[:200]}...")

        update_data_final_dict: Dict[str, Any] = {}
        log_final_obj = list(db_produto.log_processamento or [])
        
        if resultado_ia and ((isinstance(resultado_ia, str) and resultado_ia.strip()) or (isinstance(resultado_ia, list) and resultado_ia)):
            if campo_produto_para_atualizar_com_resultado:
                update_data_final_dict[campo_produto_para_atualizar_com_resultado] = resultado_ia

            if status_field_to_update: 
                update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.CONCLUIDO
            log_final_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Geração com Gemini concluída com sucesso."})
        else:
            if status_field_to_update: 
                update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.FALHA
            log_final_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Falha na geração (resultado vazio ou IA não pôde gerar)."})
            logger.warning(f"Tarefa Background {log_entry_prefix}: Gemini não retornou resultado válido para produto {produto_id}.")
        
        update_data_final_dict["log_processamento"] = log_final_obj
        if update_data_final_dict:
             crud_produtos.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_final_dict))
        logger.info(f"Tarefa Background {log_entry_prefix}: Produto {produto_id} atualizado com resultado e status final.")

    except HTTPException as http_exc:
        logger.error(f"Tarefa Background {log_entry_prefix}: HTTPException para produto {produto_id}: {http_exc.detail}")
        if db_produto and status_field_to_update:
            log_erro_obj = list(db_produto.log_processamento or [])
            log_erro_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Falha ({http_exc.status_code}) - {http_exc.detail}"})
            update_data_falha_http = {
                status_field_to_update: models.StatusGeracaoIAEnum.FALHA,
                "log_processamento": log_erro_obj
            }
            crud_produtos.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_http))
    except Exception as e:
        import traceback
        logger.error(f"Tarefa Background {log_entry_prefix}: Erro inesperado para produto {produto_id}: {traceback.format_exc()}")
        if db_produto and status_field_to_update:
            log_erro_inesperado_obj = list(db_produto.log_processamento or [])
            log_erro_inesperado_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Erro crítico inesperado - {str(e)}"})
            update_data_falha_critica = {
                status_field_to_update: models.StatusGeracaoIAEnum.FALHA,
                "log_processamento": log_erro_inesperado_obj
            }
            crud_produtos.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_critica))
    finally:
        logger.info(f"Tarefa Background {log_entry_prefix}: Finalizando para produto ID: {produto_id}")
        db.close()

# --- Endpoints Legados (OpenAI) ---

@router.post("/titulos/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, deprecated=True)
async def agendar_geracao_novos_titulos_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """(Legado) Agenda a geração de títulos de produto usando a API OpenAI."""
    db_produto_check = crud_produtos.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")
    
    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="titulo",
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_titulos_com_openai,
        num_titulos=num_titulos
    )
    return {"msg": f"Geração de títulos (OpenAI) para o produto ID {produto_id} agendada."}

@router.post("/descricao/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, deprecated=True)
async def agendar_geracao_nova_descricao_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """(Legado) Agenda a geração de descrição de produto usando a API OpenAI."""
    db_produto_check = crud_produtos.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")
        
    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="descricao",
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_descricao_com_openai,
        tamanho_palavras=tamanho_palavras
    )
    return {"msg": f"Geração de descrição (OpenAI) para o produto ID {produto_id} agendada."}


# --- NOVOS Endpoints para Gemini ---

@router.post("/titulos/gemini/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED)
async def agendar_geracao_novos_titulos_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """Agenda a geração de títulos de produto usando a API Gemini."""
    db_produto_check = crud_produtos.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    # limit_service.verificar_limite_uso(db, current_user, "titulo") # Verificação de limite

    update_data_pendente = {"status_titulo_ia": models.StatusGeracaoIAEnum.PENDENTE}
    crud_produtos.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_pendente))
    
    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="titulo",
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_titulos_com_gemini,
        num_titulos=num_titulos
    )
    return {"msg": f"Geração de títulos com Gemini para o produto ID {produto_id} foi agendada."}

@router.post("/descricao/gemini/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED)
async def agendar_geracao_nova_descricao_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """Agenda a geração de descrição de produto usando a API Gemini."""
    db_produto_check = crud_produtos.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    # limit_service.verificar_limite_uso(db, current_user, "descricao") # Verificação de limite
    
    update_data_pendente = {"status_descricao_ia": models.StatusGeracaoIAEnum.PENDENTE}
    crud_produtos.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_pendente))

    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="descricao",
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_descricao_com_gemini,
        tamanho_palavras=tamanho_palavras
    )
    return {"msg": f"Geração de descrição com Gemini para o produto ID {produto_id} foi agendada."}

# --- Endpoint Síncrono para Sugestões de Atributos com Gemini ---
@router.post("/sugerir-atributos-gemini/{produto_id}", response_model=schemas.SugestoesAtributosResponse)
async def sugerir_atributos_para_produto_com_gemini(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """
    Obtém sugestões de valores para os atributos de um produto específico usando a API Gemini.
    Este endpoint é síncrono e retorna as sugestões diretamente.
    """
    try:
        sugestoes_response = await ia_generation_service.sugerir_valores_atributos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=current_user
        )
        return sugestoes_response
    except HTTPException as e:
        raise e 
    except Exception as e:
        logger.error(f"Erro no endpoint sugerir_atributos_para_produto_com_gemini: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado: {str(e)}"
        )

