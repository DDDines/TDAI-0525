from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules import web_data_extractor_module


class WebDataExtractorRuntimeService:
    """Explicit runtime service surface for web data extraction flows."""

    def __init__(self) -> None:
        self._search = None
        self._content = None
        self._support = None

    def _get_search(self):
        if self._search is None:
            self._search = web_data_extractor_module.get_web_search_workflow()
        return self._search

    def _get_content(self):
        if self._content is None:
            self._content = web_data_extractor_module.get_web_content_collection_workflow()
        return self._content

    def _get_support(self):
        if self._support is None:
            self._support = web_data_extractor_module.get_web_extraction_support_workflow()
        return self._support

    def busca_publica_disponivel(self) -> bool:
        return self._get_search().busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._get_search().buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._get_search().buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._get_content().coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._get_support().extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._get_support().extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._get_support().normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._get_support().extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._get_support().extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._get_support().extract_text_from_image_region(*args, **kwargs)


web_data_extractor_runtime_service = WebDataExtractorRuntimeService()
