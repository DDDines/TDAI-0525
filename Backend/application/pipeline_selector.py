from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict

from Backend.core.app_mode import AppMode, compare_shadow_payloads, get_app_mode
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
    """Selects legacy/oop plan according to APP_MODE.

    - legacy: execute legacy plan
    - oop: execute oop plan
    - shadow: execute legacy plan and log diff between plans
    """

    def __init__(self, context: str):
        self.context = context

    def select(self, legacy_plan: TaskExecutionPlan, oop_plan: TaskExecutionPlan) -> TaskExecutionPlan:
        mode = get_app_mode()
        if mode == AppMode.OOP:
            logger.info("APP_MODE=oop (%s): selecionado plano OOP", self.context)
            return oop_plan

        if mode == AppMode.SHADOW:
            compare_shadow_payloads(
                self.context,
                legacy_plan.to_compare_payload(),
                oop_plan.to_compare_payload(),
            )
            logger.info("APP_MODE=shadow (%s): executando plano LEGACY", self.context)
            return legacy_plan

        logger.info("APP_MODE=legacy (%s): executando plano LEGACY", self.context)
        return legacy_plan
