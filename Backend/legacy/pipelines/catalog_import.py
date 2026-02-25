from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.application.pipeline_selector import TaskExecutionPlan, TaskExecutor


class LegacyCatalogImportTaskBuilder:
    def __init__(self, executor: TaskExecutor):
        self._executor = executor

    def build_finalize_plan(
        self,
        *,
        db_session_factory: Any,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
    ) -> TaskExecutionPlan:
        task_kwargs = {
            "db_session_factory": db_session_factory,
            "file_id": file_id,
            "user_id": user_id,
            "product_type_id": product_type_id,
            "fornecedor_id": fornecedor_id,
            "mapping": dict(mapping) if isinstance(mapping, dict) else mapping,
            "pages": list(pages) if pages else pages,
            "region": list(region) if region else region,
        }
        return TaskExecutionPlan(
            name="catalog_import.finalize",
            executor_name="legacy_catalog_import_task",
            executor=self._executor,
            task_kwargs=task_kwargs,
        )
