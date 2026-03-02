"""Module content service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    """Class WebDataExtractorContentService.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar_conteudo_pagina_playwright.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Execute extrair_texto_principal_com_trafilatura.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )
