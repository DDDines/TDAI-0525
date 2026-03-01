from __future__ import annotations

from Backend.infrastructure.runtime_services.web_data_extractor_runtime_service import (
    WebDataExtractorRuntimeService,
)


class _WebDataExtractorRuntimeProvider:
    @staticmethod
    def get_runtime_service() -> WebDataExtractorRuntimeService:
        return WebDataExtractorRuntimeService()


get_runtime_service = _WebDataExtractorRuntimeProvider.get_runtime_service
