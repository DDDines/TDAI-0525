"""Module test service container defaults.

Contains backend logic related to test service container defaults and documents its role in the OOP architecture.
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

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_service_container_uses_oop_adapters_by_default():
        """Run test service container uses oop adapters by default in this workflow."""
        container = ServiceContainer()
    
        assert isinstance(container.file_processing._port, FileProcessingServiceAdapter)
        assert isinstance(container.web_data_extractor.search._port, WebDataExtractorServiceAdapter)

test_service_container_uses_oop_adapters_by_default = _TopLevelFunctionSurface.test_service_container_uses_oop_adapters_by_default
