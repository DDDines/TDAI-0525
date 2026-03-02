"""Document content service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    """Represent Web Data Extractor Content Service and centralize its responsibilities inside this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize injected dependencies and runtime configuration for Web Data Extractor Content Service."""
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        return await self._port.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        return self._port.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )
