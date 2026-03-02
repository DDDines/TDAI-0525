"""Module search service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import List

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorSearchService:
    """Class WebDataExtractorSearchService.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    def busca_publica_disponivel(self) -> bool:
        """Execute busca_publica_disponivel.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar_urls_publicas.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar_urls_google.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.buscar_urls_google(
            query=query,
            num_results=num_results,
        )
