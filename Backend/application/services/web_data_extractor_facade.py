from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor_components import (
    WebContentService,
    WebLLMService,
    WebOCRService,
    WebSearchService,
)
from Backend.services import web_data_extractor_service as legacy_web_data_extractor_service


class WebDataExtractorFacade:
    """Adaptador OO para o módulo legado de extração/enriquecimento web.

    Preserva compatibilidade com chamadas legadas e permite migração gradual
    para arquitetura orientada a objetos.
    """

    def __init__(
        self, legacy_module: Any = legacy_web_data_extractor_service
    ) -> None:
        legacy_adapter = getattr(
            legacy_module, "web_data_extractor_legacy_service", legacy_module
        )
        self._legacy = legacy_adapter
        self.search = WebSearchService(legacy_adapter)
        self.content = WebContentService(legacy_adapter)
        self.llm = WebLLMService(legacy_adapter)
        self.ocr = WebOCRService(legacy_adapter)

    def busca_publica_disponivel(self) -> bool:
        return self.search.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self.search.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self.search.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self.content.coletar_conteudo_pagina_playwright(
            *args, **kwargs
        )

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self.content.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self.content.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self.content.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self.llm.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self.llm.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self.ocr.extract_text_from_image_region(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._legacy, item)
