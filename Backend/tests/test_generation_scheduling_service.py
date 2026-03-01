from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)


class _CrudProdutosStub:
    def __init__(self, produto=None):
        self.produto = produto
        self.updated = []

    def get_produto(self, db, *, produto_id: int):
        _ = (db, produto_id)
        return self.produto

    def update_produto(self, db, *, db_produto, produto_update):
        self.updated.append((db, db_produto, produto_update))
        return db_produto


class _SchemasStub:
    class ProdutoUpdate:
        def __init__(self, **kwargs):
            self.payload = kwargs


class _ModelsStub:
    class StatusGeracaoIAEnum:
        PENDENTE = "PENDENTE"


class _BackgroundTasksStub:
    def __init__(self):
        self.calls = []

    def add_task(self, task_executor, **kwargs):
        self.calls.append((task_executor, kwargs))


def _build_service(produto=None):
    crud_stub = _CrudProdutosStub(produto=produto)
    service = GenerationSchedulingService(
        schemas=_SchemasStub,
        models=_ModelsStub,
    )
    return service, crud_stub


def test_validate_product_access_not_found():
    service, _ = _build_service(produto=None)
    user = SimpleNamespace(id=1, is_superuser=False)

    with pytest.raises(HTTPException) as exc:
        service.validate_product_access(
            product_repo=_CrudProdutosStub(produto=None),
            produto_id=10,
            current_user=user,
        )

    assert exc.value.status_code == 404


def test_validate_product_access_forbidden():
    produto = SimpleNamespace(user_id=2)
    service, _ = _build_service(produto=produto)
    user = SimpleNamespace(id=1, is_superuser=False)

    with pytest.raises(HTTPException) as exc:
        service.validate_product_access(
            product_repo=_CrudProdutosStub(produto=produto),
            produto_id=10,
            current_user=user,
        )

    assert exc.value.status_code == 403


def test_validate_product_access_success():
    produto = SimpleNamespace(user_id=1)
    service, _ = _build_service(produto=produto)
    user = SimpleNamespace(id=1, is_superuser=False)

    result = service.validate_product_access(
        product_repo=_CrudProdutosStub(produto=produto),
        produto_id=10,
        current_user=user,
    )

    assert result is produto


def test_mark_pending_status_updates_expected_field():
    produto = SimpleNamespace(user_id=1)
    service, crud_stub = _build_service(produto=produto)

    service.mark_pending_status(
        product_repo=crud_stub,
        db_produto=produto,
        generation_type="titulo",
    )

    assert len(crud_stub.updated) == 1
    _, _, produto_update = crud_stub.updated[0]
    assert produto_update.payload == {"status_titulo_ia": "PENDENTE"}


def test_enqueue_generation_task_forwards_expected_kwargs():
    service, _ = _build_service(produto=SimpleNamespace(user_id=1))
    background_tasks = _BackgroundTasksStub()

    def _executor(**kwargs):
        return kwargs

    service.enqueue_generation_task(
        background_tasks=background_tasks,
        task_executor=_executor,
        db_session_factory=lambda: None,
        user_id=7,
        produto_id=8,
        generation_type="descricao",
        generation_func=object(),
        tamanho_palavras=150,
    )

    assert len(background_tasks.calls) == 1
    _, kwargs = background_tasks.calls[0]
    assert kwargs["user_id"] == 7
    assert kwargs["produto_id"] == 8
    assert kwargs["tipo_geracao_principal"] == "descricao"
    assert kwargs["tamanho_palavras"] == 150
