"""Document contracts module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy.orm import Session

from Backend import models


class WebDataExtractorPort(Protocol):
    """Represent Web Data Extractor Port and centralize its responsibilities inside this module."""
    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        ...

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Search candidate URLs using the public search fallback."""
        ...

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Search candidate URLs using Google CSE."""
        ...

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Fetch rendered HTML content from a URL with Playwright."""
        ...

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Extract the main article-like text from raw HTML."""
        ...

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Extract structured metadata (JSON-LD/OpenGraph/etc.) from HTML."""
        ...

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Normalize raw metadata fields into the internal schema."""
        ...

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Use LLM extraction to produce enriched product fields."""
        ...

    async def extract_relevant_data_from_url(
        self,
        *,
        session: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Enrich one product with relevant data from a target URL."""
        ...

    def extract_text_from_image_region(self, image_bytes: bytes) -> Any:
        """Run OCR extraction for a cropped image region."""
        ...
