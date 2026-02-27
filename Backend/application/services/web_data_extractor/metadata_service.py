from __future__ import annotations

from typing import Any

from Backend.application.services.web_data_extractor.contracts import (
    WebDataExtractorPort,
)


class WebDataExtractorMetadataService:
    def __init__(self, port: WebDataExtractorPort) -> None:
        self._port = port

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return self._port.extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return self._port.normalizar_dados_de_metadados(*args, **kwargs)
