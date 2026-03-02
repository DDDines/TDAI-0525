"""Module limit runtime service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models
from Backend.infrastructure.runtime_modules.limit_module import LimitWorkflow


class LimitRuntimeService:
    """Explicit runtime service surface for limits and credits flows."""

    def __init__(self) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._workflow = LimitWorkflow()

    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Execute verificar_limite_uso.

        This callable is documented to make behavior explicit for readers.
        """
        return self._workflow.verificar_limite_uso(
            db=session,
            user=user,
            tipo_geracao_principal=tipo_geracao_principal,
        )

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Execute verificar_creditos_disponiveis_geracao_ia.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._workflow.verificar_creditos_disponiveis_geracao_ia(
            db=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Execute verificar_e_consumir_creditos_geracao_ia.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._workflow.verificar_e_consumir_creditos_geracao_ia(
            db=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )
