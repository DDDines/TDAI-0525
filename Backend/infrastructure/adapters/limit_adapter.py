"""Document limit adapter module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from Backend import models
from Backend.infrastructure.runtime_modules.limit_module import (
    LimitWorkflow,
)


class LimitServiceAdapter:
    """OOP port adapter backed by the current limits implementation."""

    def __init__(self, runtime: LimitWorkflow | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for Limit Service Adapter."""
        self._runtime = runtime or LimitWorkflow()

    def verificar_limite_uso(
        self,
        session: Session,
        user: models.User,
        tipo_geracao_principal: str,
    ) -> int:
        """Execute verificar limite uso as part of this module workflow."""
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
        """Verificar creditos disponiveis geracao ia."""
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
        """Verificar e consumir creditos geracao ia."""
        return await self._runtime.verificar_e_consumir_creditos_geracao_ia(
            db=session,
            user_id=user_id,
            creditos_necessarios=creditos_necessarios,
        )

    def verificar_limite_produtos(
        self,
        session: Session,
        user: Any,
    ) -> None:
        """Bloqueia criacao de produtos quando o limite do plano e atingido."""
        return self._runtime.verificar_limite_produtos(db=session, user=user)

    def verificar_limite_enriquecimento(
        self,
        session: Session,
        user: Any,
    ) -> None:
        """Bloqueia inicio de enriquecimento web quando o limite mensal e atingido."""
        return self._runtime.verificar_limite_enriquecimento(db=session, user=user)
