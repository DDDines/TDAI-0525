"""Additional coverage for limit runtime branches and workflow delegates."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException, status

from Backend.testing.runtime_apis import limit_service


class _UsageRepoStub:
    def __init__(self, *, usos_no_mes=0, geracoes_no_mes=0):
        self._usos_no_mes = usos_no_mes
        self._geracoes_no_mes = geracoes_no_mes

    def count_usos_ia_by_user_and_type_no_mes_corrente(self, *, user_id, tipo_geracao_prefix):
        _ = user_id, tipo_geracao_prefix
        return self._usos_no_mes

    def get_geracoes_ia_count_no_mes_corrente(self, *, user_id):
        _ = user_id
        return self._geracoes_no_mes


class _UserRepoStub:
    def __init__(self, user):
        self._user = user

    def get_user(self, *, user_id):
        _ = user_id
        return self._user


def _logger_factory(_name):
    return SimpleNamespace(info=lambda *_a, **_k: None, warning=lambda *_a, **_k: None)


def _build_runtime(*, usos_no_mes=0, geracoes_no_mes=0, user=None):
    return limit_service.LimitRuntime(
        usage_repository_factory=lambda _db: _UsageRepoStub(
            usos_no_mes=usos_no_mes,
            geracoes_no_mes=geracoes_no_mes,
        ),
        user_repository_factory=lambda _db: _UserRepoStub(user),
        logger_factory=_logger_factory,
    )


def test_limit_runtime_verificar_limite_uso_error_paths():
    runtime = _build_runtime(user=SimpleNamespace(id=1, plano=None))
    with pytest.raises(HTTPException) as no_plan:
        runtime.verificar_limite_uso("db", SimpleNamespace(id=1, plano=None), "titulo")
    assert no_plan.value.status_code == status.HTTP_403_FORBIDDEN

    plano = SimpleNamespace(limite_geracao_ia=2)
    user = SimpleNamespace(id=1, plano=plano)
    runtime = _build_runtime(usos_no_mes=2, user=user)

    with pytest.raises(HTTPException) as descricao_limit:
        runtime.verificar_limite_uso("db", user, "descricao")
    assert descricao_limit.value.status_code == status.HTTP_403_FORBIDDEN
    assert "descricoes" in descricao_limit.value.detail

    with pytest.raises(HTTPException) as titulo_limit:
        runtime.verificar_limite_uso("db", user, "titulo")
    assert titulo_limit.value.status_code == status.HTTP_403_FORBIDDEN
    assert "titulos" in titulo_limit.value.detail


@pytest.mark.asyncio
async def test_limit_runtime_credit_paths_and_workflow_delegates():
    unlimited_user = SimpleNamespace(id=1, limite_geracao_ia=None, plano=SimpleNamespace(limite_geracao_ia=None))
    runtime = _build_runtime(user=unlimited_user)
    assert await runtime.verificar_creditos_disponiveis_geracao_ia("db", user_id=1) is True

    limited_user = SimpleNamespace(id=1, limite_geracao_ia=0, plano=SimpleNamespace(limite_geracao_ia=3))
    runtime = _build_runtime(geracoes_no_mes=2, user=limited_user)
    assert await runtime.verificar_creditos_disponiveis_geracao_ia("db", user_id=1) is True
    assert await runtime.verificar_e_consumir_creditos_geracao_ia("db", user_id=1, creditos_necessarios=2) is False

    called = []

    class FakeRuntime:
        def verificar_limite_uso(self, **kwargs):
            called.append(("limite", kwargs))
            return 7

        async def verificar_creditos_disponiveis_geracao_ia(self, **kwargs):
            called.append(("creditos", kwargs))
            return True

        async def verificar_e_consumir_creditos_geracao_ia(self, **kwargs):
            called.append(("consumo", kwargs))
            return False

    workflow = limit_service.LimitWorkflow(runtime=FakeRuntime())
    assert workflow.verificar_limite_uso("db", SimpleNamespace(id=1), "titulo") == 7
    assert await workflow.verificar_creditos_disponiveis_geracao_ia("db", user_id=1) is True
    assert await workflow.verificar_e_consumir_creditos_geracao_ia("db", user_id=1) is False
    assert [item[0] for item in called] == ["limite", "creditos", "consumo"]
