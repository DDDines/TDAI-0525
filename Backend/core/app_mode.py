"""App mode.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

class AppMode(str, Enum):
    """Encapsulates App mode."""
    OOP = 'oop'

class AppModeWorkflow:

    """Encapsulates App mode workflow."""
    def __init__(self, runtime: Optional['AppModeRuntime']=None) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._runtime = runtime or AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        """Return App mode."""
        return self._runtime.get_app_mode()

class AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        """Return App mode."""
        return AppMode.OOP
