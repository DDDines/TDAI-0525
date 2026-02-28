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
        self._orchestrator = orchestrator or CatalogImportPipelineOrchestrator(
            oop_executor=oop_executor,
        )
        self._dispatcher = dispatcher_cls
        self._sync_env_var = sync_env_var
        self._thread_name_prefix = thread_name_prefix

    def select_plan(
        self,
        *,
        db_session_factory: Any,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        return self._orchestrator.select_finalize_plan(
            db_session_factory=db_session_factory,
            command=command,
        )

    async def dispatch_or_run(
        self,
        *,
        background_tasks: BackgroundTasks,
        db_session_factory: Any,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        plan = self.select_plan(
            db_session_factory=db_session_factory,
            command=command,
        )
        if self._dispatcher.should_run_inline_for_tests(self._sync_env_var):
            await self._dispatcher.run_inline(plan)
        else:
            _ = background_tasks  # compatibilidade explicita de assinatura
            self._dispatcher.dispatch_threaded(
                plan,
                thread_name_prefix=self._thread_name_prefix,
            )
        return plan

    async def run_direct(
        self,
        *,
        db_session_factory: Any,
        command: CatalogImportFinalizeCommand,
    ) -> TaskExecutionPlan:
        plan = self.select_plan(
            db_session_factory=db_session_factory,
            command=command,
        )
        await plan.executor(**plan.task_kwargs)
        return plan
