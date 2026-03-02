"""Module limit adapter.

Contains backend logic related to limit adapter and documents its role in the OOP architecture.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models
from Backend.infrastructure.runtime_modules.limit_module import (
    LimitWorkflow,
)


class LimitServiceAdapter:
    """OOP port adapter backed by the current limits implementation."""

    def __init__(self, runtime: LimitWorkflow | None = None) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._runtime = runtime or LimitWorkflow()

    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Run verificar limite uso in this workflow."""
        return self._runtime.verificar_limite_uso(
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
        return await self._runtime.verificar_creditos_disponiveis_geracao_ia(
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
        return await self._runtime.verificar_e_consumir_creditos_geracao_ia(
            db=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )
