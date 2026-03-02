"""Module limit runtime service.

Contains backend logic related to limit runtime service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models
from Backend.infrastructure.runtime_modules.limit_module import LimitWorkflow


class LimitRuntimeService:
    """Explicit runtime service surface for limits and credits flows."""

    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._workflow = LimitWorkflow()

    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Run verificar limite uso in this workflow."""
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
        """Run verificar creditos disponiveis geracao ia in this workflow."""
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
        """Run verificar e consumir creditos geracao ia in this workflow."""
        return await self._workflow.verificar_e_consumir_creditos_geracao_ia(
            db=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )
