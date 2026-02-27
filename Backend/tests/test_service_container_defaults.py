from __future__ import annotations

from Backend.application.services.service_container import ServiceContainer
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)


def test_service_container_uses_oop_adapters_by_default():
    container = ServiceContainer()

    assert isinstance(container.file_processing._port, FileProcessingServiceAdapter)
    assert isinstance(container.web_data_extractor.search._port, WebDataExtractorServiceAdapter)
