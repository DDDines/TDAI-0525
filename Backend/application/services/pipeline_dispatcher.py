"""Pipeline dispatcher.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

import os

from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan


class PipelineDispatcher:
    """Responsavel por despachar planos em inline ou background tasks."""

    @staticmethod
    def should_run_inline_for_tests(sync_env_var: str) -> bool:
        """Process Should run inline for tests."""
        return bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv(sync_env_var) == "1"

    @staticmethod
    async def run_inline(plan: TaskExecutionPlan) -> None:
        """Run inline."""
        await plan.executor(**plan.task_kwargs)

    @staticmethod
    def dispatch_background(background_tasks: BackgroundTasks, plan: TaskExecutionPlan) -> None:
        """Dispatch background."""
        background_tasks.add_task(plan.executor, **plan.task_kwargs)
