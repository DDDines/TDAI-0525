from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from Backend.testing.runtime_apis import limit_service


class _CrudStub:
    def __init__(self, *, usos_no_mes: int = 0, geracoes_no_mes: int = 0) -> None:
        self._usos_no_mes = usos_no_mes
        self._geracoes_no_mes = geracoes_no_mes

    def count_usos_ia_by_user_and_type_no_mes_corrente(self, *_args, **_kwargs):
        return self._usos_no_mes

    def get_geracoes_ia_count_no_mes_corrente(self, *_args, **_kwargs):
        return self._geracoes_no_mes


class _CrudUsersStub:
    def __init__(self, user) -> None:
        self._user = user

    def get_user(self, *_args, **_kwargs):
        return self._user


def _logger_factory(_name):
    return SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None)


def _build_runtime(*, usos_no_mes: int = 0, geracoes_no_mes: int = 0, user=None):
    return limit_service._LimitRuntime(
        crud_module=_CrudStub(usos_no_mes=usos_no_mes, geracoes_no_mes=geracoes_no_mes),
        crud_users_module=_CrudUsersStub(user),
        logger_factory=_logger_factory,
    )


def test_runtime_verificar_limite_uso_retorna_saldo():
    plano = SimpleNamespace(limite_geracao_ia=10)
    user = SimpleNamespace(id=1, plano=plano, limite_geracao_ia=None)
    runtime = _build_runtime(usos_no_mes=3, user=user)

    remaining = runtime.verificar_limite_uso("db", user, "descricao")

    assert remaining == 7


def test_runtime_verificar_limite_uso_ilimitado_retorna_menos_um():
    plano = SimpleNamespace(limite_geracao_ia=0)
    user = SimpleNamespace(id=1, plano=plano, limite_geracao_ia=None)
    runtime = _build_runtime(user=user)

    remaining = runtime.verificar_limite_uso("db", user, "titulo")

    assert remaining == -1


def test_runtime_verificar_limite_uso_tipo_invalido_dispara_400():
    plano = SimpleNamespace(limite_geracao_ia=10)
    user = SimpleNamespace(id=1, plano=plano, limite_geracao_ia=None)
    runtime = _build_runtime(user=user)

    with pytest.raises(HTTPException) as exc:
        runtime.verificar_limite_uso("db", user, "invalido")

    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_runtime_verificar_creditos_disponiveis_user_inexistente_dispara_404():
    runtime = _build_runtime(user=None)

    with pytest.raises(HTTPException) as exc:
        await runtime.verificar_creditos_disponiveis_geracao_ia("db", user_id=123)

    assert exc.value.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_runtime_verificar_creditos_disponiveis_respeita_limite():
    plano = SimpleNamespace(limite_geracao_ia=5)
    user = SimpleNamespace(id=1, plano=plano, limite_geracao_ia=5)
    runtime = _build_runtime(geracoes_no_mes=4, user=user)

    assert await runtime.verificar_creditos_disponiveis_geracao_ia("db", user_id=1) is True
    assert (
        await runtime.verificar_creditos_disponiveis_geracao_ia(
            "db",
            user_id=1,
            creditos_necessarios=2,
        )
        is False
    )


@pytest.mark.asyncio
async def test_legacy_service_delega_para_workflow(monkeypatch):
    called = {}

    async def _fake_verificar(*args, **kwargs):
        called["args"] = args
        called["kwargs"] = kwargs
        return True

    monkeypatch.setattr(limit_service, "verificar_creditos_disponiveis_geracao_ia", _fake_verificar)

    result = await limit_service.limit_service_legacy_service.verificar_creditos_disponiveis_geracao_ia(
        "db",
        user_id=9,
    )

    assert result is True
    assert called["kwargs"] == {"user_id": 9}

