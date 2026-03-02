"""Module test product management service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_management_service import (
    ProductManagementService,
)


class _CrudProdutosStub:
    """Class _CrudProdutosStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, produto=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.produto = produto
        self.created = []
        self.updated = []
        self.deleted = []
        self.list_items = []
        self.total_items = 0

    def create_produto(self, *, produto, user_id):
        """Execute create_produto.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute get_produto.

        This callable is documented to make behavior explicit for readers.
        """
        _ = produto_id
        return self.produto

    def get_produtos_by_user(self, **kwargs):
        """Execute get_produtos_by_user.

        This callable is documented to make behavior explicit for readers.
        """
        _ = kwargs
        return self.list_items

    def count_produtos_by_user(self, **kwargs):
        """Execute count_produtos_by_user.

        This callable is documented to make behavior explicit for readers.
        """
        _ = kwargs
        return self.total_items

    def update_produto(self, *, db_produto, produto_update):
        """Execute update_produto.

        This callable is documented to make behavior explicit for readers.
        """
        self.updated.append((db_produto, produto_update))
        if getattr(produto_update, "nome_base", None):
            db_produto.nome_base = produto_update.nome_base
        return db_produto

    def delete_produto(self, *, db_produto):
        """Execute delete_produto.

        This callable is documented to make behavior explicit for readers.
        """
        self.deleted.append(db_produto)
        return db_produto


class _CrudFornecedoresStub:
    """Class _CrudFornecedoresStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, fornecedor=True):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.fornecedor = fornecedor

    def get_fornecedor(self, *, fornecedor_id):
        """Execute get_fornecedor.

        This callable is documented to make behavior explicit for readers.
        """
        _ = fornecedor_id
        return self.fornecedor


class _CrudProductTypesStub:
    """Class _CrudProductTypesStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, product_type=True):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.product_type = product_type

    def get_product_type(self, *, product_type_id):
        """Execute get_product_type.

        This callable is documented to make behavior explicit for readers.
        """
        _ = product_type_id
        return self.product_type


class _CrudHistoricoStub:
    """Class _CrudHistoricoStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def create_registro_historico(self, payload):
        """Execute create_registro_historico.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(payload.data)


class _CrudUsoIAStub:
    """Class _CrudUsoIAStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def create_registro_uso_ia(self, payload):
        """Execute create_registro_uso_ia.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append(payload.data)


class _SchemaPayload:
    """Class _SchemaPayload.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, **kwargs):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.data = kwargs


class _SchemasStub:
    """Class _SchemasStub.

    Encapsulates one responsibility in the backend architecture.
    """
    RegistroUsoIACreate = _SchemaPayload
    RegistroHistoricoCreate = _SchemaPayload


class _TipoAcaoEnumStub:
    """Class _TipoAcaoEnumStub.

    Encapsulates one responsibility in the backend architecture.
    """
    CRIACAO_PRODUTO = "CRIACAO_PRODUTO"


class _TipoAcaoSistemaEnumStub:
    """Class _TipoAcaoSistemaEnumStub.

    Encapsulates one responsibility in the backend architecture.
    """
    CRIACAO = "CRIACAO"
    ATUALIZACAO = "ATUALIZACAO"
    DELECAO = "DELECAO"


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    TipoAcaoEnum = _TipoAcaoEnumStub
    TipoAcaoSistemaEnum = _TipoAcaoSistemaEnumStub


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(
        *,
        produto=None,
        fornecedor=True,
        product_type=True,
    ):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_create_produto_records_historico_and_ia_usage.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_create_produto_raises_when_fornecedor_missing.

        This callable is documented to make behavior explicit for readers.
        """
        service, _, _, _ = _build_service(fornecedor=False)
    
        with pytest.raises(HTTPException) as exc:
            service.create_produto(
                produto=SimpleNamespace(id=10, fornecedor_id=1, product_type_id=None),
                current_user=SimpleNamespace(id=3, is_superuser=False),
            )
    
        assert exc.value.status_code == 404

    def test_read_produto_raises_403_for_non_owner():
        """Execute test_read_produto_raises_403_for_non_owner.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(id=10, user_id=9)
        service, _, _, _ = _build_service(produto=produto)
    
        with pytest.raises(HTTPException) as exc:
            service.read_produto(
                produto_id=10,
                current_user=SimpleNamespace(id=3, is_superuser=False),
            )
    
        assert exc.value.status_code == 403

    def test_list_produtos_builds_page_payload():
        """Execute test_list_produtos_builds_page_payload.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_update_produto_records_historico.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_delete_produto_records_historico.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute test_batch_delete_produtos_raises_when_all_missing.

        This callable is documented to make behavior explicit for readers.
        """
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














