"""Module app mode.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional

class AppMode(str, Enum):
    """Class AppMode.

    Encapsulates one responsibility in the backend architecture.
    """
    OOP = 'oop'

class AppModeWorkflow:

    """Class AppModeWorkflow.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, runtime: Optional['AppModeRuntime']=None) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime = runtime or AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        """Execute get_app_mode.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.get_app_mode()

class AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        """Execute get_app_mode.

        This callable is documented to make behavior explicit for readers.
        """
        return AppMode.OOP
