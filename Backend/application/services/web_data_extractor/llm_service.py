"""Module llm service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorLLMService:
    """Class WebDataExtractorLLMService.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute extrair_dados_produto_com_llm.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute extract_relevant_data_from_url.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.extract_relevant_data_from_url(
            session=session,
            url=url,
            produto=produto,
        )
