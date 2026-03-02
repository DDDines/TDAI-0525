"""Module pipeline selector.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from Backend.core.app_mode import AppModeWorkflow
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)

TaskExecutor = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class TaskExecutionPlan:
    """Class TaskExecutionPlan.

    Encapsulates one responsibility in the backend architecture.
    """
    name: str
    executor_name: str
    executor: TaskExecutor
    task_kwargs: Dict[str, Any]

    def to_compare_payload(self) -> Dict[str, Any]:
        """Execute to_compare_payload.

        This callable is documented to make behavior explicit for readers.
        """
        return {
            "name": self.name,
            "executor_name": self.executor_name,
            "task_kwargs": self.task_kwargs,
        }


class PipelineSelector:
    """Selects OOP execution plan."""

    def __init__(self, context: str):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.context = context

    def select(
        self,
        *,
        oop_plan: TaskExecutionPlan,
    ) -> TaskExecutionPlan:
        """Execute select.

        This callable is documented to make behavior explicit for readers.
        """
        _ = AppModeWorkflow().get_app_mode()
        logger.info("APP_MODE=oop (%s): selecionado plano OOP", self.context)
        return oop_plan
