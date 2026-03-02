"""Module search service.

Contains backend logic related to search service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import List

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorSearchService:
    """Represent web data extractor search service and centralize responsibilities for this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    def busca_publica_disponivel(self) -> bool:
        """Run busca publica disponivel in this workflow."""
        return self._port.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Run buscar urls publicas in this workflow."""
        return await self._port.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Run buscar urls google in this workflow."""
        return await self._port.buscar_urls_google(
            query=query,
            num_results=num_results,
        )
