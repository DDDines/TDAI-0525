import logging
from typing import Optional

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class LoggingWorkflow:

    def __init__(self, runtime: Optional['LoggingRuntime']=None) -> None:
        self._runtime = runtime or LoggingRuntime()

    def get_logger(self, name: str) -> logging.Logger:
        return self._runtime.get_logger(name=name)

class LoggingRuntime:
    """Runtime OO para abstrair criacao de logger."""

    def get_logger(self, *, name: str) -> logging.Logger:
        return logging.getLogger(name)

class LoggingEntryPoints:

    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        return LoggingWorkflow().get_logger(name=name)

get_logger = LoggingEntryPoints.get_logger
