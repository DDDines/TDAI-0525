from __future__ import annotations

from typing import Any, Optional

from Backend.application.pipeline_selector import TaskExecutionPlan, TaskExecutor


class LegacyWebEnrichmentTaskBuilder:
    def __init__(self, executor: TaskExecutor):
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
            executor_name="legacy_web_enrichment_task",
            executor=self._executor,
            task_kwargs=task_kwargs,
        )
