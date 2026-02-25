from __future__ import annotations

import asyncio
import os
import threading
from typing import Optional

from fastapi import BackgroundTasks

from Backend.application.pipeline_selector import TaskExecutionPlan
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


class PipelineDispatcher:
    """Responsável por despachar planos em inline, thread ou background tasks."""

    @staticmethod
    def should_run_inline_for_tests(sync_env_var: str) -> bool:
        return bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv(sync_env_var) == "1"

    @staticmethod
    async def run_inline(plan: TaskExecutionPlan) -> None:
        await plan.executor(**plan.task_kwargs)

    @staticmethod
    def dispatch_background(background_tasks: BackgroundTasks, plan: TaskExecutionPlan) -> None:
        background_tasks.add_task(plan.executor, **plan.task_kwargs)

    @staticmethod
    def dispatch_threaded(
        plan: TaskExecutionPlan,
        *,
        thread_name_prefix: str,
    ) -> None:
        file_id = plan.task_kwargs.get("file_id", "unknown")

        def _run_in_thread() -> None:
            try:
                asyncio.run(plan.executor(**plan.task_kwargs))
            except Exception as exc:  # pragma: no cover - erro inesperado de thread
                logger.exception(
                    "falha ao executar thread da pipeline '%s' (file_id=%s): %s",
                    plan.name,
                    file_id,
                    exc,
                )

        thread = threading.Thread(
            target=_run_in_thread,
            name=f"{thread_name_prefix}-{file_id}",
            daemon=True,
        )
        thread.start()
