from __future__ import annotations

import pytest

from Backend.application.services.limit_service_facade import LimitServiceFacade


class _LegacyLimitStub:
    def __init__(self) -> None:
        self.calls = []

    def verificar_limite_uso(self, *args, **kwargs):
        self.calls.append(("verificar_limite_uso", args, kwargs))
        return {"ok": True}

    async def verificar_creditos_disponiveis_geracao_ia(self, *args, **kwargs):
        self.calls.append(("verificar_creditos_disponiveis_geracao_ia", args, kwargs))
        return True


def test_limit_service_facade_delegates_sync_limit_check():
    legacy = _LegacyLimitStub()
    facade = LimitServiceFacade(port=legacy)

    result = facade.verificar_limite_uso("db", "user", "titulo")

    assert result == {"ok": True}
    assert legacy.calls[0][0] == "verificar_limite_uso"


@pytest.mark.asyncio
async def test_limit_service_facade_delegates_async_credit_check():
    legacy = _LegacyLimitStub()
    facade = LimitServiceFacade(port=legacy)

    result = await facade.verificar_creditos_disponiveis_geracao_ia(user="u")

    assert result is True
    assert legacy.calls[0][0] == "verificar_creditos_disponiveis_geracao_ia"
