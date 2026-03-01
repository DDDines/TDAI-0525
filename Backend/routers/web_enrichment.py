"""Camada de transporte HTTP para o dominio 'web_enrichment'."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.exc import SQLAlchemyError

from Backend import models
from Backend import schemas
from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.services.web_data_extractor import WebDataExtractorOrchestratorService
from Backend.application.services.web_enrichment_content_quality_service import (
    WebEnrichmentContentQualityService,
)
from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_payload_service import (
    WebEnrichmentPayloadService,
)
from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)
from Backend.application.services.web_enrichment_start_service import (
    WebEnrichmentStartService,
)
from Backend.application.services.web_enrichment_task_runner import (
    WebEnrichmentTaskRunner,
)
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.database import SessionLocal
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository

from .auth_utils import get_current_active_user

router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(get_current_active_user)],
    redirect_slashes=False,
)

logger = get_logger(__name__)


class _WebEnrichmentMappingRuntime:
    """Runtime OO para regras de mapeamento/qualidade do enriquecimento web."""

    def __init__(
        self,
        *,
        relevance_service: Optional[WebEnrichmentRelevanceService] = None,
        normalization_service: Optional[WebEnrichmentNormalizationService] = None,
        content_quality_service: Optional[WebEnrichmentContentQualityService] = None,
        payload_service: Optional[WebEnrichmentPayloadService] = None,
    ) -> None:
        self._normalization_service = normalization_service or WebEnrichmentNormalizationService()
        self._relevance_service = relevance_service or WebEnrichmentRelevanceService()
        self._content_quality_service = content_quality_service or WebEnrichmentContentQualityService(
            normalization_service=self._normalization_service
        )
        self._payload_service = payload_service or WebEnrichmentPayloadService(
            normalization_service=self._normalization_service
        )

    def normalize_human_text(self, value: Any) -> str:
        return self._normalization_service.normalize_human_text(value)

    def is_source_relevant_for_product(
        self,
        db_produto_obj: models.Produto,
        *,
        source_name: Any,
        source_desc: Any,
        source_url: str,
    ) -> bool:
        return self._relevance_service.is_source_relevant_for_product(
            db_produto_obj,
            source_name=source_name,
            source_desc=source_desc,
            source_url=source_url,
        )

    def extract_supplier_domain(self, site_url: Any) -> str:
        return self._relevance_service.extract_supplier_domain(site_url)

    def prioritize_urls_for_enrichment(
        self,
        db_produto_obj: models.Produto,
        urls_candidatas: List[str],
        *,
        fornecedor_domain: str = "",
        max_urls: int = 4,
    ) -> Tuple[List[str], List[Tuple[str, int]]]:
        return self._relevance_service.prioritize_urls_for_enrichment(
            db_produto_obj,
            urls_candidatas,
            fornecedor_domain=fornecedor_domain,
            max_urls=max_urls,
        )

    def is_meaningful_extracted_text(self, value: Any) -> bool:
        return self._content_quality_service.is_meaningful_extracted_text(value)

    def metadata_has_minimum_signal(self, metadata: Dict[str, Any]) -> bool:
        return self._content_quality_service.metadata_has_minimum_signal(metadata)

    def build_payload_enriquecimento_visivel(
        self,
        db_produto_obj: models.Produto,
        dados_extraidos_agregados: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        return self._payload_service.build_payload_enriquecimento_visivel(
            db_produto_obj,
            dados_extraidos_agregados,
        )


class _WebEnrichmentRouterRuntime:
    """Runtime OO para rotas de enriquecimento web."""

    def __init__(
        self,
        *,
        task_runner: Optional[WebEnrichmentTaskRunner] = None,
        start_service: Optional[WebEnrichmentStartService] = None,
        web_extractor: Optional[WebDataExtractorOrchestratorService] = None,
        mapping_runtime: Optional[_WebEnrichmentMappingRuntime] = None,
    ) -> None:
        self._mapping_runtime = mapping_runtime or _WebEnrichmentMappingRuntime()

        extractor_service = web_extractor or WebDataExtractorOrchestratorService(
            WebDataExtractorServiceAdapter()
        )

        self._task_runner = task_runner or WebEnrichmentTaskRunner(
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            user_repository=UserRepository,
            product_repository=ProductRepository,
            usage_repository=RegistroUsoIARepository,
            models=models,
            schemas=schemas,
            web_extractor=extractor_service,
            settings=settings,
            json_module=json,
            re_module=re,
            normalize_human_text=self._mapping_runtime.normalize_human_text,
            build_payload_enriquecimento_visivel=self._mapping_runtime.build_payload_enriquecimento_visivel,
            extrair_dominio_fornecedor=self._mapping_runtime.extract_supplier_domain,
            priorizar_urls_para_enriquecimento=self._mapping_runtime.prioritize_urls_for_enrichment,
            is_meaningful_extracted_text=self._mapping_runtime.is_meaningful_extracted_text,
            metadata_has_minimum_signal=self._mapping_runtime.metadata_has_minimum_signal,
            is_source_relevant_for_product=self._mapping_runtime.is_source_relevant_for_product,
        )
        self._start_service = start_service or WebEnrichmentStartService(
            product_repository=ProductRepository,
            models=models,
        )

    @property
    def mapping(self) -> _WebEnrichmentMappingRuntime:
        return self._mapping_runtime

    async def execute_task(
        self,
        *,
        db_session_factory,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> None:
        await self._task_runner.execute(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

    def validate_start_preconditions(
        self,
        *,
        db_session_factory,
        produto_id: int,
        current_user: models.User,
    ) -> None:
        db = db_session_factory()
        try:
            self._start_service.validate_start_preconditions(
                product_repo=ProductRepository(db),
                produto_id=produto_id,
                current_user=current_user,
            )
        finally:
            db.close()

    def dispatch_start(
        self,
        *,
        background_tasks: BackgroundTasks,
        db_session_factory,
        command: WebEnrichmentStartCommand,
        oop_executor,
    ) -> None:
        self._start_service.dispatch_start(
            background_tasks=background_tasks,
            db_session_factory=db_session_factory,
            command=command,
            oop_executor=oop_executor,
        )


class _WebEnrichmentRouterWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'web_enrichment'."""

    def __init__(self, runtime: Optional[_WebEnrichmentRouterRuntime] = None) -> None:
        self._runtime = runtime or _WebEnrichmentRouterRuntime()

    @property
    def mapping(self) -> _WebEnrichmentMappingRuntime:
        return self._runtime.mapping

    async def tarefa_enriquecer_produto_web(
        self,
        db_session_factory,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ):
        await self._runtime.execute_task(
            db_session_factory=db_session_factory,
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )

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
            oop_executor=self.tarefa_enriquecer_produto_web,
        )

        return {
            "msg": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."
        }


WebEnrichmentRouterWorkflow = _WebEnrichmentRouterWorkflow


class _EndpointHandlers:

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
        workflow = WebEnrichmentRouterWorkflow(runtime=_WebEnrichmentRouterRuntime())
        return workflow.iniciar_enriquecimento_produto_web(
            produto_id=produto_id,
            background_tasks=background_tasks,
            current_user=current_user,
            termos_busca_override=termos_busca_override,
        )

iniciar_enriquecimento_produto_web_endpoint = _EndpointHandlers.iniciar_enriquecimento_produto_web_endpoint


router.add_api_route(
    "/produto/{produto_id}/",
    iniciar_enriquecimento_produto_web_endpoint,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.Msg,
    include_in_schema=False,
)
