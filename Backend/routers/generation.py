# Backend/routers/generation.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List
import logging # <-- ADICIONADO

from . import auth_utils
from Backend import crud_users
from Backend import crud_produtos
from Backend import models
from Backend import schemas
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.service_container import service_container
from Backend.database import get_db, SessionLocal
from .auth_utils import get_current_active_user

# Configuração do logger para este módulo
logger = logging.getLogger(__name__) # <-- ADICIONADO
ia_generation_service = service_container.ia_generation
limit_service = service_container.limit
generation_task_service = GenerationTaskService(
    crud_users=crud_users,
    crud_produtos=crud_produtos,
    models=models,
    schemas=schemas,
    logger=logger,
)

router = APIRouter(
    prefix="/geracao",
    tags=["Geração de Conteúdo com IA"],
    dependencies=[Depends(get_current_active_user)],
)

# Função auxiliar delegada para o serviço OO de geração
async def _tarefa_processar_geracao_e_registrar_uso(
    db_session_factory,
    user_id: int,
    produto_id: int,
    tipo_geracao_principal: str,
    funcao_geracao_ia_no_servico,
    **kwargs_para_funcao_servico,
):
    await generation_task_service.run_generation_task(
        db_session_factory=db_session_factory,
        user_id=user_id,
        produto_id=produto_id,
        tipo_geracao_principal=tipo_geracao_principal,
        funcao_geracao_ia_no_servico=funcao_geracao_ia_no_servico,
        **kwargs_para_funcao_servico,
    )

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

