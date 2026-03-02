"""Module ia generation adapter.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.infrastructure.runtime_modules.ia_generation_module import (
    IAGenerationWorkflow,
)


class IAGenerationServiceAdapter:
    """OOP port adapter backed by the current IA generation implementation."""

    def __init__(self, runtime: IAGenerationWorkflow | None = None) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._runtime = runtime or IAGenerationWorkflow()

    async def gerar_titulos_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Execute gerar_titulos_com_openai.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._runtime.gerar_titulos_com_openai(
            db=session,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_openai(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Execute gerar_descricao_com_openai.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._runtime.gerar_descricao_com_openai(
            db=session,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        num_titulos: int = 3,
    ) -> list[str]:
        """Execute gerar_titulos_com_gemini.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._runtime.gerar_titulos_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        """Execute gerar_descricao_com_gemini.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._runtime.gerar_descricao_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def sugerir_valores_atributos_com_gemini(
        self,
        *,
        session: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        """Execute sugerir_valores_atributos_com_gemini.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._runtime.sugerir_valores_atributos_com_gemini(
            db=session,
            produto_id=produto_id,
            user=user,
        )
