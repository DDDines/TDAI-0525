"""Module content service.

Contains backend logic related to content service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    """Represent web data extractor content service and centralize responsibilities for this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Run coletar conteudo pagina playwright in this workflow."""
        return await self._port.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Run extrair texto principal com trafilatura in this workflow."""
        return self._port.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )
