from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.web_data_extractor_runtime import (
    get_runtime_module,
)


def _default_web_data_extractor_module() -> Any:
    return get_runtime_module()


class WebDataExtractorServiceAdapter:
    """OOP port adapter backed by the current web extraction implementation."""

    def __init__(self, module: Any | None = None) -> None:
        self._module = module or _default_web_data_extractor_module()

    def busca_publica_disponivel(self) -> bool:
        runtime = getattr(self._module, "_web_search_engine_runtime", None)
        if runtime is not None:
            return runtime.busca_publica_disponivel()
        return self._module.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_search_workflow", None)
        if workflow is not None:
            return await workflow.buscar_urls_publicas(*args, **kwargs)
        return await self._module.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_search_workflow", None)
        if workflow is not None:
            return await workflow.buscar_urls_google(*args, **kwargs)
        return await self._module.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_content_collection_workflow", None)
        if workflow is not None:
            return await workflow.coletar_conteudo_pagina_playwright(*args, **kwargs)
        return await self._module.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return workflow.extrair_texto_principal_com_trafilatura(*args, **kwargs)
        return self._module.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return workflow.extrair_metadados_estruturados(*args, **kwargs)
        return self._module.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return workflow.normalizar_dados_de_metadados(*args, **kwargs)
        return self._module.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return await workflow.extrair_dados_produto_com_llm(*args, **kwargs)
        return await self._module.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return await workflow.extract_relevant_data_from_url(*args, **kwargs)
        return await self._module.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        workflow = getattr(self._module, "_web_extraction_support_workflow", None)
        if workflow is not None:
            return workflow.extract_text_from_image_region(*args, **kwargs)
        return self._module.extract_text_from_image_region(*args, **kwargs)
