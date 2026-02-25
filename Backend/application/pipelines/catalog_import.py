from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)


class OOPCatalogImportExecutor:
    """OOP adapter for catalog import processing.

    Current behavior delegates to the injected OOP use case.
    """

    def __init__(self, use_case: CatalogImportProcessingUseCase):
        self._use_case = use_case

    async def __call__(self, **task_kwargs: Any) -> Any:
        return await self._use_case.execute(**task_kwargs)


class CatalogImportTaskBuilder:
    def __init__(self, executor: OOPCatalogImportExecutor):
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
            executor_name="oop_catalog_import_task",
            executor=self._executor,
            task_kwargs=task_kwargs,
        )
