"""Web enrichment.

Defines the module responsibilities and how it fits in the backend architecture.
"""

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
        """Initialize required dependencies and runtime configuration."""
        self._use_case = use_case

    async def __call__(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str] = None,
    ) -> Any:
        """Process Call."""
        command = WebEnrichmentStartCommand(
            produto_id=produto_id,
            user_id=user_id,
            termos_busca_override=termos_busca_override,
        )
        return await self._use_case.execute_command(
            command=command,
        )


class WebEnrichmentTaskBuilder:
    """Encapsulates Web enrichment task builder."""
    def __init__(self, executor: OOPWebEnrichmentExecutor):
        """Initialize required dependencies and runtime configuration."""
        self._executor = executor

    def build_start_plan(
        self,
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str],
    ) -> TaskExecutionPlan:
        """Build start plan."""
        task_kwargs = {
            "produto_id": produto_id,
            "user_id": user_id,
            "termos_busca_override": termos_busca_override,
        }
        return TaskExecutionPlan(
            name="web_enrichment.start",
            executor_name="oop_web_enrichment_task",
            executor=self._executor,
            task_kwargs=task_kwargs,
        )
