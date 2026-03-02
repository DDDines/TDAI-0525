"""Module metadata service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorMetadataService:
    """Class WebDataExtractorMetadataService.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, port: WebDataExtractorPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Execute extrair_metadados_estruturados.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute normalizar_dados_de_metadados.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.normalizar_dados_de_metadados(
            metadata_bruta=metadata_bruta
        )
