"""Metadata service.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any, Dict

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorMetadataService:
    """Encapsulates Web data extractor metadata service."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._port = port

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Process Extrair metadados estruturados."""
        return self._port.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Process Normalizar dados de metadados."""
        return self._port.normalizar_dados_de_metadados(
            metadata_bruta=metadata_bruta
        )
