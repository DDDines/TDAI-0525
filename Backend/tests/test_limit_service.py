from __future__ import annotations

import pytest

from Backend.application.services.limit_service import LimitService


class _PortStub:
    def __init__(self) -> None:
        self.calls = []

    def verificar_limite_uso(self, *args, **kwargs):
        self.calls.append(("verificar_limite_uso", args, kwargs))
        return {"ok": True}

    async def verificar_creditos_disponiveis_geracao_ia(self, *args, **kwargs):
        self.calls.append(("verificar_creditos_disponiveis_geracao_ia", args, kwargs))
        return True


def test_limit_service_delegates_sync_limit_check():
    port = _PortStub()
    service = LimitService(port=port)

    result = service.verificar_limite_uso("db", "user", "titulo")

    assert result == {"ok": True}
    assert port.calls[0][0] == "verificar_limite_uso"


@pytest.mark.asyncio
async def test_limit_service_delegates_async_credit_check():
    port = _PortStub()
    service = LimitService(port=port)

    result = await service.verificar_creditos_disponiveis_geracao_ia(user="u")

    assert result is True
    assert port.calls[0][0] == "verificar_creditos_disponiveis_geracao_ia"
