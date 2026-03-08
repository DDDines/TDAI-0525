"""Additional detail tests for product media service."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_media_service import ProductMediaService


class _CrudProdutosStub:
    """Small repo stub for media upload tests."""

    def __init__(self, *, produto=None, save_error=None):
        self.produto = produto
        self.save_error = save_error

    def get_produto(self, *, produto_id):
        _ = produto_id
        return self.produto

    async def save_produto_image(self, *, produto_id, file):
        _ = produto_id, file
        if self.save_error:
            raise self.save_error
        return "uploads/produto.jpg"

    def update_produto(self, *, db_produto, produto_update):
        db_produto.imagem_principal_url = produto_update.imagem_principal_url
        return db_produto


class _ProdutoUpdateSchema:
    """Simple schema stub mirroring the constructor used by the service."""

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    """Schema container stub."""

    ProdutoUpdate = _ProdutoUpdateSchema


def _build_service(*, produto=None, save_error=None):
    """Build media service and underlying repo stub."""
    repo = _CrudProdutosStub(produto=produto, save_error=save_error)
    return ProductMediaService(produto_repo=repo, schemas=_SchemasStub)


def test_upload_produto_image_raises_500_for_io_error():
    """Cover the explicit IO error handling branch."""
    service = _build_service(
        produto=SimpleNamespace(id=1, user_id=10),
        save_error=IOError("disk full"),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.upload_produto_image(
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=99, is_superuser=True),
            )
        )
    assert exc.value.status_code == 500
    assert "armazenamento" in exc.value.detail.lower()


def test_upload_produto_image_raises_500_for_unexpected_error():
    """Cover the generic unexpected-error branch."""
    service = _build_service(
        produto=SimpleNamespace(id=1, user_id=10),
        save_error=RuntimeError("boom"),
    )
    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.upload_produto_image(
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=99, is_superuser=True),
            )
        )
    assert exc.value.status_code == 500
    assert "nao foi possivel salvar" in exc.value.detail.lower()
