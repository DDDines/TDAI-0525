"""Limit service.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from Backend import models
from Backend.application.services.ports import LimitPort


class LimitService:
    """Explicit OOP service for usage limits and credits."""

    def __init__(
        self,
        *,
        port: LimitPort,
    ) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._port = port

    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Process Verificar limite uso."""
        return self._port.verificar_limite_uso(
            session=session,
            user=user,
            tipo_geracao_principal=tipo_geracao_principal,
        )

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Process Verificar creditos disponiveis geracao ia."""
        return await self._port.verificar_creditos_disponiveis_geracao_ia(
            session=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        session: Session,
        user_id: int,
        creditos_necessarios: int = 1,
    ) -> bool:
        """Process Verificar e consumir creditos geracao ia."""
        return await self._port.verificar_e_consumir_creditos_geracao_ia(
            session=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )
