from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorLLMService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await self._port.extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await self._port.extract_relevant_data_from_url(*args, **kwargs)
