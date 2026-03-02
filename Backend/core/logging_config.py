"""Module logging config.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

import logging
from typing import Optional

LOG_FORMAT = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class LoggingWorkflow:

    """Class LoggingWorkflow.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, runtime: Optional['LoggingRuntime']=None) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime = runtime or LoggingRuntime()

    def get_logger(self, name: str) -> logging.Logger:
        """Execute get_logger.

        This callable is documented to make behavior explicit for readers.
        """
        return self._runtime.get_logger(name=name)

class LoggingRuntime:
    """Runtime OO para abstrair criacao de logger."""

    def get_logger(self, *, name: str) -> logging.Logger:
        """Execute get_logger.

        This callable is documented to make behavior explicit for readers.
        """
        return logging.getLogger(name)

class LoggingEntryPoints:

    """Class LoggingEntryPoints.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Execute get_logger.

        This callable is documented to make behavior explicit for readers.
        """
        return LoggingWorkflow().get_logger(name=name)

get_logger = LoggingEntryPoints.get_logger
