"""Content service.

"""

from __future__ import annotations

from typing import Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    """Encapsulates Web data extractor content service."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize dependencies for WebDataExtractorContentService."""
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Coletar conteudo pagina playwright."""
        return await self._port.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        return self._port.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )
