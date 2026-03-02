"""Module catalog import finalize service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
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
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute select_plan.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute dispatch_or_run.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute run_direct.

        This callable is documented to make behavior explicit for readers.
        """
        plan = self.select_plan(
            command=command,
        )
        await plan.executor(**plan.task_kwargs)
        return plan
