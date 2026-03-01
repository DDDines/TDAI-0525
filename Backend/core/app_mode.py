from __future__ import annotations
from enum import Enum
from typing import Optional

class _ModuleAliasProviders:

    @staticmethod
    def get_app_mode_workflow():
        return AppModeWorkflow()

class AppMode(str, Enum):
    OOP = 'oop'

class _AppModeWorkflow:

    def __init__(self, runtime: Optional['_AppModeRuntime']=None) -> None:
        self._runtime = runtime or _AppModeRuntime()

    def get_app_mode(self) -> AppMode:
        return self._runtime.get_app_mode()

class _AppModeRuntime:
    """Runtime para resolucao de modo de execucao.

    A plataforma opera em OOP-only.
    """

    def get_app_mode(self) -> AppMode:
        return AppMode.OOP
AppModeWorkflow = _AppModeWorkflow
