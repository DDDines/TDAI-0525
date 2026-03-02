"""Module logging config.

Contains backend logic related to logging config and documents its role in the OOP architecture.
"""

import logging
from typing import Optional

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class LoggingWorkflow:

    """Represent logging workflow and centralize responsibilities for this module."""
    def __init__(self, runtime: Optional['LoggingRuntime']=None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._runtime = runtime or LoggingRuntime()

    def get_logger(self, name: str) -> logging.Logger:
        """Return logger for this workflow."""
        return self._runtime.get_logger(name=name)

class LoggingRuntime:
    """Runtime OO para abstrair criacao de logger."""

    def get_logger(self, *, name: str) -> logging.Logger:
        """Return logger for this workflow."""
        return logging.getLogger(name)

class LoggingEntryPoints:

    """Represent logging entry points and centralize responsibilities for this module."""
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Return logger for this workflow."""
        return LoggingWorkflow().get_logger(name=name)

get_logger = LoggingEntryPoints.get_logger
