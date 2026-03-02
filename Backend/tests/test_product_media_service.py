"""Module test product media service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_media_service import ProductMediaService


class _CrudProdutosStub:
    """Class _CrudProdutosStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, produto=None, save_error=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.produto = produto
        self.save_error = save_error
        self.update_calls = []

    def get_produto(self, *, produto_id):
        """Execute get_produto.

        This callable is documented to make behavior explicit for readers.
        """
        _ = produto_id
        return self.produto

    async def save_produto_image(self, *, produto_id, file):
        """Execute save_produto_image.

        This callable is documented to make behavior explicit for readers.
        """
        _ = (produto_id, file)
        if self.save_error:
            raise self.save_error
        return "uploads/produto.jpg"

    def update_produto(self, *, db_produto, produto_update):
        """Execute update_produto.

        This callable is documented to make behavior explicit for readers.
        """
        self.update_calls.append((db_produto, produto_update))
        db_produto.imagem_principal_url = produto_update.imagem_principal_url
        return db_produto


class _ProdutoUpdateSchema:
    """Class _ProdutoUpdateSchema.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, **kwargs):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    """Class _SchemasStub.

    Encapsulates one responsibility in the backend architecture.
    """
    ProdutoUpdate = _ProdutoUpdateSchema


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(*, produto=None, save_error=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        crud_produtos = _CrudProdutosStub(produto=produto, save_error=save_error)
        service = ProductMediaService(
            produto_repo=crud_produtos,
            schemas=_SchemasStub,
        )
        return service, crud_produtos

    def test_upload_produto_image_raises_404_when_missing():
        """Execute test_upload_produto_image_raises_404_when_missing.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service(produto=None)
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.upload_produto_image(
                    produto_id=1,
                    file=object(),
                    current_user=SimpleNamespace(id=1, is_superuser=False),
                )
            )
    
        assert exc.value.status_code == 404

    def test_upload_produto_image_raises_403_when_not_owner():
        """Execute test_upload_produto_image_raises_403_when_not_owner.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service(produto=SimpleNamespace(id=1, user_id=99))
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.upload_produto_image(
                    produto_id=1,
                    file=object(),
                    current_user=SimpleNamespace(id=1, is_superuser=False),
                )
            )
    
        assert exc.value.status_code == 403

    def test_upload_produto_image_raises_400_for_validation_error():
        """Execute test_upload_produto_image_raises_400_for_validation_error.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service(
            produto=SimpleNamespace(id=1, user_id=1),
            save_error=ValueError("arquivo invalido"),
        )
    
        with pytest.raises(HTTPException) as exc:
            asyncio.run(
                service.upload_produto_image(
                    produto_id=1,
                    file=object(),
                    current_user=SimpleNamespace(id=1, is_superuser=False),
                )
            )
    
        assert exc.value.status_code == 400

    def test_upload_produto_image_updates_product_url():
        """Execute test_upload_produto_image_updates_product_url.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(id=1, user_id=1, imagem_principal_url=None)
        service, crud_produtos = _build_service(produto=produto)
    
        updated = asyncio.run(
            service.upload_produto_image(
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=1, is_superuser=False),
            )
        )
    
        assert updated.imagem_principal_url == "uploads/produto.jpg"
        assert len(crud_produtos.update_calls) == 1

_build_service = _TopLevelFunctionSurface._build_service
test_upload_produto_image_raises_404_when_missing = _TopLevelFunctionSurface.test_upload_produto_image_raises_404_when_missing
test_upload_produto_image_raises_403_when_not_owner = _TopLevelFunctionSurface.test_upload_produto_image_raises_403_when_not_owner
test_upload_produto_image_raises_400_for_validation_error = _TopLevelFunctionSurface.test_upload_produto_image_raises_400_for_validation_error
test_upload_produto_image_updates_product_url = _TopLevelFunctionSurface.test_upload_produto_image_updates_product_url








