"""Camada de transporte HTTP para o dominio 'generation'."""
# Backend/routers/generation.py

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from . import auth_utils
from .auth_utils import get_current_active_user
from Backend import models
from Backend import schemas
from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.ia_generation_service import IAGenerationService
from Backend.application.services.service_container import (
    build_request_scoped_dependency,
)
from Backend.database import SessionLocal
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/geracao",
    tags=["Geracao de Conteudo com IA"],
    dependencies=[Depends(get_current_active_user)],
)


class _GenerationRouterWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'generation'."""
    def __init__(self, runtime: Optional["_GenerationRouterRuntime"] = None) -> None:
        self._runtime = runtime or _GenerationRouterRuntime()

    def _resolve_ia_generation_service(self) -> IAGenerationService:
        resolver = getattr(self._runtime, "get_ia_generation_service", None)
        if callable(resolver):
            return resolver()
        return IAGenerationService()

    async def tarefa_processar_geracao_e_registrar_uso(
        self,
        db_session_factory,
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        funcao_geracao_ia_no_servico,
        **kwargs_para_funcao_servico,
    ):
        await self._runtime.run_generation_task(
            db_session_factory=db_session_factory,
            user_id=user_id,
            produto_id=produto_id,
            tipo_geracao_principal=tipo_geracao_principal,
            funcao_geracao_ia_no_servico=funcao_geracao_ia_no_servico,
            **kwargs_para_funcao_servico,
        )

    def agendar_geracao_novos_titulos_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        db: Session,
        current_user: models.User,
    ) -> Dict[str, str]:
        ia_generation_service = self._resolve_ia_generation_service()
        self._runtime.validate_product_access(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )
        self._runtime.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            db_session_factory=SessionLocal,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=ia_generation_service.gerar_titulos_com_openai,
            num_titulos=num_titulos,
        )
        return {"msg": f"Geracao de titulos (OpenAI) para o produto ID {produto_id} agendada."}

    def agendar_geracao_nova_descricao_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        db: Session,
        current_user: models.User,
    ) -> Dict[str, str]:
        ia_generation_service = self._resolve_ia_generation_service()
        self._runtime.validate_product_access(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )
        self._runtime.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
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

    def agendar_geracao_novos_titulos_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        db: Session,
        current_user: models.User,
    ) -> Dict[str, str]:
        ia_generation_service = self._resolve_ia_generation_service()
        db_produto_check = self._runtime.validate_product_access(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )
        self._runtime.mark_pending_status(
            db=db,
            db_produto=db_produto_check,
            generation_type="titulo",
        )
        self._runtime.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
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

    def agendar_geracao_nova_descricao_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        db: Session,
        current_user: models.User,
    ) -> Dict[str, str]:
        ia_generation_service = self._resolve_ia_generation_service()
        db_produto_check = self._runtime.validate_product_access(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )
        self._runtime.mark_pending_status(
            db=db,
            db_produto=db_produto_check,
            generation_type="descricao",
        )
        self._runtime.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
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

    async def sugerir_atributos_para_produto_com_gemini(
        self,
        *,
        produto_id: int,
        db: Session,
        current_user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        try:
            return await self._runtime.sugerir_valores_atributos_com_gemini(
                db=db,
                produto_id=produto_id,
                user=current_user,
            )
        except HTTPException:
            raise
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


class _GenerationRouterRuntime:
    """Runtime OO para operaÃ§Ãµes do router de geraÃ§Ã£o IA."""

    def __init__(
        self,
        *,
        ia_generation_service: IAGenerationService | None = None,
        generation_task_service: GenerationTaskService | None = None,
        generation_scheduling_service: GenerationSchedulingService | None = None,
        product_repository_cls: type[ProductRepository] = ProductRepository,
    ) -> None:
        self._ia_generation_service = ia_generation_service or IAGenerationService()
        self._generation_task_service = generation_task_service or GenerationTaskService(
            user_repository_cls=UserRepository,
            product_repository_cls=product_repository_cls,
            models=models,
            schemas=schemas,
            logger=logger,
        )
        self._generation_scheduling_service = (
            generation_scheduling_service
            or GenerationSchedulingService(
                product_repository_cls=product_repository_cls,
                schemas=schemas,
                models=models,
            )
        )
        self._product_repository_cls = product_repository_cls

    def get_ia_generation_service(self) -> IAGenerationService:
        return self._ia_generation_service

    async def run_generation_task(self, **kwargs):
        await self._generation_task_service.run_generation_task(**kwargs)

    def validate_product_access(self, **kwargs):
        db = kwargs.pop("db")
        kwargs["product_repo"] = self._product_repository_cls(db)
        return self._generation_scheduling_service.validate_product_access(**kwargs)

    def mark_pending_status(self, **kwargs):
        db = kwargs.pop("db")
        kwargs["product_repo"] = self._product_repository_cls(db)
        return self._generation_scheduling_service.mark_pending_status(**kwargs)

    def enqueue_generation_task(self, **kwargs):
        return self._generation_scheduling_service.enqueue_generation_task(**kwargs)

    async def sugerir_valores_atributos_com_gemini(self, **kwargs):
        return await self._ia_generation_service.sugerir_valores_atributos_com_gemini(
            **kwargs
        )


GenerationRouterWorkflow = _GenerationRouterWorkflow


def get_generation_router_workflow() -> GenerationRouterWorkflow:
    """Factory de workflow OO para o modulo atual (get_generation_router_workflow)."""
    return GenerationRouterWorkflow(runtime=_GenerationRouterRuntime())


class _GenerationRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'generation'."""
    def __init__(self, db: Session, workflow: GenerationRouterWorkflow | None = None) -> None:
        self._db = db
        self._workflow = workflow or get_generation_router_workflow()

    def agendar_geracao_novos_titulos_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        current_user: models.User,
    ) -> Dict[str, str]:
        return self._workflow.agendar_geracao_novos_titulos_openai(
            produto_id=produto_id,
            background_tasks=background_tasks,
            num_titulos=num_titulos,
            db=self._db,
            current_user=current_user,
        )

    def agendar_geracao_nova_descricao_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        current_user: models.User,
    ) -> Dict[str, str]:
        return self._workflow.agendar_geracao_nova_descricao_openai(
            produto_id=produto_id,
            background_tasks=background_tasks,
            tamanho_palavras=tamanho_palavras,
            db=self._db,
            current_user=current_user,
        )

    def agendar_geracao_novos_titulos_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        current_user: models.User,
    ) -> Dict[str, str]:
        return self._workflow.agendar_geracao_novos_titulos_gemini(
            produto_id=produto_id,
            background_tasks=background_tasks,
            num_titulos=num_titulos,
            db=self._db,
            current_user=current_user,
        )

    def agendar_geracao_nova_descricao_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        current_user: models.User,
    ) -> Dict[str, str]:
        return self._workflow.agendar_geracao_nova_descricao_gemini(
            produto_id=produto_id,
            background_tasks=background_tasks,
            tamanho_palavras=tamanho_palavras,
            db=self._db,
            current_user=current_user,
        )

    async def sugerir_atributos_para_produto_com_gemini(
        self,
        *,
        produto_id: int,
        current_user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        return await self._workflow.sugerir_atributos_para_produto_com_gemini(
            produto_id=produto_id,
            db=self._db,
            current_user=current_user,
        )


_build_generation_request_workflow = build_request_scoped_dependency(
    lambda session: _GenerationRequestScope(db=session),
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
    request_workflow: _GenerationRequestScope = Depends(_build_generation_request_workflow),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (agendar_geracao_novos_titulos_openai)."""
    return request_workflow.agendar_geracao_novos_titulos_openai(
        produto_id=produto_id,
        background_tasks=background_tasks,
        num_titulos=num_titulos,
        current_user=current_user,
    )


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
    request_workflow: _GenerationRequestScope = Depends(_build_generation_request_workflow),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (agendar_geracao_nova_descricao_openai)."""
    return request_workflow.agendar_geracao_nova_descricao_openai(
        produto_id=produto_id,
        background_tasks=background_tasks,
        tamanho_palavras=tamanho_palavras,
        current_user=current_user,
    )


@router.post(
    "/titulos/gemini/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_novos_titulos_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(3, ge=1, le=10),
    request_workflow: _GenerationRequestScope = Depends(_build_generation_request_workflow),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (agendar_geracao_novos_titulos_gemini)."""
    return request_workflow.agendar_geracao_novos_titulos_gemini(
        produto_id=produto_id,
        background_tasks=background_tasks,
        num_titulos=num_titulos,
        current_user=current_user,
    )


@router.post(
    "/descricao/gemini/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_nova_descricao_gemini(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    request_workflow: _GenerationRequestScope = Depends(_build_generation_request_workflow),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (agendar_geracao_nova_descricao_gemini)."""
    return request_workflow.agendar_geracao_nova_descricao_gemini(
        produto_id=produto_id,
        background_tasks=background_tasks,
        tamanho_palavras=tamanho_palavras,
        current_user=current_user,
    )


@router.post(
    "/sugerir-atributos-gemini/{produto_id}",
    response_model=schemas.SugestoesAtributosResponse,
)
async def sugerir_atributos_para_produto_com_gemini(
    produto_id: int,
    request_workflow: _GenerationRequestScope = Depends(_build_generation_request_workflow),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (sugerir_atributos_para_produto_com_gemini)."""
    return await request_workflow.sugerir_atributos_para_produto_com_gemini(
        produto_id=produto_id,
        current_user=current_user,
    )






