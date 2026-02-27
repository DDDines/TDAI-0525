# catalogai_project/Backend/routers/web_enrichment.py
from typing import List, Dict, Any, Optional, Tuple
import json
import re

from fastapi import APIRouter, Depends, status, BackgroundTasks, Query
from sqlalchemy.exc import SQLAlchemyError

from Backend import crud_users
from Backend import crud_produtos
from Backend import crud
from Backend import models
from Backend import schemas
from Backend.core.deprecation import deprecated_legacy_service_proxy
from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.services import (
    WebEnrichmentContentQualityService,
    WebEnrichmentNormalizationService,
    WebEnrichmentPayloadService,
    WebEnrichmentRelevanceService,
    WebEnrichmentStartService,
    WebEnrichmentTaskRunner,
)
from Backend.application.services.service_container import service_container
from Backend.database import SessionLocal
from Backend.infrastructure.legacy.web_data_extractor_bridge import (
    LegacyWebDataExtractorBridge,
)

from .auth_utils import get_current_active_user
from Backend.core.config import settings
from Backend.core.logging_config import get_logger

router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(get_current_active_user)],
    # Evita 307 por barra final/ausente que pode perder Authorization em alguns clientes.
    redirect_slashes=False,
)

logger = get_logger(__name__)
relevance_service = WebEnrichmentRelevanceService()
web_normalization_service = WebEnrichmentNormalizationService()
web_content_quality_service = WebEnrichmentContentQualityService(
    normalization_service=web_normalization_service
)
web_payload_service = WebEnrichmentPayloadService(
    normalization_service=web_normalization_service
)
web_extractor = service_container.web_data_extractor
legacy_web_extractor = LegacyWebDataExtractorBridge()
web_enrichment_start_service = WebEnrichmentStartService(
    crud_produtos=crud_produtos,
    models=models,
)


def _normalize_human_text(value: Any) -> str:
    return web_normalization_service.normalize_human_text(value)


def _is_source_relevant_for_product(
    db_produto_obj: models.Produto,
    *,
    source_name: Any,
    source_desc: Any,
    source_url: str,
) -> bool:
    return relevance_service.is_source_relevant_for_product(
        db_produto_obj,
        source_name=source_name,
        source_desc=source_desc,
        source_url=source_url,
    )


def _extrair_dominio_fornecedor(site_url: Any) -> str:
    return relevance_service.extract_supplier_domain(site_url)


def _priorizar_urls_para_enriquecimento(
    db_produto_obj: models.Produto,
    urls_candidatas: List[str],
    fornecedor_domain: str = "",
    max_urls: int = 4,
) -> Tuple[List[str], List[Tuple[str, int]]]:
    return relevance_service.prioritize_urls_for_enrichment(
        db_produto_obj,
        urls_candidatas,
        fornecedor_domain=fornecedor_domain,
        max_urls=max_urls,
    )


def _is_meaningful_extracted_text(value: Any) -> bool:
    return web_content_quality_service.is_meaningful_extracted_text(value)


def _metadata_has_minimum_signal(metadata: Dict[str, Any]) -> bool:
    return web_content_quality_service.metadata_has_minimum_signal(metadata)


def _build_payload_enriquecimento_visivel(
    db_produto_obj: models.Produto,
    dados_extraidos_agregados: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    return web_payload_service.build_payload_enriquecimento_visivel(
        db_produto_obj,
        dados_extraidos_agregados,
    )


web_enrichment_task_runner = WebEnrichmentTaskRunner(
    logger=logger,
    SQLAlchemyError=SQLAlchemyError,
    crud_users=crud_users,
    crud_produtos=crud_produtos,
    crud=crud,
    models=models,
    schemas=schemas,
    web_extractor=web_extractor,
    legacy_web_extractor=legacy_web_extractor,
    oop_web_extractor=web_extractor,
    settings=settings,
    json_module=json,
    re_module=re,
    normalize_human_text=_normalize_human_text,
    build_payload_enriquecimento_visivel=_build_payload_enriquecimento_visivel,
    extrair_dominio_fornecedor=_extrair_dominio_fornecedor,
    priorizar_urls_para_enriquecimento=_priorizar_urls_para_enriquecimento,
    is_meaningful_extracted_text=_is_meaningful_extracted_text,
    metadata_has_minimum_signal=_metadata_has_minimum_signal,
    is_source_relevant_for_product=_is_source_relevant_for_product,
)


class _WebEnrichmentRouterRuntime:
    """Runtime OO para rotas de enriquecimento web."""

    async def execute_legacy_task(
        self,
        *,
        db_session_factory,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        await web_enrichment_task_runner.execute_legacy(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    async def execute_oop_task(self, **task_kwargs) -> None:
        await web_enrichment_task_runner.execute_oop(**task_kwargs)

    def validate_start_preconditions(
        self,
        *,
        db_session_factory,
        produto_id: int,
        current_user: models.User,
    ) -> None:
        web_enrichment_start_service.validate_start_preconditions(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            current_user=current_user,
        )

    def dispatch_start(
        self,
        *,
        background_tasks: BackgroundTasks,
        db_session_factory,
        command: WebEnrichmentStartCommand,
        legacy_executor,
        oop_executor,
    ) -> None:
        web_enrichment_start_service.dispatch_start(
            background_tasks=background_tasks,
            db_session_factory=db_session_factory,
            command=command,
            legacy_executor=legacy_executor,
            oop_executor=oop_executor,
        )


class _WebEnrichmentRouterWorkflow:
    def __init__(self, runtime: Optional["_WebEnrichmentRouterRuntime"] = None) -> None:
        self._runtime = runtime or _WebEnrichmentRouterRuntime()

    async def tarefa_enriquecer_produto_web(
        self,
        db_session_factory,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ):
        await self._runtime.execute_legacy_task(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    async def oop_tarefa_enriquecer_produto_web(self, **task_kwargs):
        """Executor OOP dedicado (modo oop), separado do legado para comparacao futura."""
        await self._runtime.execute_oop_task(**task_kwargs)

    def iniciar_enriquecimento_produto_web(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        current_user: models.User,
        termos_busca_override: Optional[str] = None,
    ) -> Dict[str, str]:
        self._runtime.validate_start_preconditions(
            db_session_factory=SessionLocal,
            produto_id=produto_id,
            current_user=current_user,
        )

        command = WebEnrichmentStartCommand(
            produto_id=produto_id,
            user_id=current_user.id,
            termos_busca_override=termos_busca_override,
        )

        self._runtime.dispatch_start(
            background_tasks=background_tasks,
            db_session_factory=SessionLocal,
            command=command,
            legacy_executor=self.tarefa_enriquecer_produto_web,
            oop_executor=self.oop_tarefa_enriquecer_produto_web,
        )
        return {
            "msg": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."
        }


web_enrichment_router_runtime = _WebEnrichmentRouterRuntime()
web_enrichment_router_workflow = _WebEnrichmentRouterWorkflow(
    runtime=web_enrichment_router_runtime
)


async def _tarefa_enriquecer_produto_web(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None,
):
    await web_enrichment_router_workflow.tarefa_enriquecer_produto_web(
        db_session_factory=db_session_factory,
        produto_id=produto_id,
        user_id=user_id,
        termos_busca_override=termos_busca_override,
    )


async def _oop_tarefa_enriquecer_produto_web(**task_kwargs):
    await web_enrichment_router_workflow.oop_tarefa_enriquecer_produto_web(**task_kwargs)


@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(
        None,
        description="Opcional: termos de busca especificos para o Google Search.",
    ),
):
    return web_enrichment_router_workflow.iniciar_enriquecimento_produto_web(
        produto_id=produto_id,
        background_tasks=background_tasks,
        current_user=current_user,
        termos_busca_override=termos_busca_override,
    )


router.add_api_route(
    "/produto/{produto_id}/",
    iniciar_enriquecimento_produto_web_endpoint,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.Msg,
    include_in_schema=False,
)


class WebEnrichmentRouterLegacyService:
    async def tarefa_enriquecer_produto_web(self, *args, **kwargs):
        return await web_enrichment_router_workflow.tarefa_enriquecer_produto_web(*args, **kwargs)

    async def oop_tarefa_enriquecer_produto_web(self, *args, **kwargs):
        return await web_enrichment_router_workflow.oop_tarefa_enriquecer_produto_web(*args, **kwargs)

    def iniciar_enriquecimento_produto_web(self, *args, **kwargs):
        return web_enrichment_router_workflow.iniciar_enriquecimento_produto_web(*args, **kwargs)


web_enrichment_router_legacy_service = deprecated_legacy_service_proxy(
    WebEnrichmentRouterLegacyService(),
    qualified_name="Backend.routers.web_enrichment.web_enrichment_router_legacy_service",
)
