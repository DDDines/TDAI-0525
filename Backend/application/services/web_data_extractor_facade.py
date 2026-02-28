from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor import (
    WebDataExtractorOrchestratorService,
    WebDataExtractorPort,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import (
    WebDataExtractorServiceAdapter,
)


class WebDataExtractorFacade:
    """Explicit OOP facade for web extraction services."""

    def __init__(
        self,
        *,
        port: WebDataExtractorPort | None = None,
    ) -> None:
        effective_port = port or WebDataExtractorServiceAdapter()
        self._orchestrator = WebDataExtractorOrchestratorService(effective_port)
        self.search = self._orchestrator.search
        self.content = self._orchestrator.content
        self.llm = self._orchestrator.llm
        self.ocr = self._orchestrator.ocr

    def busca_publica_disponivel(self) -> bool:
        return self._orchestrator.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.coletar_conteudo_pagina_playwright(
            *args,
            **kwargs,
        )

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._orchestrator.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._orchestrator.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._orchestrator.extract_text_from_image_region(*args, **kwargs)
