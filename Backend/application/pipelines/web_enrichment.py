from __future__ import annotations

from typing import Any, Optional

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)


class OOPWebEnrichmentExecutor:
    """OOP adapter for web enrichment processing.

    Current behavior delegates to the injected OOP use case.
    """

    def __init__(self, use_case: WebEnrichmentProcessingUseCase):
        self._use_case = use_case

    async def __call__(self, **task_kwargs: Any) -> Any:
        return await self._use_case.execute(**task_kwargs)


class WebEnrichmentTaskBuilder:
    def __init__(self, executor: OOPWebEnrichmentExecutor):
        self._executor = executor

    def build_start_plan(
        self,
        *,
        db_session_factory: Any,
        produto_id: int,
        user_id: int,
        termos_busca_override: Optional[str],
    ) -> TaskExecutionPlan:
        task_kwargs = {
            "db_session_factory": db_session_factory,
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
