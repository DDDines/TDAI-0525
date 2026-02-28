from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime_modules.limit_module import get_limit_workflow


class LimitRuntimeService:
    """Explicit runtime service surface for limits and credits flows."""

    def __init__(self) -> None:
        self._workflow = get_limit_workflow()

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._workflow.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._workflow.verificar_creditos_disponiveis_geracao_ia(
            *args,
            **kwargs,
        )

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._workflow.verificar_e_consumir_creditos_geracao_ia(
            *args,
            **kwargs,
        )


limit_runtime_service = LimitRuntimeService()

