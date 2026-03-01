from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.web_data_extractor_module import (
    WebDataExtractorRuntime,
)


class WebDataExtractorServiceAdapter:
    """OOP port adapter backed by the current web extraction implementation."""

    def __init__(self, runtime: WebDataExtractorRuntime | None = None) -> None:
        self._runtime = runtime or WebDataExtractorRuntime()

    def busca_publica_disponivel(self) -> bool:
        return self._runtime.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._runtime.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._runtime.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._runtime.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._runtime.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._runtime.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._runtime.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._runtime.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._runtime.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._runtime.extract_text_from_image_region(*args, **kwargs)
