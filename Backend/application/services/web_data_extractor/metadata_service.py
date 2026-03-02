"""Document metadata service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorMetadataService:
    """Represent Web Data Extractor Metadata Service and centralize its responsibilities inside this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize injected dependencies and runtime configuration for Web Data Extractor Metadata Service."""
        self._port = port

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Execute extrair metadados estruturados as part of this module workflow."""
        return self._port.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute normalizar dados de metadados as part of this module workflow."""
        return self._port.normalizar_dados_de_metadados(
            metadata_bruta=metadata_bruta
        )
