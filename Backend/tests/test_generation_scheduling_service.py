"""Module test generation scheduling service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)


class _CrudProdutosStub:
    """Class _CrudProdutosStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, produto=None):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.produto = produto
        self.updated = []

    def get_produto(self, *, produto_id: int):
        """Execute get_produto.

        This callable is documented to make behavior explicit for readers.
        """
        _ = produto_id
        return self.produto

    def update_produto(self, *, db_produto, produto_update):
        """Execute update_produto.

        This callable is documented to make behavior explicit for readers.
        """
        self.updated.append((db_produto, produto_update))
        return db_produto


class _SchemasStub:
    """Class _SchemasStub.

    Encapsulates one responsibility in the backend architecture.
    """
    class ProdutoUpdate:
        """Class ProdutoUpdate.

        Encapsulates one responsibility in the backend architecture.
        """
        def __init__(self, **kwargs):
            """Execute __init__.

            This callable is documented to make behavior explicit for readers.
            """
            self.payload = kwargs


class _ModelsStub:
    """Class _ModelsStub.

    Encapsulates one responsibility in the backend architecture.
    """
    class StatusGeracaoIAEnum:
        """Class StatusGeracaoIAEnum.

        Encapsulates one responsibility in the backend architecture.
        """
        PENDENTE = "PENDENTE"


class _BackgroundTasksStub:
    """Class _BackgroundTasksStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self):
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls = []

    def add_task(self, task_executor, **kwargs):
        """Execute add_task.

        This callable is documented to make behavior explicit for readers.
        """
        self.calls.append((task_executor, kwargs))


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def _build_service(produto=None):
        """Execute _build_service.

        This callable is documented to make behavior explicit for readers.
        """
        crud_stub = _CrudProdutosStub(produto=produto)
        service = GenerationSchedulingService(
            schemas=_SchemasStub,
            models=_ModelsStub,
            product_repository=crud_stub,
        )
        return service, crud_stub

    def test_validate_product_access_not_found():
        """Execute test_validate_product_access_not_found.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service(produto=None)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_product_access(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 404

    def test_validate_product_access_forbidden():
        """Execute test_validate_product_access_forbidden.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=2)
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_product_access(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 403

    def test_validate_product_access_success():
        """Execute test_validate_product_access_success.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=1)
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        result = service.validate_product_access(
            produto_id=10,
            current_user=user,
        )
    
        assert result is produto

    def test_mark_pending_status_updates_expected_field():
        """Execute test_mark_pending_status_updates_expected_field.

        This callable is documented to make behavior explicit for readers.
        """
        produto = SimpleNamespace(user_id=1)
        service, crud_stub = _build_service(produto=produto)
    
        service.mark_pending_status(
            db_produto=produto,
            generation_type="titulo",
        )
    
        assert len(crud_stub.updated) == 1
        _, produto_update = crud_stub.updated[0]
        assert produto_update.payload == {"status_titulo_ia": "PENDENTE"}

    def test_enqueue_generation_task_forwards_expected_kwargs():
        """Execute test_enqueue_generation_task_forwards_expected_kwargs.

        This callable is documented to make behavior explicit for readers.
        """
        service, _ = _build_service(produto=SimpleNamespace(user_id=1))
        background_tasks = _BackgroundTasksStub()
    
        def _executor(**kwargs):
            """Execute _executor.

            This callable is documented to make behavior explicit for readers.
            """
            return kwargs
    
        service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=_executor,
            user_id=7,
            produto_id=8,
            generation_type="descricao",
            generation_func=object(),
            tamanho_palavras=150,
        )
    
        assert len(background_tasks.calls) == 1
        _, kwargs = background_tasks.calls[0]
        assert kwargs["user_id"] == 7
        assert kwargs["produto_id"] == 8
        assert kwargs["tipo_geracao_principal"] == "descricao"
        assert kwargs["tamanho_palavras"] == 150

_build_service = _TopLevelFunctionSurface._build_service
test_validate_product_access_not_found = _TopLevelFunctionSurface.test_validate_product_access_not_found
test_validate_product_access_forbidden = _TopLevelFunctionSurface.test_validate_product_access_forbidden
test_validate_product_access_success = _TopLevelFunctionSurface.test_validate_product_access_success
test_mark_pending_status_updates_expected_field = _TopLevelFunctionSurface.test_mark_pending_status_updates_expected_field
test_enqueue_generation_task_forwards_expected_kwargs = _TopLevelFunctionSurface.test_enqueue_generation_task_forwards_expected_kwargs










