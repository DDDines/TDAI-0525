"""Module test product management service.

Contains backend logic related to test product management service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_management_service import (
    ProductManagementService,
)


class _CrudProdutosStub:
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self, *, produto=None):
        """Initialize collaborators and configuration required by this component."""
        self.produto = produto
        self.created = []
        self.updated = []
        self.deleted = []
        self.list_items = []
        self.total_items = 0

    def create_produto(self, *, produto, user_id):
        """Create produto for this workflow."""
        created = SimpleNamespace(
            id=produto.id,
            user_id=user_id,
            fornecedor_id=getattr(produto, "fornecedor_id", None),
            product_type_id=getattr(produto, "product_type_id", None),
            nome_base=getattr(produto, "nome_base", None),
        )
        self.created.append((produto, user_id))
        return created

    def get_produto(self, *, produto_id):
        """Return produto for this workflow."""
        _ = produto_id
        return self.produto

    def get_produtos_by_user(self, **kwargs):
        """Return produtos by user for this workflow."""
        _ = kwargs
        return self.list_items

    def count_produtos_by_user(self, **kwargs):
        """Count produtos by user for this workflow."""
        _ = kwargs
        return self.total_items

    def update_produto(self, *, db_produto, produto_update):
        """Update produto for this workflow."""
        self.updated.append((db_produto, produto_update))
        if getattr(produto_update, "nome_base", None):
            db_produto.nome_base = produto_update.nome_base
        return db_produto

    def delete_produto(self, *, db_produto):
        """Delete produto for this workflow."""
        self.deleted.append(db_produto)
        return db_produto


class _CrudFornecedoresStub:
    """Represent crud fornecedores stub and centralize responsibilities for this module."""
    def __init__(self, *, fornecedor=True):
        """Initialize collaborators and configuration required by this component."""
        self.fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id):
        """Return fornecedor for this workflow."""
        _ = fornecedor_id
        return self.fornecedor


class _CrudProductTypesStub:
    """Represent crud product types stub and centralize responsibilities for this module."""
    def __init__(self, *, product_type=True):
        """Initialize collaborators and configuration required by this component."""
        self.product_type = product_type

    def get_product_type(self, *, product_type_id):
        """Return product type for this workflow."""
        _ = product_type_id
        return self.product_type


class _CrudHistoricoStub:
    """Represent crud historico stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def create_registro_historico(self, payload):
        """Create registro historico for this workflow."""
        self.calls.append(payload.data)


class _CrudUsoIAStub:
    """Represent crud uso i a stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def create_registro_uso_ia(self, payload):
        """Create registro uso ia for this workflow."""
        self.calls.append(payload.data)


class _SchemaPayload:
    """Represent schema payload and centralize responsibilities for this module."""
    def __init__(self, **kwargs):
        """Initialize collaborators and configuration required by this component."""
        self.data = kwargs


class _SchemasStub:
    """Represent schemas stub and centralize responsibilities for this module."""
    RegistroUsoIACreate = _SchemaPayload
    RegistroHistoricoCreate = _SchemaPayload


class _TipoAcaoEnumStub:
    """Represent tipo acao enum stub and centralize responsibilities for this module."""
    CRIACAO_PRODUTO = "CRIACAO_PRODUTO"


class _TipoAcaoSistemaEnumStub:
    """Represent tipo acao sistema enum stub and centralize responsibilities for this module."""
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    TipoAcaoEnum = _TipoAcaoEnumStub
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(
        *,
        produto=None,
        fornecedor=True,
        product_type=True,
    ):
        """Run build service in this workflow."""
        crud_produtos = _CrudProdutosStub(produto=produto)
        crud_historico = _CrudHistoricoStub()
        crud_uso_ia = _CrudUsoIAStub()
        service = ProductManagementService(
            models=_ModelsStub,
            schemas=_SchemasStub,
            produto_repo=crud_produtos,
            fornecedor_repo=_CrudFornecedoresStub(fornecedor=fornecedor),
            product_type_repo=_CrudProductTypesStub(product_type=product_type),
            historico_repo=crud_historico,
            uso_ia_repo=crud_uso_ia,
        )
        return service, crud_produtos, crud_historico, crud_uso_ia

    def test_create_produto_records_historico_and_ia_usage():
        """Run test create produto records historico and ia usage in this workflow."""
        service, crud_produtos, crud_historico, crud_uso_ia = _build_service()
    
        created = service.create_produto(
            produto=SimpleNamespace(id=10, fornecedor_id=1, product_type_id=2, nome_base="Peca"),
            current_user=SimpleNamespace(id=3, is_superuser=False),
        )
    
        assert created.id == 10
        assert len(crud_produtos.created) == 1
        assert crud_uso_ia.calls[0]["tipo_acao"] == "CRIACAO_PRODUTO"
        assert crud_historico.calls[0]["acao"] == "CRIACAO"

    def test_create_produto_raises_when_fornecedor_missing():
        """Run test create produto raises when fornecedor missing in this workflow."""
        service, _, _, _ = _build_service(fornecedor=False)
    
        with pytest.raises(HTTPException) as exc:
            service.create_produto(
                produto=SimpleNamespace(id=10, fornecedor_id=1, product_type_id=None),
                current_user=SimpleNamespace(id=3, is_superuser=False),
            )
    
        assert exc.value.status_code == 404

    def test_read_produto_raises_403_for_non_owner():
        """Run test read produto raises 403 for non owner in this workflow."""
        produto = SimpleNamespace(id=10, user_id=9)
        service, _, _, _ = _build_service(produto=produto)
    
        with pytest.raises(HTTPException) as exc:
            service.read_produto(
                produto_id=10,
                current_user=SimpleNamespace(id=3, is_superuser=False),
            )
    
        assert exc.value.status_code == 403

    def test_list_produtos_builds_page_payload():
        """Run test list produtos builds page payload in this workflow."""
        service, crud_produtos, _, _ = _build_service()
        crud_produtos.list_items = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
        crud_produtos.total_items = 2
    
        payload = service.list_produtos(
            skip=0,
            limit=10,
            sort_by="id",
            sort_order="desc",
            search=None,
            fornecedor_id=None,
            categoria=None,
            status_enriquecimento_web=None,
            status_titulo_ia=None,
            status_descricao_ia=None,
            product_type_id=None,
            current_user=SimpleNamespace(id=3, is_superuser=False),
        )
    
        assert payload["total_items"] == 2
        assert len(payload["items"]) == 2
        assert payload["page"] == 1

    def test_update_produto_records_historico():
        """Run test update produto records historico in this workflow."""
        produto = SimpleNamespace(id=10, user_id=3, fornecedor_id=1, product_type_id=2, nome_base="Peca")
        service, crud_produtos, crud_historico, _ = _build_service(produto=produto)
    
        updated = service.update_produto(
            produto_id=10,
            produto_update=SimpleNamespace(
                fornecedor_id=1,
                product_type_id=2,
                nome_base="Peca Atualizada",
            ),
            current_user=SimpleNamespace(id=3, is_superuser=False),
        )
    
        assert updated.nome_base == "Peca Atualizada"
        assert len(crud_produtos.updated) == 1
        assert crud_historico.calls[0]["acao"] == "ATUALIZACAO"

    def test_delete_produto_records_historico():
        """Run test delete produto records historico in this workflow."""
        produto = SimpleNamespace(id=10, user_id=3)
        service, crud_produtos, crud_historico, _ = _build_service(produto=produto)
    
        deleted = service.delete_produto(
            produto_id=10,
            current_user=SimpleNamespace(id=3, is_superuser=False),
        )
    
        assert deleted is produto
        assert len(crud_produtos.deleted) == 1
        assert crud_historico.calls[0]["acao"] == "DELECAO"

    def test_batch_delete_produtos_raises_when_all_missing():
        """Run test batch delete produtos raises when all missing in this workflow."""
        service, _, _, _ = _build_service(produto=None)
    
        with pytest.raises(HTTPException) as exc:
            service.batch_delete_produtos(
                produto_ids=[1, 2],
                current_user=SimpleNamespace(id=3, is_superuser=False),
            )
    
        assert exc.value.status_code == 400

_build_service = _TopLevelFunctionSurface._build_service
test_create_produto_records_historico_and_ia_usage = _TopLevelFunctionSurface.test_create_produto_records_historico_and_ia_usage
test_create_produto_raises_when_fornecedor_missing = _TopLevelFunctionSurface.test_create_produto_raises_when_fornecedor_missing
test_read_produto_raises_403_for_non_owner = _TopLevelFunctionSurface.test_read_produto_raises_403_for_non_owner
test_list_produtos_builds_page_payload = _TopLevelFunctionSurface.test_list_produtos_builds_page_payload
test_update_produto_records_historico = _TopLevelFunctionSurface.test_update_produto_records_historico
test_delete_produto_records_historico = _TopLevelFunctionSurface.test_delete_produto_records_historico
test_batch_delete_produtos_raises_when_all_missing = _TopLevelFunctionSurface.test_batch_delete_produtos_raises_when_all_missing














