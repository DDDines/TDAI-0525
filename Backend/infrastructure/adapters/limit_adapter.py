from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.limit_module import (
    LimitWorkflow,
)


class LimitServiceAdapter:
    """OOP port adapter backed by the current limits implementation."""

    def __init__(self, runtime: LimitWorkflow | None = None) -> None:
        self._runtime = runtime or LimitWorkflow()

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._runtime.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._runtime.verificar_creditos_disponiveis_geracao_ia(
            *args,
            **kwargs,
        )

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._runtime.verificar_e_consumir_creditos_geracao_ia(
            *args,
            **kwargs,
        )
