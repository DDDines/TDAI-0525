"""Document llm service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorLLMService:
    """Encapsulates Web data extractor l l m service."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize injected dependencies and runtime configuration for Web Data Extractor LLMService."""
        self._port = port

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extrair dados produto com llm."""
        return await self._port.extrair_dados_produto_com_llm(
            texto_pagina=texto_pagina,
            metadados_normalizados=metadados_normalizados,
            campos_desejados=campos_desejados,
            produto_nome_base=produto_nome_base,
            user=user,
        )

    async def extract_relevant_data_from_url(
        self,
        *,
        session: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Extract relevant data from url."""
        return await self._port.extract_relevant_data_from_url(
            session=session,
            url=url,
            produto=produto,
        )
