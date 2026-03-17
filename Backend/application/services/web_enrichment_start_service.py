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
        enrichment_counter: Any = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Start Service."""
        self._product_repository = product_repository
        self._enrichment_counter = enrichment_counter
        self._models = models
        self._dispatcher = dispatcher_cls
        self._orchestrator_cls = orchestrator_cls

    def _check_enrichment_limit(self, *, current_user: Any) -> None:
        """Bloqueia inicio de enriquecimento quando o limite mensal do plano e atingido."""
        if getattr(current_user, "is_superuser", False):
            return
        if self._enrichment_counter is None:
            return
        limite = getattr(current_user, "limite_enriquecimento_web", None)
        if (limite is None or limite <= 0) and getattr(current_user, "plano", None):
            limite = getattr(current_user.plano, "limite_enriquecimento_web", None)
        if limite is None or limite <= 0:
            return
        usos_no_mes = self._enrichment_counter.count_usos_ia_by_user_and_type_no_mes_corrente(
            user_id=current_user.id,
            tipo_geracao_prefix="enriquecimento",
        )
        if usos_no_mes >= limite:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Limite mensal de {limite} enriquecimentos web atingido. "
                    f"Voce utilizou {usos_no_mes} neste ciclo. "
                    "Aguarde o proximo ciclo ou faca upgrade do plano."
                ),
            )

    def validate_start_preconditions(
        self,
        *,
        produto_id: int,
        current_user: Any,
        usar_ia: bool | None = None,
    ) -> None:
        """Execute validate start preconditions as part of this module workflow."""
        self._check_enrichment_limit(current_user=current_user)
        scoped_user_id = None if current_user.is_superuser else current_user.id
        db_produto_check = self._product_repository.get_produto(
            produto_id=produto_id, user_id=scoped_user_id
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
        if usar_ia is True and not getattr(db_produto_check, "product_type_id", None):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Defina um tipo de produto antes de usar IA no enriquecimento web. "
                    "O tipo orienta quais atributos relevantes devem ser coletados."
                ),
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
