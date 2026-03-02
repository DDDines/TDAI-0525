"""Pipeline selector.

Defines the module responsibilities and how it fits in the backend architecture.
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
    """Encapsulates Task execution plan."""
    name: str
    executor_name: str
    executor: TaskExecutor
    task_kwargs: Dict[str, Any]

    def to_compare_payload(self) -> Dict[str, Any]:
        """Process To compare payload."""
        return {
            "name": self.name,
            "executor_name": self.executor_name,
            "task_kwargs": self.task_kwargs,
        }


class PipelineSelector:
    """Selects OOP execution plan."""

    def __init__(self, context: str):
        """Initialize required dependencies and runtime configuration."""
        self.context = context

    def select(
        self,
        *,
        oop_plan: TaskExecutionPlan,
    ) -> TaskExecutionPlan:
        """Process Select."""
        _ = AppModeWorkflow().get_app_mode()
        logger.info("APP_MODE=oop (%s): selecionado plano OOP", self.context)
        return oop_plan
