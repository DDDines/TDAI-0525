from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.web_data_extractor_runtime import (
    get_runtime_service,
)


def _default_web_data_extractor_runtime_service() -> Any:
    return get_runtime_service()


class WebDataExtractorServiceAdapter:
    """OOP port adapter backed by the current web extraction implementation."""

    def __init__(self, service: Any | None = None) -> None:
        self._service = service or _default_web_data_extractor_runtime_service()

    def busca_publica_disponivel(self) -> bool:
        return self._service.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._service.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._service.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._service.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._service.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._service.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._service.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._service.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._service.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._service.extract_text_from_image_region(*args, **kwargs)
