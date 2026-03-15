"""Document search service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import List, Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorSearchService:
    """Represent Web Data Extractor Search Service and centralize its responsibilities inside this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize injected dependencies and runtime configuration for Web Data Extractor Search Service."""
        self._port = port

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return self._port.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls publicas as part of this module workflow."""
        return await self._port.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
        api_key: Optional[str] = None,
        search_engine_id: Optional[str] = None,
    ) -> List[str]:
        """Execute buscar urls google as part of this module workflow."""
        return await self._port.buscar_urls_google(
            query=query,
            num_results=num_results,
            api_key=api_key,
            search_engine_id=search_engine_id,
        )
