"""Web data extractor adapter.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from Backend import models
from Backend.infrastructure.runtime_modules.web_data_extractor_module import (
    WebDataExtractorRuntime,
)


class WebDataExtractorServiceAdapter:
    """OOP port adapter backed by the current web extraction implementation."""

    def __init__(self, runtime: WebDataExtractorRuntime | None = None) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._runtime = runtime or WebDataExtractorRuntime()

    def busca_publica_disponivel(self) -> bool:
        """Process Busca publica disponivel."""
        return self._runtime.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Process Buscar urls publicas."""
        return await self._runtime.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Process Buscar urls google."""
        return await self._runtime.buscar_urls_google(
            query=query,
            num_results=num_results,
        )

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Process Coletar conteudo pagina playwright."""
        return await self._runtime.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Process Extrair texto principal com trafilatura."""
        return self._runtime.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Process Extrair metadados estruturados."""
        return self._runtime.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process Normalizar dados de metadados."""
        return self._runtime.normalizar_dados_de_metadados(
            metadata_bruta=metadata_bruta
        )

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Process Extrair dados produto com llm."""
        return await self._runtime.extrair_dados_produto_com_llm(
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
        return await self._runtime.extract_relevant_data_from_url(
            session=session,
            url=url,
            produto=produto,
        )

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self._runtime.extract_text_from_image_region(image_bytes=image_bytes)
