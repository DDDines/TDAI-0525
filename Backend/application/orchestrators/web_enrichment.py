"""Module web enrichment.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

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

TaskExecutor = Callable[..., Awaitable[Any]]


class WebEnrichmentPipelineOrchestrator:
    """Resolve o plano de execução do enriquecimento web por modo de app."""

    def __init__(
        self,
        *,
        oop_executor: TaskExecutor,
        context: str = "web_enrichment.start",
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        oop_use_case = WebEnrichmentProcessingUseCase(processor=oop_executor)
        self._oop_builder = WebEnrichmentTaskBuilder(
            executor=OOPWebEnrichmentExecutor(oop_use_case)
        )
        self._selector = PipelineSelector(context)

    def select_start_plan(
        self,
        *,
        command: WebEnrichmentStartCommand,
    ) -> TaskExecutionPlan:
        """Execute select_start_plan.

        This callable is documented to make behavior explicit for readers.
        """
        oop_plan = self._oop_builder.build_start_plan(
            produto_id=command.produto_id,
            user_id=command.user_id,
            termos_busca_override=command.termos_busca_override,
        )
        return self._selector.select(
            oop_plan=oop_plan,
        )
