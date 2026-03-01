from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
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
        command = CatalogImportFinalizeCommand(
            file_id=task_kwargs.get("file_id"),
            user_id=task_kwargs.get("user_id"),
            product_type_id=task_kwargs.get("product_type_id"),
            fornecedor_id=task_kwargs.get("fornecedor_id"),
            mapping=task_kwargs.get("mapping"),
            pages=task_kwargs.get("pages"),
            region=task_kwargs.get("region"),
        )
        return await self._use_case.execute_command(
            command=command,
        )


class CatalogImportTaskBuilder:
    def __init__(self, executor: OOPCatalogImportExecutor):
        self._executor = executor

    def build_finalize_plan(
        self,
        *,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
    ) -> TaskExecutionPlan:
        task_kwargs = {
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
