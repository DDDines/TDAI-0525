"""Async job dispatcher that can route work to FastAPI or Celery."""

from __future__ import annotations

import importlib
from typing import Any, Callable, Optional

from Backend.core.config import settings
from Backend.core.logging_config import get_logger


logger = get_logger(__name__)


class AsyncJobDispatcher:
    """Route background work to the configured async backend."""

    def __init__(
        self,
        *,
        settings_obj: Any = settings,
        task_resolver: Optional[Callable[[str], Any]] = None,
    ) -> None:
        """Store runtime dependencies used for dispatch decisions."""
        self._settings = settings_obj
        self._task_resolver = task_resolver or self._default_task_resolver

    def uses_celery(self) -> bool:
        """Return whether Celery is the configured async backend."""
        return str(getattr(self._settings, "ASYNC_DISPATCH_PROVIDER", "background_tasks")).lower() == "celery"

    @staticmethod
    def _default_task_resolver(task_name: str) -> Any:
        """Resolve a Celery task lazily to avoid hard startup coupling."""
        module = importlib.import_module("Backend.celery_tasks")
        resolver = getattr(module, "resolve_task")
        return resolver(task_name)

    def dispatch_named_task(self, *, task_name: str, task_kwargs: dict[str, Any]) -> Any:
        """Dispatch a named Celery task and return the async result handle."""
        task = self._task_resolver(task_name)
        logger.info("Despachando task Celery '%s' com payload serializavel.", task_name)
        return task.delay(**task_kwargs)

    def dispatch_named_or_background(
        self,
        *,
        background_tasks: Any,
        task_name: str,
        task_kwargs: dict[str, Any],
        fallback_callable: Callable[..., Any],
    ) -> Any:
        """Dispatch through Celery when enabled, otherwise use BackgroundTasks."""
        if self.uses_celery():
            return self.dispatch_named_task(
                task_name=task_name,
                task_kwargs=task_kwargs,
            )
        background_tasks.add_task(
            fallback_callable,
            **task_kwargs,
        )
        return None
