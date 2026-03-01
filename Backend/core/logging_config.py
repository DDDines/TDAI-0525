import logging
from typing import Optional

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class _LoggingWorkflow:
    def __init__(self, runtime: Optional["_LoggingRuntime"] = None) -> None:
        self._runtime = runtime or _LoggingRuntime()

    def get_logger(self, name: str) -> logging.Logger:
        return self._runtime.get_logger(name=name)


class _LoggingRuntime:
    """Runtime OO para abstrair criaÃ§Ã£o de logger."""

    def get_logger(self, *, name: str) -> logging.Logger:
        return logging.getLogger(name)

LoggingWorkflow = _LoggingWorkflow


get_logging_workflow = lambda: LoggingWorkflow()
get_logger = lambda name: get_logging_workflow().get_logger(name=name)




