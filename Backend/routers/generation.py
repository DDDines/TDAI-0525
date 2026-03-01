"""Camada de transporte HTTP para o dominio 'generation'."""

import logging
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.generation_scheduling_service import GenerationSchedulingService
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.ia_generation_service import IAGenerationService
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

from . import auth_utils


logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/geracao",
    tags=["Geracao de Conteudo com IA"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class GenerationRequestService:
    """Servico request-scoped do router de geracao IA."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        self._db = session
        self._db_session_factory = ServiceContainerDependencySupport.get_background_db_session_factory()
        self._ia_generation_service = IAGenerationService()
        self._generation_task_service = GenerationTaskService(
            user_repository_cls=UserRepository,
            product_repository_cls=ProductRepository,
            models=models,
            schemas=schemas,
            logger=logger,
        )
        self._generation_scheduling_service = GenerationSchedulingService(
            product_repository_cls=ProductRepository,
            schemas=schemas,
            models=models,
        )

    def _product_repo(self) -> ProductRepository:
        return ProductRepository(self._db)

    def _validate_product_access(self, *, produto_id: int, current_user: models.User):
        return self._generation_scheduling_service.validate_product_access(
            product_repo=self._product_repo(),
            produto_id=produto_id,
            current_user=current_user,
        )

    def _mark_pending_status(self, *, db_produto, generation_type: str) -> None:
        self._generation_scheduling_service.mark_pending_status(
            product_repo=self._product_repo(),
            db_produto=db_produto,
            generation_type=generation_type,
        )

    async def tarefa_processar_geracao_e_registrar_uso(
        self,
        db_session_factory,
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        funcao_geracao_ia_no_servico,
        **kwargs_para_funcao_servico,
    ) -> None:
        await self._generation_task_service.run_generation_task(
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
        current_user: models.User,
    ):
        self._validate_product_access(produto_id=produto_id, current_user=current_user)
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            db_session_factory=self._db_session_factory,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=self._ia_generation_service.gerar_titulos_com_openai,
            num_titulos=num_titulos,
        )
        return {"msg": f"Geracao de titulos (OpenAI) para o produto ID {produto_id} agendada."}

    def agendar_geracao_nova_descricao_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        current_user: models.User,
    ):
        self._validate_product_access(produto_id=produto_id, current_user=current_user)
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            db_session_factory=self._db_session_factory,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="descricao",
            generation_func=self._ia_generation_service.gerar_descricao_com_openai,
            tamanho_palavras=tamanho_palavras,
        )
        return {"msg": f"Geracao de descricao (OpenAI) para o produto ID {produto_id} agendada."}

    def agendar_geracao_novos_titulos_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        current_user: models.User,
    ):
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="titulo")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            db_session_factory=self._db_session_factory,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=self._ia_generation_service.gerar_titulos_com_gemini,
            num_titulos=num_titulos,
        )
        return {"msg": f"Geracao de titulos com Gemini para o produto ID {produto_id} foi agendada."}

    def agendar_geracao_nova_descricao_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        current_user: models.User,
    ):
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="descricao")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            db_session_factory=self._db_session_factory,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="descricao",
            generation_func=self._ia_generation_service.gerar_descricao_com_gemini,
            tamanho_palavras=tamanho_palavras,
        )
        return {"msg": f"Geracao de descricao com Gemini para o produto ID {produto_id} foi agendada."}

    async def sugerir_atributos_para_produto_com_gemini(
        self,
        *,
        produto_id: int,
        current_user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        try:
            return await self._ia_generation_service.sugerir_valores_atributos_com_gemini(
                db=self._db,
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
            ) from exc


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
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    return request_service.agendar_geracao_novos_titulos_openai(
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
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    return request_service.agendar_geracao_nova_descricao_openai(
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
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    return request_service.agendar_geracao_novos_titulos_gemini(
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
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    return request_service.agendar_geracao_nova_descricao_gemini(
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
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    return await request_service.sugerir_atributos_para_produto_com_gemini(
        produto_id=produto_id,
        current_user=current_user,
    )
