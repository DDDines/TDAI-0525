from __future__ import annotations

from typing import Any


def _default_limit_module() -> Any:
    from Backend.services import limit_service

    return limit_service


class LimitServiceAdapter:
    """OOP port adapter backed by the current limits implementation."""

    def __init__(self, module: Any | None = None) -> None:
        self._module = module or _default_limit_module()

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._module.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._module.verificar_creditos_disponiveis_geracao_ia(*args, **kwargs)

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._module.verificar_e_consumir_creditos_geracao_ia(*args, **kwargs)
