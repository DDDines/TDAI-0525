from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

from sqlalchemy.orm import Session

from Backend import models


class WebDataExtractorPort(Protocol):
    def busca_publica_disponivel(self) -> bool: ...

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]: ...

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]: ...

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]: ...

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]: ...

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]: ...

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]: ...

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]: ...

    async def extract_relevant_data_from_url(
        self,
        *,
        session: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto: ...

    def extract_text_from_image_region(self, image_bytes: bytes) -> Any: ...
