from __future__ import annotations

from enum import Enum
from typing import Optional

from Backend.core.config import settings
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


class AppMode(str, Enum):
    OOP = "oop"


class _AppModeWorkflow:
    def __init__(self, runtime: Optional["_AppModeRuntime"] = None) -> None:
        self._runtime = runtime or _AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        return self._runtime.get_app_mode()


class _AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        raw_mode = str(getattr(settings, "APP_MODE", AppMode.OOP.value) or "").strip().lower()
        if raw_mode != AppMode.OOP.value:
            logger.warning(
                "APP_MODE=%s nao e mais suportado. Forcando modo oop.",
                raw_mode or "<empty>",
            )
        return AppMode.OOP


app_mode_runtime = _AppModeRuntime()
_app_mode_workflow = _AppModeWorkflow(runtime=app_mode_runtime)


def get_app_mode() -> AppMode:
    return _app_mode_workflow.get_app_mode()
