from __future__ import annotations

from dataclasses import dataclass, field

from Backend.application.services.file_processing import FileProcessingOrchestratorService
from Backend.application.services.ia_generation_facade import IAGenerationFacade
from Backend.application.services.limit_service_facade import LimitServiceFacade
from Backend.application.services.web_data_extractor import (
    WebDataExtractorOrchestratorService,
)
from Backend.infrastructure.adapters.file_processing_adapter import (
    FileProcessingServiceAdapter,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)


def _build_file_processing_service() -> FileProcessingOrchestratorService:
    return FileProcessingOrchestratorService(FileProcessingServiceAdapter())


def _build_web_data_extractor_service() -> WebDataExtractorOrchestratorService:
    return WebDataExtractorOrchestratorService(WebDataExtractorServiceAdapter())


@dataclass
class ServiceContainer:
    """Registry simples de servicos OO compartilhados pela aplicacao."""

    file_processing: FileProcessingOrchestratorService = field(
        default_factory=_build_file_processing_service
    )
    web_data_extractor: WebDataExtractorOrchestratorService = field(
        default_factory=_build_web_data_extractor_service
    )
    ia_generation: IAGenerationFacade = field(default_factory=IAGenerationFacade)
    limit: LimitServiceFacade = field(default_factory=LimitServiceFacade)


service_container = ServiceContainer()
