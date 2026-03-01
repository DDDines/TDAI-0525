from __future__ import annotations

from typing import List

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorSearchService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    def busca_publica_disponivel(self) -> bool:
        return self._port.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        return await self._port.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        return await self._port.buscar_urls_google(
            query=query,
            num_results=num_results,
        )
