"""Document web enrichment module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Optional

from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)


class OOPWebEnrichmentExecutor:
    """OOP adapter for web enrichment processing.

    Current behavior delegates to the injected OOP use case.
    """

    def __init__(self, use_case: WebEnrichmentProcessingUseCase):
        """Initialize injected dependencies and runtime configuration for OOPWeb Enrichment Executor."""
        self._use_case = use_case

    async def __call__(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
        usar_ia: Optional[bool] = None,
    ) -> Any:
        """Execute call as part of this module workflow."""
        command = WebEnrichmentStartCommand(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
            usar_ia=usar_ia,
        )
        return await self._use_case.execute_command(
            command=command,
        )


class WebEnrichmentTaskBuilder:
    """Represent Web Enrichment Task Builder and centralize its responsibilities inside this module."""
    def __init__(self, executor: OOPWebEnrichmentExecutor):
        """Initialize injected dependencies and runtime configuration for Web Enrichment Task Builder."""
        self._executor = executor

    def build_start_plan(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str],
        usar_ia: Optional[bool] = None,
    ) -> TaskExecutionPlan:
        """Build start plan from current inputs and configuration."""
        task_kwargs = {
            "produto_id": produto_id,
            "user_id": user_id,
            "termos_busca_override": termos_busca_override,
        }
        if usar_ia is not None:
            task_kwargs["usar_ia"] = usar_ia
        return TaskExecutionPlan(
            name="web_enrichment.start",
            executor_name="oop_web_enrichment_task",
            executor=self._executor,
            task_kwargs=task_kwargs,
        )
