from __future__ import annotations

from typing import Any

from Backend.services import web_data_extractor_service as legacy_web_data_extractor_service


class WebDataExtractorFacade:
    """Adaptador OO para o módulo legado de extração/enriquecimento web.

    Preserva compatibilidade com chamadas legadas e permite migração gradual
    para arquitetura orientada a objetos.
    """

    def __init__(
        self, legacy_module: Any = legacy_web_data_extractor_service
    ) -> None:
        self._legacy = legacy_module

    def busca_publica_disponivel(self) -> bool:
        return self._legacy.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._legacy.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._legacy.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._legacy.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._legacy.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._legacy.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._legacy._normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._legacy.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._legacy.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._legacy.extract_text_from_image_region(*args, **kwargs)

    def __getattr__(self, item: str) -> Any:
        return getattr(self._legacy, item)

