"""Document web enrichment start service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from Backend.application.orchestrators.web_enrichment import (
    WebEnrichmentPipelineOrchestrator,
)
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher


class WebEnrichmentStartService:
    """Encapsula validacao de pre-condicoes e despacho do enriquecimento web."""

    def __init__(
        self,
        *,
        models: Any,
        dispatcher_cls: Any = PipelineDispatcher,
        orchestrator_cls: Any = WebEnrichmentPipelineOrchestrator,
        product_repository: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Start Service."""
        self._product_repository = product_repository
        self._models = models
        self._dispatcher = dispatcher_cls
        self._orchestrator_cls = orchestrator_cls

    def validate_start_preconditions(
        self,
        *,
        produto_id: int,
        current_user: Any,
    ) -> None:
        """Execute validate start preconditions as part of this module workflow."""
        db_produto_check = self._product_repository.get_produto(produto_id=produto_id)
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

    def _mark_pending_status(self, *, produto_id: int) -> None:
        """Marca o status como pendente para refletir a fila imediatamente na UI."""
        status_pendente = getattr(self._models.StatusEnriquecimentoEnum, "PENDENTE", None)
        if status_pendente is None:
            return
        update_fn = getattr(self._product_repository, "set_web_enrichment_status", None)
        if callable(update_fn):
            update_fn(
                produto_id=produto_id,
                status=status_pendente,
                log_message="Enriquecimento web enfileirado para execucao.",
            )

    def dispatch_start(
        self,
        *,
        background_tasks: Any,
        command: Any,
        oop_executor: Any,
    ) -> Any:
        """Execute dispatch start as part of this module workflow."""
        self._mark_pending_status(produto_id=command.produto_id)
        orchestrator = self._orchestrator_cls(
            oop_executor=oop_executor,
        )
        selected_plan = orchestrator.select_start_plan(
            command=command,
        )
        self._dispatcher.dispatch_background(background_tasks, selected_plan)
        return selected_plan
