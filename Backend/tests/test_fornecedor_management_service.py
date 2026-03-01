from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)


class _FornecedorRepoStub:
    def __init__(self, fornecedor=None):
        self._fornecedor = fornecedor
        self.created_calls = []
        self.updated_calls = []
        self.deleted_calls = []
        self.list_items = []
        self.list_total = 0
        self.has_duplicate_name = False
        self.mapping_updates = []

    def get_fornecedor(self, *, fornecedor_id):
        _ = fornecedor_id
        return self._fornecedor

    def create_fornecedor(self, *, fornecedor, user_id):
        created = SimpleNamespace(id=fornecedor.id, nome=fornecedor.nome, user_id=user_id)
        self.created_calls.append((fornecedor, user_id))
        return created

    def get_fornecedores_by_user(self, *, user_id, is_admin, skip, limit, search):
        _ = (user_id, is_admin, skip, limit, search)
        return self.list_items

    def count_fornecedores_by_user(self, *, user_id, is_admin, search):
        _ = (user_id, is_admin, search)
        return self.list_total

    def exists_fornecedor_with_name_for_user(self, *, user_id, nome, exclude_id):
        _ = (user_id, nome, exclude_id)
        return self.has_duplicate_name

    def update_fornecedor(self, *, db_fornecedor, fornecedor_update):
        self.updated_calls.append((db_fornecedor, fornecedor_update))
        if fornecedor_update.nome:
            db_fornecedor.nome = fornecedor_update.nome
        return db_fornecedor

    def set_default_column_mapping(self, *, db_fornecedor, mapping):
        db_fornecedor.default_column_mapping = mapping
        self.mapping_updates.append((db_fornecedor, mapping))
        return db_fornecedor

    def delete_fornecedor(self, *, db_fornecedor):
        self.deleted_calls.append(db_fornecedor)
        return db_fornecedor


class _HistoricoRepoStub:
    def __init__(self):
        self.calls = []

    def create_registro_historico(self, payload):
        self.calls.append(payload)


class _RegistroHistoricoCreateStub:
    def __init__(self, **kwargs):
        self.data = kwargs


class _TipoAcaoSistemaEnumStub:
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"


class _ModelsStub:
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _SchemasStub:
    RegistroHistoricoCreate = _RegistroHistoricoCreateStub


class _TopLevelFunctionSurface:

    def _build_service(*, fornecedor):
        fornecedor_repo = _FornecedorRepoStub(fornecedor=fornecedor)
        historico_repo = _HistoricoRepoStub()
        service = FornecedorManagementService(
            models=_ModelsStub,
            schemas=_SchemasStub,
            fornecedor_repo=fornecedor_repo,
            historico_repo=historico_repo,
        )
        return service, fornecedor_repo, historico_repo

    def test_resolve_fornecedor_for_user_success():
        fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
        service, _, _ = _build_service(fornecedor=fornecedor)
    
        result = service.resolve_fornecedor_for_user(
            fornecedor_id=5,
            current_user=SimpleNamespace(id=10, is_superuser=False),
            not_found_detail="nao encontrado",
            forbidden_detail="nao autorizado",
        )
    
        assert result is fornecedor

    def test_ensure_current_user_identified_raises_400():
        service, _, _ = _build_service(fornecedor=None)
    
        with pytest.raises(HTTPException) as exc:
            service.ensure_current_user_identified(current_user=SimpleNamespace(id=None))
    
        assert exc.value.status_code == 400

    def test_create_fornecedor_records_historico():
        service, fornecedor_repo, historico_repo = _build_service(fornecedor=None)
    
        created = service.create_fornecedor(
            fornecedor=SimpleNamespace(id=9, nome="Novo Fornecedor"),
            current_user=SimpleNamespace(id=10, is_superuser=False),
        )
    
        assert created.nome == "Novo Fornecedor"
        assert len(fornecedor_repo.created_calls) == 1
        payload = historico_repo.calls[0].data
        assert payload["acao"] == "CRIACAO"

    def test_list_fornecedores_page_for_regular_user():
        service, fornecedor_repo, _ = _build_service(fornecedor=None)
        fornecedor_repo.list_items = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        fornecedor_repo.list_total = 2
    
        payload = service.list_fornecedores_page(
            current_user=SimpleNamespace(id=10, is_superuser=False),
            skip=0,
            limit=10,
            termo_busca="forn",
        )
    
        assert payload["total_items"] == 2
        assert len(payload["items"]) == 2
        assert payload["page"] == 1
        assert payload["limit"] == 10

    def test_resolve_fornecedor_for_user_raises_404():
        service, _, _ = _build_service(fornecedor=None)
    
        with pytest.raises(HTTPException) as exc:
            service.resolve_fornecedor_for_user(
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
                fornecedor_id=5,
                current_user=SimpleNamespace(id=10, is_superuser=False),
                not_found_detail="nao encontrado",
                forbidden_detail="nao autorizado",
            )
    
        assert exc.value.status_code == 403

    def test_update_fornecedor_records_historico():
        fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
        service, fornecedor_repo, historico_repo = _build_service(fornecedor=fornecedor)
    
        updated = service.update_fornecedor(
            fornecedor_id=5,
            fornecedor_update=SimpleNamespace(nome="Fornecedor B"),
            current_user=SimpleNamespace(id=10, is_superuser=False),
        )
    
        assert updated.nome == "Fornecedor B"
        assert len(fornecedor_repo.updated_calls) == 1
        assert len(historico_repo.calls) == 1
        payload = historico_repo.calls[0].data
        assert payload["acao"] == "ATUALIZACAO"

    def test_update_fornecedor_raises_for_duplicate_name():
        fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
        service, fornecedor_repo, _ = _build_service(fornecedor=fornecedor)
        fornecedor_repo.has_duplicate_name = True
    
        with pytest.raises(HTTPException) as exc:
            service.update_fornecedor(
                fornecedor_id=5,
                fornecedor_update=SimpleNamespace(nome="Fornecedor B"),
                current_user=SimpleNamespace(id=10, is_superuser=False),
            )
    
        assert exc.value.status_code == 400

    def test_update_mapping_persists_and_returns_fornecedor():
        fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A", default_column_mapping=None)
        service, fornecedor_repo, _ = _build_service(fornecedor=fornecedor)
    
        updated = service.update_mapping(
            fornecedor_id=5,
            current_user=SimpleNamespace(id=10, is_superuser=False),
            mapping={"col_0": "nome_base"},
        )
    
        assert updated.default_column_mapping == {"col_0": "nome_base"}
        assert len(fornecedor_repo.mapping_updates) == 1

    def test_delete_fornecedor_records_historico():
        fornecedor = SimpleNamespace(id=5, user_id=10, nome="Fornecedor A")
        service, fornecedor_repo, historico_repo = _build_service(fornecedor=fornecedor)
    
        deleted = service.delete_fornecedor(
            fornecedor_id=5,
            current_user=SimpleNamespace(id=10, is_superuser=False),
        )
    
        assert deleted is fornecedor
        assert len(fornecedor_repo.deleted_calls) == 1
        payload = historico_repo.calls[0].data
        assert payload["acao"] == "DELECAO"

_build_service = _TopLevelFunctionSurface._build_service
test_resolve_fornecedor_for_user_success = _TopLevelFunctionSurface.test_resolve_fornecedor_for_user_success
test_ensure_current_user_identified_raises_400 = _TopLevelFunctionSurface.test_ensure_current_user_identified_raises_400
test_create_fornecedor_records_historico = _TopLevelFunctionSurface.test_create_fornecedor_records_historico
test_list_fornecedores_page_for_regular_user = _TopLevelFunctionSurface.test_list_fornecedores_page_for_regular_user
test_resolve_fornecedor_for_user_raises_404 = _TopLevelFunctionSurface.test_resolve_fornecedor_for_user_raises_404
test_resolve_fornecedor_for_user_raises_403 = _TopLevelFunctionSurface.test_resolve_fornecedor_for_user_raises_403
test_update_fornecedor_records_historico = _TopLevelFunctionSurface.test_update_fornecedor_records_historico
test_update_fornecedor_raises_for_duplicate_name = _TopLevelFunctionSurface.test_update_fornecedor_raises_for_duplicate_name
test_update_mapping_persists_and_returns_fornecedor = _TopLevelFunctionSurface.test_update_mapping_persists_and_returns_fornecedor
test_delete_fornecedor_records_historico = _TopLevelFunctionSurface.test_delete_fornecedor_records_historico




















