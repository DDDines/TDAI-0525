"""Camada de transporte HTTP para o dominio 'web_enrichment'."""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.application.services.web_data_extractor import WebDataExtractorOrchestratorService
from Backend.application.services.web_enrichment_content_quality_service import (
    WebEnrichmentContentQualityService,
)
from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_payload_service import WebEnrichmentPayloadService
from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)
from Backend.application.services.web_enrichment_start_service import WebEnrichmentStartService
from Backend.application.services.web_enrichment_task_runner import WebEnrichmentTaskRunner
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.infrastructure.adapters.limit_adapter import LimitServiceAdapter
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository

from . import auth_utils


router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
    redirect_slashes=False,
)
logger = get_logger(__name__)


class WebEnrichmentRequestService:
    """Servico request-scoped para iniciar tarefas de enriquecimento web."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Request Service."""
        self._session = session
        if hasattr(session, "get_bind"):
            session_provider = (
                ServiceContainerDependencySupport.build_background_session_provider_from_session(
                    session
                )
            )
        else:
            session_provider = ServiceContainerDependencySupport.get_background_session_provider()
        normalization_service = WebEnrichmentNormalizationService()
        relevance_service = WebEnrichmentRelevanceService()
        content_quality_service = WebEnrichmentContentQualityService(
            normalization_service=normalization_service
        )
        payload_service = WebEnrichmentPayloadService(
            normalization_service=normalization_service
        )

        extractor_service = WebDataExtractorOrchestratorService(WebDataExtractorServiceAdapter())
        self._task_runner = WebEnrichmentTaskRunner(
            session_provider=session_provider,
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            user_repository_factory=UserRepository,
            product_repository_factory=ProductRepository,
            usage_repository_factory=RegistroUsoIARepository,
            models=models,
            schemas=schemas,
            web_extractor=extractor_service,
            settings=settings,
            json_module=json,
            re_module=re,
            normalize_human_text=normalization_service.normalize_human_text,
            build_payload_enriquecimento_visivel=payload_service.build_payload_enriquecimento_visivel,
            extrair_dominio_fornecedor=relevance_service.extract_supplier_domain,
            priorizar_urls_para_enriquecimento=relevance_service.prioritize_urls_for_enrichment,
            is_meaningful_extracted_text=content_quality_service.is_meaningful_extracted_text,
            metadata_has_minimum_signal=content_quality_service.metadata_has_minimum_signal,
            is_source_relevant_for_product=relevance_service.is_source_relevant_for_product,
        )
        self._start_service = WebEnrichmentStartService(
            product_repository=ProductRepository(self._session),
            enrichment_counter=RegistroUsoIARepository(self._session),
            models=models,
        )

    async def tarefa_enriquecer_produto_web(
        self,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
        usar_ia: Optional[bool] = None,
    ):
        """Execute tarefa enriquecer produto web as part of this module workflow."""
        execute_kwargs = {
            "produto_id": produto_id,
            "user_id": user_id,
            "termos_busca_override": termos_busca_override,
        }
        if usar_ia is not None:
            execute_kwargs["usar_ia"] = usar_ia
        await self._task_runner.execute(**execute_kwargs)

    def iniciar_enriquecimento_produto_web(
        self,
        *,
        produto_id: int,
        background_tasks: BackgroundTasks,
        current_user: models.User,
        termos_busca_override: Optional[str] = None,
        usar_ia: Optional[bool] = None,
    ) -> Dict[str, str]:
        """Execute iniciar enriquecimento produto web as part of this module workflow."""
        LimitServiceAdapter().verificar_limite_enriquecimento(session=self._session, user=current_user)
        self._start_service.validate_start_preconditions(
            produto_id=produto_id,
            current_user=current_user,
            usar_ia=usar_ia,
        )

        command = WebEnrichmentStartCommand(
            produto_id=produto_id,
            user_id=current_user.id,
            termos_busca_override=termos_busca_override,
            usar_ia=usar_ia,
        )
        self._start_service.dispatch_start(
            background_tasks=background_tasks,
            command=command,
            oop_executor=self.tarefa_enriquecer_produto_web,
        )
        modo_label = "com IA" if usar_ia else "basico"
        return {
            "msg": (
                f"Processo de enriquecimento web para o produto ID {produto_id} "
                f"iniciado em segundo plano ({modo_label})."
            )
        }


@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    termos_busca_override: Optional[str] = Query(
        None,
        description="Opcional: termos de busca especificos para o Google Search.",
    ),
    usar_ia: bool = Query(
        False,
        description="Quando verdadeiro, habilita a etapa de IA apos a busca/enriquecimento basico.",
    ),
    request_service: WebEnrichmentRequestService = Depends(),
):
    """Iniciar enriquecimento produto web endpoint."""
    return request_service.iniciar_enriquecimento_produto_web(
        produto_id=produto_id,
        background_tasks=background_tasks,
        current_user=current_user,
        termos_busca_override=termos_busca_override,
        usar_ia=usar_ia,
    )


router.add_api_route(
    "/produto/{produto_id}/",
    iniciar_enriquecimento_produto_web_endpoint,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.Msg,
    include_in_schema=False,
)
