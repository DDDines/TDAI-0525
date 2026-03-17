"""Additional coverage for produtos router wrappers and coordinator paths."""

from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

from Backend import schemas
from Backend.routers import produtos as produtos_module


def test_produtos_catalog_service_builders_use_product_repositories(monkeypatch):
    captured = []

    class FakeManagementService:
        def __init__(self, **kwargs):
            captured.append(("management", kwargs))

    class FakeMediaService:
        def __init__(self, **kwargs):
            captured.append(("media", kwargs))

    monkeypatch.setattr(
        produtos_module.ProductRepositories,
        "build_product_management_repositories",
        staticmethod(lambda session: {"repo": ("management", session)}),
    )
    monkeypatch.setattr(
        produtos_module.ProductRepositories,
        "build_product_media_repositories",
        staticmethod(lambda session: {"repo": ("media", session)}),
    )
    monkeypatch.setattr(produtos_module, "ProductManagementService", FakeManagementService)
    monkeypatch.setattr(produtos_module, "ProductMediaService", FakeMediaService)

    service = object.__new__(produtos_module._ProdutosCatalogService)
    service._session = "db"

    service._build_product_management_service()
    service._build_product_media_service()

    assert captured[0][0] == "management"
    assert captured[0][1]["repo"] == ("management", "db")
    assert captured[1][0] == "media"
    assert captured[1][1]["repo"] == ("media", "db")


@pytest.mark.asyncio
async def test_produtos_catalog_service_delegates_product_and_catalog_methods():
    service = object.__new__(produtos_module._ProdutosCatalogService)
    user = SimpleNamespace(id=7)
    produto = schemas.ProdutoCreate(nome_base="Produto", sku="SKU")

    class FakeManagementService:
        def create_produto(self, **kwargs):
            return ("create", kwargs)

        def read_produto(self, **kwargs):
            return ("read", kwargs)

        def list_produtos(self, **kwargs):
            return ("list", kwargs)

        def update_produto(self, **kwargs):
            return ("update", kwargs)

        def delete_produto(self, **kwargs):
            return ("delete", kwargs)

        def batch_delete_produtos(self, **kwargs):
            return ("batch", kwargs)

    class FakeMediaService:
        async def upload_produto_image(self, **kwargs):
            return ("upload", kwargs)

    async def _finalizar_todas_paginas(**kwargs):
        return ("finalizar_todas", kwargs)

    service._build_product_management_service = lambda: FakeManagementService()
    service._build_product_media_service = lambda: FakeMediaService()
    service._catalog_import_workflow_service = SimpleNamespace(
        importar_catalogo_status_simple=lambda **kwargs: ("status_simple", kwargs),
        importar_catalogo_finalizar_todas_paginas=_finalizar_todas_paginas,
    )

    assert service.create_produto(produto=produto, current_user=user)[0] == "create"
    assert service.read_produto(produto_id=1, current_user=user)[0] == "read"
    assert service.list_produtos(
        skip=0,
        limit=10,
        sort_by=None,
        sort_order="asc",
        search=None,
        fornecedor_id=None,
        categoria=None,
        status_enriquecimento_web=None,
        status_titulo_ia=None,
        status_descricao_ia=None,
        product_type_id=None,
        enrichment_scope=None,
        current_user=user,
    )[0] == "list"
    assert service.update_produto(
        produto_id=1,
        produto_update=schemas.ProdutoUpdate(nome_base="Novo"),
        current_user=user,
    )[0] == "update"
    assert service.delete_produto(produto_id=1, current_user=user)[0] == "delete"
    assert service.batch_delete_produtos(produto_ids=[1, 2], current_user=user)[0] == "batch"
    assert (
        await service.upload_produto_image(
            produto_id=1,
            file="file",
            current_user=user,
        )
    )[0] == "upload"
    assert service.importar_catalogo_status_simple(file_id=9, user_id=7)[0] == "status_simple"
    assert (
        await service.importar_catalogo_finalizar_todas_paginas(
            file_id=9,
            start_page=2,
            mapping={"a": "b"},
            extraction_mode="ocr",
            user_id=7,
        )
    )[0] == "finalizar_todas"


@pytest.mark.asyncio
async def test_produtos_catalog_coordinator_handles_sync_async_and_preview_conversion():
    with pytest.raises(RuntimeError):
        produtos_module.ProdutosCatalogCoordinator()

    assert await produtos_module.ProdutosCatalogCoordinator._await_if_needed("valor") == "valor"

    class FakeRuntime:
        def read_produto(self, **kwargs):
            return ("read", kwargs)

        def update_produto(self, **kwargs):
            return ("update", kwargs)

        def delete_produto(self, **kwargs):
            return ("delete", kwargs)

        def batch_delete_produtos(self, **kwargs):
            return ("batch", kwargs)

        async def upload_produto_image(self, **kwargs):
            return ("upload", kwargs)

        async def importar_catalogo_preview(self, **kwargs):
            return {"file_id": 9}

        def importar_catalogo_status_simple(self, **kwargs):
            return ("status_simple", kwargs)

        async def importar_catalogo_finalizar_todas_paginas(self, **kwargs):
            return ("finalizar_todas", kwargs)

    coordinator = produtos_module.ProdutosCatalogCoordinator(runtime=FakeRuntime())
    user = SimpleNamespace(id=7)

    assert coordinator.read_produto(produto_id=1, current_user=user)[0] == "read"
    assert coordinator.update_produto(
        produto_id=1,
        produto_update=schemas.ProdutoUpdate(nome_base="Novo"),
        current_user=user,
    )[0] == "update"
    assert coordinator.delete_produto(produto_id=1, current_user=user)[0] == "delete"
    assert coordinator.batch_delete_produtos(produto_ids=[1], current_user=user)[0] == "batch"
    assert (
        await coordinator.upload_produto_image(produto_id=1, file="file", current_user=user)
    )[0] == "upload"
    preview = await coordinator.importar_catalogo_preview(
        file="file",
        fornecedor_id=None,
        start_page=1,
        page_count=1,
        dpi=72,
        user_id=7,
    )
    assert isinstance(preview, schemas.ImportPreviewResponse)
    assert preview.file_id == 9
    assert coordinator.importar_catalogo_status_simple(file_id=9, user_id=7)[0] == "status_simple"
    assert (
        await coordinator.importar_catalogo_finalizar_todas_paginas(
            file_id=9,
            start_page=2,
            mapping={"a": "b"},
            extraction_mode="ocr",
            user_id=7,
        )
    )[0] == "finalizar_todas"


@pytest.mark.asyncio
async def test_produtos_catalog_coordinator_returns_raw_preview_when_runtime_already_normalized():
    class FakeRuntime:
        async def importar_catalogo_preview(self, **kwargs):
            return ("raw-preview", kwargs["user_id"])

    coordinator = produtos_module.ProdutosCatalogCoordinator(runtime=FakeRuntime())
    assert await coordinator.importar_catalogo_preview(
        file="file",
        fornecedor_id=None,
        start_page=1,
        page_count=1,
        dpi=72,
        user_id=9,
    ) == ("raw-preview", 9)


def test_produtos_module_import_skips_catalog_logger_bootstrap_when_handler_exists():
    module_name = "Backend.routers._produtos_probe_runtime"
    sys.modules.pop(module_name, None)
    catalog_logger = logging.getLogger("catalogo")
    handler = logging.NullHandler()
    catalog_logger.addHandler(handler)
    handlers_before = list(catalog_logger.handlers)
    try:
        spec = importlib.util.spec_from_file_location(module_name, Path("Backend/routers/produtos.py"))
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        assert module.catalog_logger.handlers == handlers_before
    finally:
        catalog_logger.removeHandler(handler)
        sys.modules.pop(module_name, None)


@pytest.mark.asyncio
async def test_produtos_request_scope_and_endpoint_handlers_delegate():
    called = []
    user = SimpleNamespace(id=7)

    class FakeWorkflow:
        def importar_catalogo_status_simple(self, **kwargs):
            called.append(("status_simple", kwargs))
            return {"status": "ok"}

        async def importar_catalogo_finalizar_todas_paginas(self, **kwargs):
            called.append(("finalizar_todas", kwargs))
            return {"ready": True}

    scope = produtos_module._ProdutosCatalogRequestScope(
        session="db",
        workflow=FakeWorkflow(),
    )
    assert scope.importar_catalogo_status_simple(file_id=9, user_id=7) == {"status": "ok"}
    assert (
        await scope.importar_catalogo_finalizar_todas_paginas(
            file_id=9,
            start_page=2,
            mapping={"a": "b"},
            extraction_mode="ocr",
            user_id=7,
        )
    ) == {"ready": True}

    class FakeProductManagementService:
        def read_produto(self, **kwargs):
            called.append(("read_produto", kwargs))
            return {"produto_id": kwargs["produto_id"]}

        def batch_delete_produtos(self, **kwargs):
            called.append(("batch_delete", kwargs))
            return [{"id": 1}]

    class FakeProductMediaService:
        async def upload_produto_image(self, **kwargs):
            called.append(("upload_image", kwargs))
            return {"uploaded": True}

    request_context = SimpleNamespace(catalog_workflow=scope)
    request_services = SimpleNamespace(
        product_management_service=FakeProductManagementService(),
        product_media_service=FakeProductMediaService(),
    )

    assert produtos_module._EndpointHandlers.read_produto(
        produto_id=1,
        current_user=user,
        request_services=request_services,
    ) == {"produto_id": 1}
    assert produtos_module._EndpointHandlers.batch_delete_produtos(
        produto_ids=[1],
        current_user=user,
        request_services=request_services,
    ) == [{"id": 1}]
    assert (
        await produtos_module._EndpointHandlers.upload_produto_image(
            produto_id=1,
            file="file",
            current_user=user,
            request_services=request_services,
        )
    ) == {"uploaded": True}
    assert produtos_module._EndpointHandlers.importar_catalogo_status_simple(
        file_id=9,
        current_user=user,
        request_context=request_context,
    ) == {"status": "ok"}
    assert (
        await produtos_module._EndpointHandlers.importar_catalogo_finalizar_todas_paginas(
            file_id=9,
            start_page=2,
            mapping={"a": "b"},
            extraction_mode="ocr",
            current_user=user,
            request_context=request_context,
        )
    ) == {"ready": True}

    assert called[0][0] == "status_simple"
    assert called[2][0] == "read_produto"
