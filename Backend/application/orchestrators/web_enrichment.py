from __future__ import annotations

from typing import Any, Awaitable, Callable

from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.pipeline_selector import PipelineSelector, TaskExecutionPlan
from Backend.application.pipelines.web_enrichment import (
    OOPWebEnrichmentExecutor,
    WebEnrichmentTaskBuilder,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)
from Backend.legacy.pipelines.web_enrichment import LegacyWebEnrichmentTaskBuilder

TaskExecutor = Callable[..., Awaitable[Any]]


class WebEnrichmentPipelineOrchestrator:
    """Resolve o plano de execução do enriquecimento web por modo de app."""

    def __init__(
        self,
        *,
        legacy_executor: TaskExecutor,
        oop_executor: TaskExecutor | None = None,
        context: str = "web_enrichment.start",
    ) -> None:
        effective_oop_executor = oop_executor or legacy_executor
        self._legacy_builder = LegacyWebEnrichmentTaskBuilder(executor=legacy_executor)
        oop_use_case = WebEnrichmentProcessingUseCase(processor=effective_oop_executor)
        self._oop_builder = WebEnrichmentTaskBuilder(
            executor=OOPWebEnrichmentExecutor(oop_use_case)
        )
        self._selector = PipelineSelector(context)

    def select_start_plan(
        self,
        *,
        db_session_factory: Any,
        command: WebEnrichmentStartCommand,
    ) -> TaskExecutionPlan:
        legacy_plan = self._legacy_builder.build_start_plan(
            db_session_factory=db_session_factory,
            produto_id=command.produto_id,
            user_id=command.user_id,
            termos_busca_override=command.termos_busca_override,
        )
        oop_plan = self._oop_builder.build_start_plan(
            db_session_factory=db_session_factory,
            produto_id=command.produto_id,
            user_id=command.user_id,
            termos_busca_override=command.termos_busca_override,
        )
        return self._selector.select(
            legacy_plan=legacy_plan,
            oop_plan=oop_plan,
        )
