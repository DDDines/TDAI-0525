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
from Backend.legacy.pipelines.catalog_import import LegacyCatalogImportTaskBuilder

TaskExecutor = Callable[..., Awaitable[Any]]


class CatalogImportPipelineOrchestrator:
    """Resolve o plano de execução da importação de catálogo por modo de app."""

    def __init__(
        self,
        *,
        legacy_executor: TaskExecutor,
        oop_executor: TaskExecutor | None = None,
        context: str = "catalog_import.finalize",
    ) -> None:
        effective_oop_executor = oop_executor or legacy_executor
        self._legacy_builder = LegacyCatalogImportTaskBuilder(executor=legacy_executor)
        oop_use_case = CatalogImportProcessingUseCase(processor=effective_oop_executor)
        self._oop_builder = CatalogImportTaskBuilder(
            executor=OOPCatalogImportExecutor(oop_use_case)
        )
        self._selector = PipelineSelector(context)

    def select_finalize_plan(
        self,
        *,
        db_session_factory: Any,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        legacy_plan = self._legacy_builder.build_finalize_plan(
            db_session_factory=db_session_factory,
            file_id=command.file_id,
            user_id=command.user_id,
            product_type_id=command.product_type_id,
            fornecedor_id=command.fornecedor_id,
            mapping=command.mapping,
            pages=command.pages,
            region=command.region,
        )
        oop_plan = self._oop_builder.build_finalize_plan(
            db_session_factory=db_session_factory,
            file_id=command.file_id,
            user_id=command.user_id,
            product_type_id=command.product_type_id,
            fornecedor_id=command.fornecedor_id,
            mapping=command.mapping,
            pages=command.pages,
            region=command.region,
        )
        return self._selector.select(
            legacy_plan=legacy_plan,
            oop_plan=oop_plan,
        )
