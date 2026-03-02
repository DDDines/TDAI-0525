"""Module catalog import finalize service.

Contains backend logic related to catalog import finalize service and documents its role in the OOP architecture.
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
        db_session_factory: Any,
        dispatcher_cls: Any = PipelineDispatcher,
        orchestrator: Any = None,
        sync_env_var: str = "CATALOG_IMPORT_TEST_SYNC",
        thread_name_prefix: str = "catalog-import",
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._db_session_factory = db_session_factory
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
        """Select plan for this workflow."""
        if self._db_session_factory is None:
            raise ValueError("db_session_factory is required for CatalogImportFinalizeService")
        return self._orchestrator.select_finalize_plan(
            command=command,
        )

    async def dispatch_or_run(
        self,
        *,
        background_tasks: BackgroundTasks,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        """Dispatch or run for this workflow."""
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
        """Run direct for this workflow."""
        plan = self.select_plan(
            command=command,
        )
        await plan.executor(**plan.task_kwargs)
        return plan
