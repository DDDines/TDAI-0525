from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from Backend.application.orchestrators.web_enrichment import (
    WebEnrichmentPipelineOrchestrator,
)
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher
from Backend.application.services.repository_runtime_support import call_repository_method


class WebEnrichmentStartService:
    """Encapsula validacao de pre-condicoes e despacho do enriquecimento web."""

    def __init__(
        self,
        *,
        models: Any,
        dispatcher_cls: Any = PipelineDispatcher,
        orchestrator_cls: Any = WebEnrichmentPipelineOrchestrator,
        product_repository: Any | None = None,
    ) -> None:
        self._product_repository = product_repository
        self._models = models
        self._dispatcher = dispatcher_cls
        self._orchestrator_cls = orchestrator_cls

    def validate_start_preconditions(
        self,
        *,
        product_repo: Any | None = None,
        produto_id: int,
        current_user: Any,
    ) -> None:
        repo = product_repo or self._product_repository
        db_produto_check = call_repository_method(
            repo,
            "get_produto",
            session=getattr(repo, "_db", None),
            produto_id=produto_id,
        )
        if not db_produto_check:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado",
            )
        if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a enriquecer este produto",
            )
        if (
            db_produto_check.status_enriquecimento_web
            == self._models.StatusEnriquecimentoEnum.EM_PROGRESSO
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Processo de enriquecimento ja esta em andamento para este produto.",
            )

    def dispatch_start(
        self,
        *,
        background_tasks: Any,
        db_session_factory: Any,
        command: Any,
        oop_executor: Any,
    ) -> Any:
        orchestrator = self._orchestrator_cls(
            oop_executor=oop_executor,
        )
        selected_plan = orchestrator.select_start_plan(
            db_session_factory=db_session_factory,
            command=command,
        )
        self._dispatcher.dispatch_background(background_tasks, selected_plan)
        return selected_plan
