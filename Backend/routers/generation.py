"""Camada de transporte HTTP para o dominio 'generation'."""

import logging
from fastapi import APIRouter, BackgroundTasks, Body, Depends, HTTPException, Query, status
from typing import List
from pydantic import BaseModel as _PydanticBase
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)
from Backend.application.services.channel_content_service import (
    ChannelContentService,
    CANAL_LABELS,
    VALID_CANAIS,
)
from Backend.application.services.generation_scheduling_service import GenerationSchedulingService
from Backend.application.services.generation_task_service import GenerationTaskService
from Backend.application.services.ia_generation_service import IAGenerationService
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.adapters.limit_adapter import LimitServiceAdapter
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
        """Initialize injected dependencies and runtime configuration for Generation Request Service."""
        self._session = session
        self._ia_generation_service = ServiceContainerDependencySupport.build_ia_generation_service()
        self._basic_generation_service = BasicContentGenerationService()
        self._generation_task_service = GenerationTaskService(
            session_provider=ServiceContainerDependencySupport.get_background_session_provider(),
            user_repository_factory=UserRepository,
            product_repository_factory=ProductRepository,
            models=models,
            schemas=schemas,
            logger=logger,
        )
        self._generation_scheduling_service = GenerationSchedulingService(
            product_repository=ProductRepository(self._session),
            schemas=schemas,
            models=models,
        )
        self._limit_adapter = LimitServiceAdapter()

    def _check_ia_limit(self, *, user: models.User, tipo: str) -> None:
        """Raise HTTP 403 if the user has exceeded their IA generation limit."""
        if getattr(user, "plano", None) is None and getattr(user, "plano_id", None) is None:
            return
        self._limit_adapter.verificar_limite_uso(self._session, user, tipo)

    def _validate_product_access(self, *, produto_id: int, current_user: models.User):
        """Handle Validate product access in this request workflow."""
        return self._generation_scheduling_service.validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )

    def _mark_pending_status(self, *, db_produto, generation_type: str) -> None:
        """Handle Mark pending status in this request workflow."""
        self._generation_scheduling_service.mark_pending_status(
            db_produto=db_produto,
            generation_type=generation_type,
        )

    async def tarefa_processar_geracao_e_registrar_uso(
        self,
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        funcao_geracao_ia_no_servico,
        funcao_geracao_fallback_no_servico=None,
        num_titulos: int | None = None,
        tamanho_palavras: int | None = None,
        template_titulo: str | None = None,
        template_descricao: str | None = None,
    ) -> None:
        """Handle Tarefa processar geracao e registrar uso in this request workflow."""
        await self._generation_task_service.run_generation_task(
            user_id=user_id,
            produto_id=produto_id,
            tipo_geracao_principal=tipo_geracao_principal,
            funcao_geracao_ia_no_servico=funcao_geracao_ia_no_servico,
            funcao_geracao_fallback_no_servico=funcao_geracao_fallback_no_servico,
            num_titulos=num_titulos,
            tamanho_palavras=tamanho_palavras,
            template_titulo=template_titulo,
            template_descricao=template_descricao,
        )

    def agendar_geracao_novos_titulos_openai(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        current_user: models.User,
    ):
        """Handle Agendar geracao novos titulos openai in this request workflow."""
        self._check_ia_limit(user=current_user, tipo="titulo")
        self._validate_product_access(produto_id=produto_id, current_user=current_user)
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=self._ia_generation_service.gerar_titulos_com_openai,
            generation_provider_key="openai_title",
            fallback_generation_func=self._basic_generation_service.gerar_titulos_basicos,
            fallback_generation_provider_key="basic_title",
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
        """Handle Agendar geracao nova descricao openai in this request workflow."""
        self._check_ia_limit(user=current_user, tipo="descricao")
        self._validate_product_access(produto_id=produto_id, current_user=current_user)
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="descricao",
            generation_func=self._ia_generation_service.gerar_descricao_com_openai,
            generation_provider_key="openai_description",
            fallback_generation_func=self._basic_generation_service.gerar_descricao_basica,
            fallback_generation_provider_key="basic_description",
            tamanho_palavras=tamanho_palavras,
        )
        return {"msg": f"Geracao de descricao (OpenAI) para o produto ID {produto_id} agendada."}

    def agendar_geracao_novos_titulos_basico(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        template_titulo: str | None = None,
        current_user: models.User,
    ):
        """Agendar geracao de titulos no pipeline basico sem IA externa."""
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="titulo")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=self._basic_generation_service.gerar_titulos_basicos,
            generation_provider_key="basic_title",
            num_titulos=num_titulos,
            template_titulo=template_titulo,
        )
        return {
            "msg": (
                f"Geracao de titulos (Basico) para o produto ID {produto_id} "
                "foi agendada."
            )
        }

    def agendar_geracao_nova_descricao_basica(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        tamanho_palavras: int,
        template_descricao: str | None = None,
        current_user: models.User,
    ):
        """Agendar geracao de descricao no pipeline basico sem IA externa."""
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="descricao")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="descricao",
            generation_func=self._basic_generation_service.gerar_descricao_basica,
            generation_provider_key="basic_description",
            tamanho_palavras=tamanho_palavras,
            template_descricao=template_descricao,
        )
        return {
            "msg": (
                f"Geracao de descricao (Basico) para o produto ID {produto_id} "
                "foi agendada."
            )
        }

    def agendar_geracao_novos_titulos_gemini(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        num_titulos: int,
        current_user: models.User,
    ):
        """Handle Agendar geracao novos titulos gemini in this request workflow."""
        self._check_ia_limit(user=current_user, tipo="titulo")
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="titulo")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="titulo",
            generation_func=self._ia_generation_service.gerar_titulos_com_gemini,
            generation_provider_key="gemini_title",
            fallback_generation_func=self._basic_generation_service.gerar_titulos_basicos,
            fallback_generation_provider_key="basic_title",
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
        """Handle Agendar geracao nova descricao gemini in this request workflow."""
        self._check_ia_limit(user=current_user, tipo="descricao")
        db_produto = self._validate_product_access(
            produto_id=produto_id,
            current_user=current_user,
        )
        self._mark_pending_status(db_produto=db_produto, generation_type="descricao")
        self._generation_scheduling_service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=self.tarefa_processar_geracao_e_registrar_uso,
            user_id=current_user.id,
            produto_id=produto_id,
            generation_type="descricao",
            generation_func=self._ia_generation_service.gerar_descricao_com_gemini,
            generation_provider_key="gemini_description",
            fallback_generation_func=self._basic_generation_service.gerar_descricao_basica,
            fallback_generation_provider_key="basic_description",
            tamanho_palavras=tamanho_palavras,
        )
        return {"msg": f"Geracao de descricao com Gemini para o produto ID {produto_id} foi agendada."}

    async def sugerir_atributos_para_produto_com_gemini(
        self,
        *,
        produto_id: int,
        current_user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        """Handle Sugerir atributos para produto com gemini in this request workflow."""
        try:
            return await self._ia_generation_service.sugerir_valores_atributos_com_gemini(
                session=self._session,
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
                detail="Ocorreu um erro interno ao processar a solicitacao.",
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
    """Handle Agendar geracao novos titulos openai in this request workflow."""
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
    """Handle Agendar geracao nova descricao openai in this request workflow."""
    return request_service.agendar_geracao_nova_descricao_openai(
        produto_id=produto_id,
        background_tasks=background_tasks,
        tamanho_palavras=tamanho_palavras,
        current_user=current_user,
    )


@router.post(
    "/titulos/basico/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_novos_titulos_basico(
    produto_id: int,
    background_tasks: BackgroundTasks,
    num_titulos: int = Query(5, ge=1, le=10),
    template: str | None = Query(None, max_length=2000),
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Agendar geracao basica de titulos sem IA externa."""
    return request_service.agendar_geracao_novos_titulos_basico(
        produto_id=produto_id,
        background_tasks=background_tasks,
        num_titulos=num_titulos,
        template_titulo=template,
        current_user=current_user,
    )


@router.post(
    "/descricao/basico/{produto_id}",
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
)
async def agendar_geracao_nova_descricao_basica(
    produto_id: int,
    background_tasks: BackgroundTasks,
    tamanho_palavras: int = Query(150, ge=50, le=500),
    template: str | None = Query(None, max_length=2000),
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Agendar geracao basica de descricao sem IA externa."""
    return request_service.agendar_geracao_nova_descricao_basica(
        produto_id=produto_id,
        background_tasks=background_tasks,
        tamanho_palavras=tamanho_palavras,
        template_descricao=template,
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
    """Handle Agendar geracao novos titulos gemini in this request workflow."""
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
    """Handle Agendar geracao nova descricao gemini in this request workflow."""
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
    """Handle Sugerir atributos para produto com gemini in this request workflow."""
    return await request_service.sugerir_atributos_para_produto_com_gemini(
        produto_id=produto_id,
        current_user=current_user,
    )


class BatchGenerationRequest(_PydanticBase):
    """Payload used to trigger batch title or description generation."""

    produto_ids: List[int]
    tipo: str          # "titulo" | "descricao"
    provider: str      # "basico" | "openai" | "gemini"
    num_titulos: int = 3
    tamanho_palavras: int = 150


class BatchGenerationResponse(_PydanticBase):
    """Response returned after scheduling batch generation for multiple products."""

    agendados: int
    ignorados: int
    detalhes: List[str]


@router.post("/batch", response_model=BatchGenerationResponse, status_code=status.HTTP_202_ACCEPTED)
async def batch_generation(
    payload: BatchGenerationRequest,
    background_tasks: BackgroundTasks,
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Agenda geração em lote para múltiplos produtos."""
    tipo = payload.tipo.lower()
    provider = payload.provider.lower()

    if tipo not in ("titulo", "descricao"):
        raise HTTPException(status_code=400, detail="tipo deve ser 'titulo' ou 'descricao'.")
    if provider not in ("basico", "openai", "gemini"):
        raise HTTPException(status_code=400, detail="provider deve ser 'basico', 'openai' ou 'gemini'.")

    # Verifica limite uma vez antes do lote
    request_service._check_ia_limit(user=current_user, tipo=tipo)

    agendados = 0
    ignorados = 0
    detalhes: List[str] = []

    for produto_id in payload.produto_ids:
        try:
            if tipo == "titulo":
                if provider == "openai":
                    request_service.agendar_geracao_novos_titulos_openai(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        num_titulos=payload.num_titulos,
                        current_user=current_user,
                    )
                elif provider == "gemini":
                    request_service.agendar_geracao_novos_titulos_gemini(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        num_titulos=payload.num_titulos,
                        current_user=current_user,
                    )
                else:
                    request_service.agendar_geracao_novos_titulos_basico(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        num_titulos=payload.num_titulos,
                        current_user=current_user,
                    )
            else:
                if provider == "openai":
                    request_service.agendar_geracao_nova_descricao_openai(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        tamanho_palavras=payload.tamanho_palavras,
                        current_user=current_user,
                    )
                elif provider == "gemini":
                    request_service.agendar_geracao_nova_descricao_gemini(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        tamanho_palavras=payload.tamanho_palavras,
                        current_user=current_user,
                    )
                else:
                    request_service.agendar_geracao_nova_descricao_basica(
                        produto_id=produto_id,
                        background_tasks=background_tasks,
                        tamanho_palavras=payload.tamanho_palavras,
                        current_user=current_user,
                    )
            agendados += 1
        except HTTPException as exc:
            ignorados += 1
            detalhes.append(f"Produto {produto_id}: {exc.detail}")

    return BatchGenerationResponse(agendados=agendados, ignorados=ignorados, detalhes=detalhes)


@router.post("/canal/{canal}/{produto_id}/", response_model=schemas.ConteudoCanaisResponse)
async def gerar_conteudo_canal(
    canal: str,
    produto_id: int,
    gerar_titulo: bool = Query(True),
    gerar_descricao: bool = Query(True),
    request_service: GenerationRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Generate channel-specific title and description for a product."""
    request_service._check_ia_limit(user=current_user, tipo="titulo")
    channel_service = ChannelContentService(db=request_service._session, models=models)
    try:
        result = await channel_service.generate_canal_content(
            produto_id=produto_id,
            canal=canal,
            user=current_user,
            gerar_titulo=gerar_titulo,
            gerar_descricao=gerar_descricao,
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/canal/config/")
def get_canal_config():
    """Return available publication channels."""
    return {
        "canais": [
            {"value": k, "label": v} for k, v in CANAL_LABELS.items()
        ]
    }


# Compatibilidade de rota para clientes com barra final.
router.add_api_route(
    "/titulos/openai/{produto_id}/",
    agendar_geracao_novos_titulos_openai,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
    deprecated=True,
)
router.add_api_route(
    "/descricao/openai/{produto_id}/",
    agendar_geracao_nova_descricao_openai,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
    deprecated=True,
)
router.add_api_route(
    "/titulos/basico/{produto_id}/",
    agendar_geracao_novos_titulos_basico,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
router.add_api_route(
    "/descricao/basico/{produto_id}/",
    agendar_geracao_nova_descricao_basica,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
router.add_api_route(
    "/titulos/gemini/{produto_id}/",
    agendar_geracao_novos_titulos_gemini,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
router.add_api_route(
    "/descricao/gemini/{produto_id}/",
    agendar_geracao_nova_descricao_gemini,
    methods=["POST"],
    response_model=schemas.Msg,
    status_code=status.HTTP_202_ACCEPTED,
    include_in_schema=False,
)
router.add_api_route(
    "/sugerir-atributos-gemini/{produto_id}/",
    sugerir_atributos_para_produto_com_gemini,
    methods=["POST"],
    response_model=schemas.SugestoesAtributosResponse,
    include_in_schema=False,
)
# Non-trailing-slash compat for channel routes (primary routes registered with trailing slash above)
router.add_api_route(
    "/canal/config",
    get_canal_config,
    methods=["GET"],
    include_in_schema=False,
)
router.add_api_route(
    "/canal/{canal}/{produto_id}",
    gerar_conteudo_canal,
    methods=["POST"],
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
