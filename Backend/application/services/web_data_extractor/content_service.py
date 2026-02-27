from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorContentService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._port.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._port.extrair_texto_principal_com_trafilatura(*args, **kwargs)
