from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.web_data_extractor.contracts import WebDataExtractorPort


class IAGenerationPort(Protocol):
    async def gerar_titulos_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]: ...

    async def gerar_descricao_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str: ...

    async def gerar_titulos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]: ...

    async def gerar_descricao_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str: ...

    async def sugerir_valores_atributos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse: ...


class LimitPort(Protocol):
    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int: ...

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool: ...

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool: ...


class ValidationPort(Protocol):
    def run_validation_crew(self, raw_data: Any): ...


__all__ = [
    "FileProcessingPort",
    "WebDataExtractorPort",
    "IAGenerationPort",
    "LimitPort",
    "ValidationPort",
]
