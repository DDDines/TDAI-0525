# Backend/routers/generation.py

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import auth_utils
from .auth_utils import get_current_active_user
from Backend import crud_users
from Backend import crud_produtos
from Backend import models
from Backend import schemas
from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.service_container import service_container
from Backend.database import SessionLocal, get_db

logger = logging.getLogger(__name__)
ia_generation_service = service_container.ia_generation

generation_task_service = GenerationTaskService(
    crud_users=crud_users,
    crud_produtos=crud_produtos,
    models=models,
    schemas=schemas,
    logger=logger,
)
generation_scheduling_service = GenerationSchedulingService(
    crud_produtos=crud_produtos,
    schemas=schemas,
    models=models,
)

router = APIRouter(
    prefix="/geracao",
    tags=["Geracao de Conteudo com IA"],
    dependencies=[Depends(get_current_active_user)],
)


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


@router.post(
    "/titulos/openai/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
)
async def agendar_geracao_novos_titulos_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    generation_scheduling_service.validate_product_access(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )
    generation_scheduling_service.enqueue_generation_task(
        background_tasks=background_tasks,
        task_executor=_tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        generation_type="titulo",
        generation_func=ia_generation_service.gerar_titulos_com_openai,
        num_titulos=num_titulos,
    )
    return {"msg": f"Geracao de titulos (OpenAI) para o produto ID {produto_id} agendada."}


@router.post(
    "/descricao/openai/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    deprecated=True,
)
async def agendar_geracao_nova_descricao_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    generation_scheduling_service.validate_product_access(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )
    generation_scheduling_service.enqueue_generation_task(
        background_tasks=background_tasks,
        task_executor=_tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        generation_type="descricao",
        generation_func=ia_generation_service.gerar_descricao_com_openai,
        tamanho_palavras=tamanho_palavras,
    )
    return {
        "msg": f"Geracao de descricao (OpenAI) para o produto ID {produto_id} agendada."
    }


@router.post(
    "/titulos/gemini/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_novos_titulos_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto_check = generation_scheduling_service.validate_product_access(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )
    # limit_service.verificar_limite_uso(db, current_user, "titulo")
    generation_scheduling_service.mark_pending_status(
        db=db,
        db_produto=db_produto_check,
        generation_type="titulo",
    )
    generation_scheduling_service.enqueue_generation_task(
        background_tasks=background_tasks,
        task_executor=_tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        generation_type="titulo",
        generation_func=ia_generation_service.gerar_titulos_com_gemini,
        num_titulos=num_titulos,
    )
    return {
        "msg": f"Geracao de titulos com Gemini para o produto ID {produto_id} foi agendada."
    }


@router.post(
    "/descricao/gemini/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_nova_descricao_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto_check = generation_scheduling_service.validate_product_access(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )
    # limit_service.verificar_limite_uso(db, current_user, "descricao")
    generation_scheduling_service.mark_pending_status(
        db=db,
        db_produto=db_produto_check,
        generation_type="descricao",
    )
    generation_scheduling_service.enqueue_generation_task(
        background_tasks=background_tasks,
        task_executor=_tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        generation_type="descricao",
        generation_func=ia_generation_service.gerar_descricao_com_gemini,
        tamanho_palavras=tamanho_palavras,
    )
    return {
        "msg": f"Geracao de descricao com Gemini para o produto ID {produto_id} foi agendada."
    }


@router.post(
    "/sugerir-atributos-gemini/{produto_id}",
    response_model=schemas.SugestoesAtributosResponse,
)
async def sugerir_atributos_para_produto_com_gemini(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        sugestoes_response = await ia_generation_service.sugerir_valores_atributos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=current_user,
        )
        return sugestoes_response
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        logger.error(
            "Erro no endpoint sugerir_atributos_para_produto_com_gemini: %s",
            exc,
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado: {str(exc)}",
        )
