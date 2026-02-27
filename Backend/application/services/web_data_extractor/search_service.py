from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorSearchService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    def busca_publica_disponivel(self) -> bool:
        return self._port.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._port.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._port.buscar_urls_google(*args, **kwargs)
