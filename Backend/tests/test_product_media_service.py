from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.product_media_service import ProductMediaService


class _CrudProdutosStub:
    def __init__(self, *, produto=None, save_error=None):
        self.produto = produto
        self.save_error = save_error
        self.update_calls = []

    def get_produto(self, db, produto_id):
        _ = (db, produto_id)
        return self.produto

    async def save_produto_image(self, db, produto_id, file):
        _ = (db, produto_id, file)
        if self.save_error:
            raise self.save_error
        return "uploads/produto.jpg"

    def update_produto(self, *, db, db_produto, produto_update):
        _ = db
        self.update_calls.append((db_produto, produto_update))
        db_produto.imagem_principal_url = produto_update.imagem_principal_url
        return db_produto


class _ProdutoUpdateSchema:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class _SchemasStub:
    ProdutoUpdate = _ProdutoUpdateSchema


def _build_service(*, produto=None, save_error=None):
    crud_produtos = _CrudProdutosStub(produto=produto, save_error=save_error)
    service = ProductMediaService(
        crud_produtos=crud_produtos,
        schemas=_SchemasStub,
    )
    return service, crud_produtos


def test_upload_produto_image_raises_404_when_missing():
    service, _ = _build_service(produto=None)

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.upload_produto_image(
                db=object(),
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=1, is_superuser=False),
            )
        )

    assert exc.value.status_code == 404


def test_upload_produto_image_raises_403_when_not_owner():
    service, _ = _build_service(produto=SimpleNamespace(id=1, user_id=99))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.upload_produto_image(
                db=object(),
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=1, is_superuser=False),
            )
        )

    assert exc.value.status_code == 403


def test_upload_produto_image_raises_400_for_validation_error():
    service, _ = _build_service(
        produto=SimpleNamespace(id=1, user_id=1),
        save_error=ValueError("arquivo invalido"),
    )

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            service.upload_produto_image(
                db=object(),
                produto_id=1,
                file=object(),
                current_user=SimpleNamespace(id=1, is_superuser=False),
            )
        )

    assert exc.value.status_code == 400


def test_upload_produto_image_updates_product_url():
    produto = SimpleNamespace(id=1, user_id=1, imagem_principal_url=None)
    service, crud_produtos = _build_service(produto=produto)

    updated = asyncio.run(
        service.upload_produto_image(
            db=object(),
            produto_id=1,
            file=object(),
            current_user=SimpleNamespace(id=1, is_superuser=False),
        )
    )

    assert updated.imagem_principal_url == "uploads/produto.jpg"
    assert len(crud_produtos.update_calls) == 1
