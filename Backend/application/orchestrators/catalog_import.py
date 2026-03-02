"""Module catalog import.

Contains backend logic related to catalog import and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.pipeline_selector import PipelineSelector, TaskExecutionPlan
from Backend.application.pipelines.catalog_import import (
    CatalogImportTaskBuilder,
    OOPCatalogImportExecutor,
)
from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)

TaskExecutor = Callable[..., Awaitable[Any]]


class CatalogImportPipelineOrchestrator:
    """Resolve o plano de execução da importação de catálogo por modo de app."""

    def __init__(
        self,
        *,
        oop_executor: TaskExecutor,
        context: str = "catalog_import.finalize",
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
        oop_use_case = CatalogImportProcessingUseCase(processor=oop_executor)
        self._oop_builder = CatalogImportTaskBuilder(
            executor=OOPCatalogImportExecutor(oop_use_case)
        )
        self._selector = PipelineSelector(context)

    def select_finalize_plan(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        """Select finalize plan for this workflow."""
        oop_plan = self._oop_builder.build_finalize_plan(
            file_id=command.file_id,
            user_id=command.user_id,
            product_type_id=command.product_type_id,
            fornecedor_id=command.fornecedor_id,
            mapping=command.mapping,
            pages=command.pages,
            region=command.region,
        )
        return self._selector.select(
            oop_plan=oop_plan,
        )
