"""Document logging config module responsibilities and runtime integration points."""

import logging
from typing import Optional

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class LoggingWorkflow:

    """Represent Logging Workflow and centralize its responsibilities inside this module."""
    def __init__(self, runtime: Optional['LoggingRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Logging Workflow."""
        self._runtime = runtime or LoggingRuntime()

    def get_logger(self, name: str) -> logging.Logger:
        """Retrieve logger using the current service dependencies."""
        return self._runtime.get_logger(name=name)

class LoggingRuntime:
    """Runtime OO para abstrair criacao de logger."""

    def get_logger(self, *, name: str) -> logging.Logger:
        """Retrieve logger using the current service dependencies."""
        return logging.getLogger(name)

class LoggingEntryPoints:

    """Represent Logging Entry Points and centralize its responsibilities inside this module."""
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Retrieve logger using the current service dependencies."""
        return LoggingWorkflow().get_logger(name=name)

get_logger = LoggingEntryPoints.get_logger
