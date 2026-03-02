"""Catalog import finalization dispatcher.

Encapsulates plan selection and execution strategy (inline in tests or
background in runtime) for catalog import finalization commands.
"""

from __future__ import annotations

from typing import Any

from fastapi import BackgroundTasks

from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.orchestrators.catalog_import import (
    CatalogImportPipelineOrchestrator,
)
from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.pipeline_dispatcher import PipelineDispatcher


class CatalogImportFinalizeService:
    """Seleciona e executa o plano de finalizacao da importacao de catalogo."""

    def __init__(
        self,
        *,
        oop_executor: Any,
        dispatcher_cls: Any = PipelineDispatcher,
        orchestrator: Any = None,
        sync_env_var: str = "CATALOG_IMPORT_TEST_SYNC",
        thread_name_prefix: str = "catalog-import",
    ) -> None:
        """Build dispatcher/orchestrator collaborators for finalize execution."""
        self._orchestrator = orchestrator or CatalogImportPipelineOrchestrator(
            oop_executor=oop_executor,
        )
        self._dispatcher = dispatcher_cls
        self._sync_env_var = sync_env_var
        self._thread_name_prefix = thread_name_prefix

    def select_plan(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        """Create the task execution plan for a finalize command."""
        return self._orchestrator.select_finalize_plan(
            command=command,
        )

    async def dispatch_or_run(
        self,
        *,
        background_tasks: BackgroundTasks,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        """Execute inline in test mode or dispatch to FastAPI background tasks."""
        plan = self.select_plan(
            command=command,
        )
        if self._dispatcher.should_run_inline_for_tests(self._sync_env_var):
            await self._dispatcher.run_inline(plan)
        else:
            _ = self._thread_name_prefix  # compatibilidade explicita de configuracao
            self._dispatcher.dispatch_background(background_tasks, plan)
        return plan

    async def run_direct(
        self,
        *,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        """Run the selected finalize plan synchronously in the current request."""
        plan = self.select_plan(
            command=command,
        )
        await plan.executor(**plan.task_kwargs)
        return plan
