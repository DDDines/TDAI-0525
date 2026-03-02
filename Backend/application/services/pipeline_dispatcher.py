"""Module pipeline dispatcher.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import os

from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan


class PipelineDispatcher:
    """Responsavel por despachar planos em inline ou background tasks."""

    @staticmethod
    def should_run_inline_for_tests(sync_env_var: str) -> bool:
        """Execute should_run_inline_for_tests.

        This callable is documented to make behavior explicit for readers.
        """
        return bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv(sync_env_var) == "1"

    @staticmethod
    async def run_inline(plan: TaskExecutionPlan) -> None:
        """Execute run_inline.

        This callable is documented to make behavior explicit for readers.
        """
        await plan.executor(**plan.task_kwargs)

    @staticmethod
    def dispatch_background(background_tasks: BackgroundTasks, plan: TaskExecutionPlan) -> None:
        """Execute dispatch_background.

        This callable is documented to make behavior explicit for readers.
        """
        background_tasks.add_task(plan.executor, **plan.task_kwargs)
