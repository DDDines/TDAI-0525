from __future__ import annotations

from typing import Any, Protocol

from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.web_data_extractor.contracts import WebDataExtractorPort


class IAGenerationPort(Protocol):
    async def gerar_titulos_com_openai(self, *args: Any, **kwargs: Any): ...

    async def gerar_descricao_com_openai(self, *args: Any, **kwargs: Any): ...

    async def gerar_titulos_com_gemini(self, *args: Any, **kwargs: Any): ...

    async def gerar_descricao_com_gemini(self, *args: Any, **kwargs: Any): ...

    async def sugerir_valores_atributos_com_gemini(self, *args: Any, **kwargs: Any): ...


class LimitPort(Protocol):
    def verificar_limite_uso(self, *args: Any, **kwargs: Any): ...

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any): ...

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any): ...


class ValidationPort(Protocol):
    def run_validation_crew(self, raw_data: Any): ...


__all__ = [
    "FileProcessingPort",
    "WebDataExtractorPort",
    "IAGenerationPort",
    "LimitPort",
    "ValidationPort",
]
