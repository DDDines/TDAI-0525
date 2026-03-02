"""Document app mode module responsibilities and runtime integration points."""

from __future__ import annotations
from enum import Enum
from typing import Optional

class AppMode(str, Enum):
    """Represent App Mode and centralize its responsibilities inside this module."""
    OOP = 'oop'

class AppModeWorkflow:

    """Represent App Mode Workflow and centralize its responsibilities inside this module."""
    def __init__(self, runtime: Optional['AppModeRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for App Mode Workflow."""
        self._runtime = runtime or AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        """Retrieve app mode using the current service dependencies."""
        return self._runtime.get_app_mode()

class AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        """Retrieve app mode using the current service dependencies."""
        return AppMode.OOP
