"""Module app mode.

Contains backend logic related to app mode and documents its role in the OOP architecture.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

class AppMode(str, Enum):
    """Represent app mode and centralize responsibilities for this module."""
    OOP = 'oop'

class AppModeWorkflow:

    """Represent app mode workflow and centralize responsibilities for this module."""
    def __init__(self, runtime: Optional['AppModeRuntime']=None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._runtime = runtime or AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        """Return app mode for this workflow."""
        return self._runtime.get_app_mode()

class AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        """Return app mode for this workflow."""
        return AppMode.OOP
