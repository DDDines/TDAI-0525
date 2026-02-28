from __future__ import annotations

from typing import Any

from Backend.application.services.ports import LimitPort
from Backend.infrastructure.adapters.limit_adapter import LimitServiceAdapter


class LimitServiceFacade:
    """Explicit OOP facade for limits and credits service."""

    def __init__(
        self,
        *,
        port: LimitPort | None = None,
    ) -> None:
        self._port = port or LimitServiceAdapter()

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._port.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        return await self._port.verificar_creditos_disponiveis_geracao_ia(
            *args,
            **kwargs,
        )

    async def verificar_e_consumir_creditos_geracao_ia(
        self,
        *args: Any,
        **kwargs: Any,
    ):
        return await self._port.verificar_e_consumir_creditos_geracao_ia(
            *args,
            **kwargs,
        )
