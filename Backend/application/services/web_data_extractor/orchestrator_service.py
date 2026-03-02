"""Document orchestrator service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from Backend import models

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
        """Initialize injected dependencies and runtime configuration for Web Data Extractor Orchestrator Service."""
        self.search = WebDataExtractorSearchService(port)
        self.content = WebDataExtractorContentService(port)
        self.metadata = WebDataExtractorMetadataService(port)
        self.llm = WebDataExtractorLLMService(port)
        self.ocr = WebDataExtractorOCRService(port)

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return self.search.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls publicas as part of this module workflow."""
        return await self.search.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls google as part of this module workflow."""
        return await self.search.buscar_urls_google(
            query=query,
            num_results=num_results,
        )

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        return await self.content.coletar_conteudo_pagina_playwright(url=url)

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        return self.content.extrair_texto_principal_com_trafilatura(
            html_content=html_content
        )

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Execute extrair metadados estruturados as part of this module workflow."""
        return self.metadata.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute normalizar dados de metadados as part of this module workflow."""
        return self.metadata.normalizar_dados_de_metadados(
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
        """Extrair dados produto com llm."""
        return await self.llm.extrair_dados_produto_com_llm(
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
        return await self.llm.extract_relevant_data_from_url(
            session=session,
            url=url,
            produto=produto,
        )

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self.ocr.extract_text_from_image_region(image_bytes)
