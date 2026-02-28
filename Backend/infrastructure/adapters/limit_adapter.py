from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.limit_runtime import (
    get_runtime_service,
)


def _default_limit_runtime_service() -> Any:
    return get_runtime_service()


class LimitServiceAdapter:
    """OOP port adapter backed by the current limits implementation."""

    def __init__(self, service: Any | None = None) -> None:
        self._service = service or _default_limit_runtime_service()

    def verificar_limite_uso(self, *args: Any, **kwargs: Any):
        return self._service.verificar_limite_uso(*args, **kwargs)

    async def verificar_creditos_disponiveis_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._service.verificar_creditos_disponiveis_geracao_ia(
            *args,
            **kwargs,
        )

    async def verificar_e_consumir_creditos_geracao_ia(self, *args: Any, **kwargs: Any):
        return await self._service.verificar_e_consumir_creditos_geracao_ia(
            *args,
            **kwargs,
        )
