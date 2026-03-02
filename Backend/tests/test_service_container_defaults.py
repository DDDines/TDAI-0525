"""Module test service container defaults.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from Backend.application.services.service_container import ServiceContainer
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_service_container_uses_oop_adapters_by_default():
        """Execute test_service_container_uses_oop_adapters_by_default.

        This callable is documented to make behavior explicit for readers.
        """
        container = ServiceContainer()
    
        assert isinstance(container.file_processing._port, FileProcessingServiceAdapter)
        assert isinstance(container.web_data_extractor.search._port, WebDataExtractorServiceAdapter)

test_service_container_uses_oop_adapters_by_default = _TopLevelFunctionSurface.test_service_container_uses_oop_adapters_by_default
