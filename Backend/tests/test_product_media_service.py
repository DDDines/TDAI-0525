"""Module test product media service.

Contains backend logic related to test product media service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_media_service import ProductMediaService


class _CrudProdutosStub:
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self, *, produto=None, save_error=None):
        """Initialize collaborators and configuration required by this component."""
        self.produto = produto
        self.save_error = save_error
        self.update_calls = []

    def get_produto(self, *, produto_id):
        """Return produto for this workflow."""
        _ = produto_id
        return self.produto

    async def save_produto_image(self, *, produto_id, file):
        """Run save produto image in this workflow."""
        _ = (produto_id, file)
        if self.save_error:
            raise self.save_error
        return "uploads/produto.jpg"

    def update_produto(self, *, db_produto, produto_update):
        """Update produto for this workflow."""
        self.update_calls.append((db_produto, produto_update))
        db_produto.imagem_principal_url = produto_update.imagem_principal_url
        return db_produto


class _ProdutoUpdateSchema:
    """Represent produto update schema and centralize responsibilities for this module."""
    def __init__(self, **kwargs):
        """Initialize collaborators and configuration required by this component."""
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    """Represent schemas stub and centralize responsibilities for this module."""
    ProdutoUpdate = _ProdutoUpdateSchema


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(*, produto=None, save_error=None):
        """Run build service in this workflow."""
        crud_produtos = _CrudProdutosStub(produto=produto, save_error=save_error)
        service = ProductMediaService(
            produto_repo=crud_produtos,
            schemas=_SchemasStub,
        )
        return service, crud_produtos

    def test_upload_produto_image_raises_404_when_missing():
        """Run test upload produto image raises 404 when missing in this workflow."""
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
        """Run test upload produto image raises 403 when not owner in this workflow."""
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
        """Run test upload produto image raises 400 for validation error in this workflow."""
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
        """Run test upload produto image updates product url in this workflow."""
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








