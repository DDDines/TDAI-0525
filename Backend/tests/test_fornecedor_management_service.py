from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)


class _QueryStub:
    def __init__(self, first_result):
        self._first_result = first_result

    def filter(self, *args, **kwargs):
        _ = (args, kwargs)
        return self

    def first(self):
        return self._first_result


class _DbStub:
    def __init__(self, *, duplicate_result=None):
        self._duplicate_result = duplicate_result
        self.added = []
        self.committed = 0
        self.refreshed = 0

    def query(self, model):
        _ = model
        return _QueryStub(self._duplicate_result)

    def add(self, item):
        self.added.append(item)

    def commit(self):
        self.committed += 1

    def refresh(self, item):
        _ = item
        self.refreshed += 1


class _CrudFornecedoresStub:
    def __init__(self, fornecedor=None):
        self._fornecedor = fornecedor
        self.updated_calls = []
        self.deleted_calls = []

    def get_fornecedor(self, db, fornecedor_id):
        _ = (db, fornecedor_id)
        return self._fornecedor

    def update_fornecedor(self, *, db, db_fornecedor, fornecedor_update):
        _ = db
        self.updated_calls.append((db_fornecedor, fornecedor_update))
        if fornecedor_update.nome:
            db_fornecedor.nome = fornecedor_update.nome
        return db_fornecedor

    def delete_fornecedor(self, *, db, db_fornecedor):
        _ = db
        self.deleted_calls.append(db_fornecedor)
        return db_fornecedor


class _CrudHistoricoStub:
    def __init__(self):
        self.calls = []

    def create_registro_historico(self, db, payload):
        self.calls.append((db, payload))


class _RegistroHistoricoCreateStub:
    def __init__(self, **kwargs):
        self.data = kwargs


class _TipoAcaoSistemaEnumStub:
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"


class _FornecedorModelStub:
    user_id = object()
    nome = object()
    id = object()


class _ModelsStub:
    Fornecedor = _FornecedorModelStub
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _SchemasStub:
    RegistroHistoricoCreate = _RegistroHistoricoCreateStub


class _FuncStub:
    @staticmethod
    def lower(value):
        return value


def _build_service(*, fornecedor):
    crud_fornecedores = _CrudFornecedoresStub(fornecedor=fornecedor)
    crud_historico = _CrudHistoricoStub()
    service = FornecedorManagementService(
        models=_ModelsStub,
        schemas=_SchemasStub,
        crud_fornecedores=crud_fornecedores,
        crud_historico=crud_historico,
        sqlalchemy_func=_FuncStub,
    )
    return service, crud_fornecedores, crud_historico


def test_resolve_fornecedor_for_user_success():
    fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
    service, _, _ = _build_service(fornecedor=fornecedor)

    result = service.resolve_fornecedor_for_user(
        db=_DbStub(),
        fornecedor_id=5,
        current_user=SimpleNamespace(id=10, is_superuser=False),
        not_found_detail="nao encontrado",
        forbidden_detail="nao autorizado",
    )

    assert result is fornecedor


def test_resolve_fornecedor_for_user_raises_404():
    service, _, _ = _build_service(fornecedor=None)

    with pytest.raises(HTTPException) as exc:
        service.resolve_fornecedor_for_user(
            db=_DbStub(),
            fornecedor_id=5,
            current_user=SimpleNamespace(id=10, is_superuser=False),
            not_found_detail="nao encontrado",
            forbidden_detail="nao autorizado",
        )

    assert exc.value.status_code == 404
    assert exc.value.detail == "nao encontrado"


def test_resolve_fornecedor_for_user_raises_403():
    fornecedor = SimpleNamespace(id=5, user_id=99, nome="Fornecedor A")
    service, _, _ = _build_service(fornecedor=fornecedor)

    with pytest.raises(HTTPException) as exc:
        service.resolve_fornecedor_for_user(
            db=_DbStub(),
            fornecedor_id=5,
            current_user=SimpleNamespace(id=10, is_superuser=False),
            not_found_detail="nao encontrado",
            forbidden_detail="nao autorizado",
        )

    assert exc.value.status_code == 403


def test_update_fornecedor_records_historico():
    fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
    service, crud_fornecedores, crud_historico = _build_service(fornecedor=fornecedor)
    db = _DbStub(duplicate_result=None)

    updated = service.update_fornecedor(
        db=db,
        fornecedor_id=5,
        fornecedor_update=SimpleNamespace(nome="Fornecedor B"),
        current_user=SimpleNamespace(id=10, is_superuser=False),
    )

    assert updated.nome == "Fornecedor B"
    assert len(crud_fornecedores.updated_calls) == 1
    assert len(crud_historico.calls) == 1
    payload = crud_historico.calls[0][1].data
    assert payload["acao"] == "ATUALIZACAO"


def test_update_fornecedor_raises_for_duplicate_name():
    fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
    service, _, _ = _build_service(fornecedor=fornecedor)
    db = _DbStub(duplicate_result=object())

    with pytest.raises(HTTPException) as exc:
        service.update_fornecedor(
            db=db,
            fornecedor_id=5,
            fornecedor_update=SimpleNamespace(nome="Fornecedor B"),
            current_user=SimpleNamespace(id=10, is_superuser=False),
        )

    assert exc.value.status_code == 400


def test_update_mapping_persists_and_refreshes():
    fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A", default_column_mapping=None)
    service, _, _ = _build_service(fornecedor=fornecedor)
    db = _DbStub()

    updated = service.update_mapping(
        db=db,
        fornecedor_id=5,
        current_user=SimpleNamespace(id=10, is_superuser=False),
        mapping={"col_0": "nome_base"},
    )

    assert updated.default_column_mapping == {"col_0": "nome_base"}
    assert db.committed == 1
    assert db.refreshed == 1


def test_delete_fornecedor_records_historico():
    fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
    service, crud_fornecedores, crud_historico = _build_service(fornecedor=fornecedor)

    deleted = service.delete_fornecedor(
        db=_DbStub(),
        fornecedor_id=5,
        current_user=SimpleNamespace(id=10, is_superuser=False),
    )

    assert deleted is fornecedor
    assert len(crud_fornecedores.deleted_calls) == 1
    payload = crud_historico.calls[0][1].data
    assert payload["acao"] == "DELECAO"
