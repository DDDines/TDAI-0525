from __future__ import annotations
from enum import Enum
from typing import Optional

class AppMode(str, Enum):
    OOP = 'oop'

class AppModeWorkflow:

    def __init__(self, runtime: Optional['AppModeRuntime']=None) -> None:
        self._runtime = runtime or AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        return self._runtime.get_app_mode()

class AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        return AppMode.OOP
