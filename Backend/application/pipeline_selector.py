from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Optional

from Backend.core.app_mode import AppMode, get_app_mode
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)

TaskExecutor = Callable[..., Awaitable[Any]]


@dataclass(frozen=True)
class TaskExecutionPlan:
    name: str
    executor_name: str
    executor: TaskExecutor
    task_kwargs: Dict[str, Any]

    def to_compare_payload(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "executor_name": self.executor_name,
            "task_kwargs": self.task_kwargs,
        }


class PipelineSelector:
    """Selects OOP execution plan.

    APP_MODE values different from "oop" are tolerated only for transition
    compatibility, but selection remains OOP-only.
    """

    def __init__(self, context: str):
        self.context = context

    def select(
        self,
        *,
        oop_plan: TaskExecutionPlan,
        legacy_plan: Optional[TaskExecutionPlan] = None,
    ) -> TaskExecutionPlan:
        _ = legacy_plan
        mode = get_app_mode()
        if mode != AppMode.OOP:
            logger.warning(
                "APP_MODE=%s (%s) detectado; forcando plano OOP.",
                mode.value,
                self.context,
            )
        else:
            logger.info("APP_MODE=oop (%s): selecionado plano OOP", self.context)
        return oop_plan
