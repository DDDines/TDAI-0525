"""Document pipeline dispatcher module responsibilities and runtime integration points."""

from __future__ import annotations

import asyncio
import inspect
import os

from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.application.services.async_job_dispatcher import AsyncJobDispatcher


class PipelineDispatcher:
    """Responsavel por despachar planos em inline ou background tasks."""

    @staticmethod
    def _run_plan_in_worker_thread(plan: TaskExecutionPlan) -> None:
        """Run task execution plan in a worker thread.

        BackgroundTasks executes sync callables in a threadpool. Wrapping async
        executors here avoids running long CPU-heavy coroutine bodies directly
        on the main event loop, which keeps status polling endpoints responsive.
        """
        execution_result = plan.executor(**plan.task_kwargs)
        if inspect.isawaitable(execution_result):
            asyncio.run(execution_result)

    @staticmethod
    def should_run_inline_for_tests(sync_env_var: str) -> bool:
        """Should run inline for tests."""
        return bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv(sync_env_var) == "1"

    @staticmethod
    async def run_inline(plan: TaskExecutionPlan) -> None:
        """Execute run inline as part of this module workflow."""
        await plan.executor(**plan.task_kwargs)

    @staticmethod
    def dispatch_background(background_tasks: BackgroundTasks, plan: TaskExecutionPlan) -> None:
        """Execute dispatch background as part of this module workflow."""
        dispatcher = AsyncJobDispatcher()
        if dispatcher.uses_celery():
            try:
                dispatcher.dispatch_named_task(
                    task_name=plan.name,
                    task_kwargs=plan.task_kwargs,
                )
                return
            except LookupError:
                pass
        background_tasks.add_task(
            PipelineDispatcher._run_plan_in_worker_thread,
            plan,
        )
