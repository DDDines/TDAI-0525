from __future__ import annotations

from typing import Any, Optional

from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.services import web_data_extractor_service


class LegacyWebDataExtractorBridge:
    """Bridge explicito para o modulo legado de extracao/enriquecimento web."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or web_data_extractor_service

    @staticmethod
    def _assert_legacy_allowed() -> None:
        assert_legacy_usage_allowed(
            "Backend.infrastructure.legacy.LegacyWebDataExtractorBridge"
        )

    def _call(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return getattr(self._module, method_name)(*args, **kwargs)

    async def _call_async(self, method_name: str, *args: Any, **kwargs: Any):
        self._assert_legacy_allowed()
        return await getattr(self._module, method_name)(*args, **kwargs)

    def busca_publica_disponivel(self) -> bool:
        return self._call("busca_publica_disponivel")

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self._call_async("buscar_urls_publicas", *args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self._call_async("buscar_urls_google", *args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self._call_async("coletar_conteudo_pagina_playwright", *args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self._call("extrair_texto_principal_com_trafilatura", *args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._call("extrair_metadados_estruturados", *args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._call("normalizar_dados_de_metadados", *args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._call_async("extrair_dados_produto_com_llm", *args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._call_async("extract_relevant_data_from_url", *args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return self._call("extract_text_from_image_region", *args, **kwargs)
