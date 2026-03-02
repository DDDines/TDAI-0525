"""Module test fornecedor management service.

Contains backend logic related to test fornecedor management service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)


class _FornecedorRepoStub:
    """Represent fornecedor repo stub and centralize responsibilities for this module."""
    def __init__(self, fornecedor=None):
        """Initialize collaborators and configuration required by this component."""
        self._fornecedor = fornecedor
        self.created_calls = []
        self.updated_calls = []
        self.deleted_calls = []
        self.list_items = []
        self.list_total = 0
        self.has_duplicate_name = False
        self.mapping_updates = []

    def get_fornecedor(self, *, fornecedor_id):
        """Return fornecedor for this workflow."""
        _ = fornecedor_id
        return self._fornecedor

    def create_fornecedor(self, *, fornecedor, user_id):
        """Create fornecedor for this workflow."""
        created = SimpleNamespace(id=fornecedor.id, nome=fornecedor.nome, user_id=user_id)
        self.created_calls.append((fornecedor, user_id))
        return created

    def get_fornecedores_by_user(self, *, user_id, is_admin, skip, limit, search):
        """Return fornecedores by user for this workflow."""
        _ = (user_id, is_admin, skip, limit, search)
        return self.list_items

    def count_fornecedores_by_user(self, *, user_id, is_admin, search):
        """Count fornecedores by user for this workflow."""
        _ = (user_id, is_admin, search)
        return self.list_total

    def exists_fornecedor_with_name_for_user(self, *, user_id, nome, exclude_id):
        """Run exists fornecedor with name for user in this workflow."""
        _ = (user_id, nome, exclude_id)
        return self.has_duplicate_name

    def update_fornecedor(self, *, db_fornecedor, fornecedor_update):
        """Update fornecedor for this workflow."""
        self.updated_calls.append((db_fornecedor, fornecedor_update))
        if fornecedor_update.nome:
            db_fornecedor.nome = fornecedor_update.nome
        return db_fornecedor

    def set_default_column_mapping(self, *, db_fornecedor, mapping):
        """Run set default column mapping in this workflow."""
        db_fornecedor.default_column_mapping = mapping
        self.mapping_updates.append((db_fornecedor, mapping))
        return db_fornecedor

    def delete_fornecedor(self, *, db_fornecedor):
        """Delete fornecedor for this workflow."""
        self.deleted_calls.append(db_fornecedor)
        return db_fornecedor


class _HistoricoRepoStub:
    """Represent historico repo stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def create_registro_historico(self, payload):
        """Create registro historico for this workflow."""
        self.calls.append(payload)


class _RegistroHistoricoCreateStub:
    """Represent registro historico create stub and centralize responsibilities for this module."""
    def __init__(self, **kwargs):
        """Initialize collaborators and configuration required by this component."""
        self.data = kwargs


class _TipoAcaoSistemaEnumStub:
    """Represent tipo acao sistema enum stub and centralize responsibilities for this module."""
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _SchemasStub:
    """Represent schemas stub and centralize responsibilities for this module."""
    RegistroHistoricoCreate = _RegistroHistoricoCreateStub


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, fornecedor):
        """Run build service in this workflow."""
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
        """Run test resolve fornecedor for user success in this workflow."""
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
        """Run test ensure current user identified raises 400 in this workflow."""
        service, _, _ = _build_service(fornecedor=None)
    
        with pytest.raises(HTTPException) as exc:
            service.ensure_current_user_identified(current_user=SimpleNamespace(id=None))
    
        assert exc.value.status_code == 400

    def test_create_fornecedor_records_historico():
        """Run test create fornecedor records historico in this workflow."""
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
        """Run test list fornecedores page for regular user in this workflow."""
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
        """Run test resolve fornecedor for user raises 404 in this workflow."""
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
        """Run test resolve fornecedor for user raises 403 in this workflow."""
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
        """Run test update fornecedor records historico in this workflow."""
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
        """Run test update fornecedor raises for duplicate name in this workflow."""
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
        """Run test update mapping persists and returns fornecedor in this workflow."""
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
        """Run test delete fornecedor records historico in this workflow."""
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




















