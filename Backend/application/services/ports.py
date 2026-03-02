"""Document ports module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Protocol

from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.web_data_extractor.contracts import WebDataExtractorPort


class IAGenerationPort(Protocol):
    """Represent IAGeneration Port and centralize its responsibilities inside this module."""
    async def gerar_titulos_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Generate SEO titles with OpenAI for a product."""
        ...

    async def gerar_descricao_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Generate a product description with OpenAI."""
        ...

    async def gerar_titulos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Generate SEO titles with Gemini for a product."""
        ...

    async def gerar_descricao_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Generate a product description with Gemini."""
        ...

    async def sugerir_valores_atributos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        """Suggest dynamic attribute values with Gemini."""
        ...


class LimitPort(Protocol):
    """Represent Limit Port and centralize its responsibilities inside this module."""
    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Return the credit cost for the requested generation action."""
        ...

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Check whether the user has enough credits before generation."""
        ...

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Validate and consume credits in a single transactional operation."""
        ...


class ValidationPort(Protocol):
    """Represent Validation Port and centralize its responsibilities inside this module."""
    def run_validation_crew(self, raw_data: Any):
        """Validate and normalize raw extraction data."""
        ...


__all__ = [
    "FileProcessingPort",
    "WebDataExtractorPort",
    "IAGenerationPort",
    "LimitPort",
    "ValidationPort",
]
