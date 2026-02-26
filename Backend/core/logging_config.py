import logging

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


def _get_logger_impl(name: str) -> logging.Logger:
    return logging.getLogger(name)


class _LoggingWorkflow:
    def get_logger(self, name: str) -> logging.Logger:
        return _get_logger_impl(name=name)


_logging_workflow = _LoggingWorkflow()


def get_logger(name: str) -> logging.Logger:
    return _logging_workflow.get_logger(name=name)


class LoggingLegacyService:
    def get_logger(self, *args, **kwargs):
        return get_logger(*args, **kwargs)


logging_legacy_service = LoggingLegacyService()
