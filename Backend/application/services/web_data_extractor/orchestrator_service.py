from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor.content_service import (
    WebDataExtractorContentService,
)
from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)
from Backend.application.services.web_data_extractor.llm_service import (
    WebDataExtractorLLMService,
)
from Backend.application.services.web_data_extractor.metadata_service import (
    WebDataExtractorMetadataService,
)
from Backend.application.services.web_data_extractor.ocr_service import (
    WebDataExtractorOCRService,
)
from Backend.application.services.web_data_extractor.search_service import (
    WebDataExtractorSearchService,
)


class WebDataExtractorOrchestratorService:
    """Servico OO unificado para extracao de dados da web."""

    def __init__(self, port: WebDataExtractorPort) -> None:
        self.search = WebDataExtractorSearchService(port)
        self.content = WebDataExtractorContentService(port)
        self.metadata = WebDataExtractorMetadataService(port)
        self.llm = WebDataExtractorLLMService(port)
        self.ocr = WebDataExtractorOCRService(port)

    def busca_publica_disponivel(self) -> bool:
        return self.search.busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await self.search.buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await self.search.buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await self.content.coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return self.content.extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self.metadata.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self.metadata.normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self.llm.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self.llm.extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, image_bytes: bytes):
        return self.ocr.extract_text_from_image_region(image_bytes)
