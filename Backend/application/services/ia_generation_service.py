"""Module ia generation service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.ports import IAGenerationPort


class IAGenerationService:
    """Explicit OOP service for IA generation flows."""

    def __init__(
        self,
        *,
        port: IAGenerationPort,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

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
        return await self._port.gerar_titulos_com_openai(
            session=session,
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
        return await self._port.gerar_descricao_com_openai(
            session=session,
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
        return await self._port.gerar_titulos_com_gemini(
            session=session,
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
        return await self._port.gerar_descricao_com_gemini(
            session=session,
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
        return await self._port.sugerir_valores_atributos_com_gemini(
            session=session,
            produto_id=produto_id,
            user=user,
        )
