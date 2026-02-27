from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.routers.auth_utils import _AuthUtilsWorkflow
from Backend.routers.historico import _HistoricoWorkflow
from Backend.routers.search import _SearchWorkflow


@pytest.mark.asyncio
async def test_auth_workflow_get_current_user_usa_runtime_injetado():
    called = []

    class FakeRuntime:
        def decode_token(self, token, secret_key):
            called.append(("decode", token, secret_key))
            return SimpleNamespace(user_id=123)

        def get_user(self, db, user_id):
            called.append(("get_user", db, user_id))
            return SimpleNamespace(id=user_id, is_active=True, is_superuser=False)

    workflow = _AuthUtilsWorkflow(runtime=FakeRuntime())
    user = await workflow.get_current_user(request=object(), db="db", token="abc")

    assert user.id == 123
    assert called[0][0] == "decode"
    assert called[1] == ("get_user", "db", 123)


@pytest.mark.asyncio
async def test_auth_workflow_get_current_user_lanca_401_quando_payload_invalido():
    class FakeRuntime:
        def decode_token(self, token, secret_key):
            return None

        def get_user(self, db, user_id):
            return None

    workflow = _AuthUtilsWorkflow(runtime=FakeRuntime())

    with pytest.raises(HTTPException) as exc_info:
        await workflow.get_current_user(request=object(), db="db", token="abc")

    assert exc_info.value.status_code == 401


def test_historico_workflow_lista_historico_com_runtime_injetado():
    called = []

    class FakeRuntime:
        def get_registros_historico(self, db, *, user_id, skip, limit):
            called.append(("items", db, user_id, skip, limit))
            return []

        def count_registros_historico(self, db, *, user_id):
            called.append(("count", db, user_id))
            return 25

        def get_tipos_acao(self):
            called.append(("tipos",))
            return ["CRIACAO", "ATUALIZACAO"]

    workflow = _HistoricoWorkflow(runtime=FakeRuntime())
    current_user = SimpleNamespace(id=77, is_superuser=False)

    page = workflow.list_historico(db="db", current_user=current_user, skip=10, limit=10)

    assert page.total_items == 25
    assert page.page == 2
    assert page.limit == 10
    assert called[0] == ("items", "db", 77, 10, 10)
    assert called[1] == ("count", "db", 77)


def test_historico_workflow_get_tipos_acao_delega_runtime():
    class FakeRuntime:
        def get_registros_historico(self, db, *, user_id, skip, limit):
            return []

        def count_registros_historico(self, db, *, user_id):
            return 0

        def get_tipos_acao(self):
            return ["CRIACAO", "DELECAO"]

    workflow = _HistoricoWorkflow(runtime=FakeRuntime())
    assert workflow.get_tipos_acao() == ["CRIACAO", "DELECAO"]


def test_search_workflow_delega_runtime_injetado():
    called = []

    class FakeRuntime:
        def search_all(self, **kwargs):
            called.append(kwargs)
            return {"ok": True}

    workflow = _SearchWorkflow(runtime=FakeRuntime())
    result = workflow.search_all(
        db="db",
        current_user=SimpleNamespace(id=1),
        q="abc",
        limit=5,
    )

    assert result == {"ok": True}
    assert called[0]["db"] == "db"
    assert called[0]["q"] == "abc"
    assert called[0]["limit"] == 5
