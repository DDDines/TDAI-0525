from __future__ import annotations

from dataclasses import dataclass, field

from Backend.application.services.file_processing_facade import FileProcessingFacade
from Backend.application.services.ia_generation_facade import IAGenerationFacade
from Backend.application.services.limit_service_facade import LimitServiceFacade
from Backend.application.services.web_data_extractor_facade import (
    WebDataExtractorFacade,
)


@dataclass
class ServiceContainer:
    """Registry simples de serviços OO compartilhados pela aplicação."""

    file_processing: FileProcessingFacade = field(default_factory=FileProcessingFacade)
    web_data_extractor: WebDataExtractorFacade = field(
        default_factory=WebDataExtractorFacade
    )
    ia_generation: IAGenerationFacade = field(default_factory=IAGenerationFacade)
    limit: LimitServiceFacade = field(default_factory=LimitServiceFacade)


service_container = ServiceContainer()

