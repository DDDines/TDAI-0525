"""Module metadata service.

Contains backend logic related to metadata service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Dict

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorMetadataService:
    """Represent web data extractor metadata service and centralize responsibilities for this module."""
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Run extrair metadados estruturados in this workflow."""
        return self._port.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run normalizar dados de metadados in this workflow."""
        return self._port.normalizar_dados_de_metadados(
            metadata_bruta=metadata_bruta
        )
