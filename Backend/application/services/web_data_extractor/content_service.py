from __future__ import annotations

from typing import Optional

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        return await self._port.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        return self._port.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )
