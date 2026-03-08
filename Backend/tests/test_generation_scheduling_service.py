"""Module test generation scheduling service.

Contains backend logic related to test generation scheduling service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)


class _CrudProdutosStub:
    """Represent crud produtos stub and centralize responsibilities for this module."""
    def __init__(self, produto=None):
        """Initialize collaborators and configuration required by this component."""
        self.produto = produto
        self.updated = []

    def get_produto(self, *, produto_id: int):
        """Return produto for this workflow."""
        _ = produto_id
        return self.produto

    def update_produto(self, *, db_produto, produto_update):
        """Update produto for this workflow."""
        self.updated.append((db_produto, produto_update))
        return db_produto


class _SchemasStub:
    """Represent schemas stub and centralize responsibilities for this module."""
    class ProdutoUpdate:
        """Represent produto update and centralize responsibilities for this module."""
        def __init__(self, **kwargs):
            """Initialize collaborators and configuration required by this component."""
            self.payload = kwargs


class _ModelsStub:
    """Represent models stub and centralize responsibilities for this module."""
    class StatusGeracaoIAEnum:
        """Represent status geracao i a enum and centralize responsibilities for this module."""
        PENDENTE = "PENDENTE"


class _BackgroundTasksStub:
    """Represent background tasks stub and centralize responsibilities for this module."""
    def __init__(self):
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    def add_task(self, task_executor, **kwargs):
        """Run add task in this workflow."""
        self.calls.append((task_executor, kwargs))


class _DispatcherStub:
    """Represent dispatcher stub and centralize responsibilities for this module."""

    def __init__(self, *, use_celery: bool):
        """Initialize collaborators and configuration required by this component."""
        self._use_celery = use_celery
        self.named_calls = []

    def uses_celery(self):
        """Return whether this stub is configured to emulate Celery."""
        return self._use_celery

    def dispatch_named_task(self, *, task_name, task_kwargs):
        """Capture Celery dispatch requests."""
        self.named_calls.append((task_name, task_kwargs))
        return "async-result"


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_service(produto=None, dispatcher_cls=None):
        """Run build service in this workflow."""
        crud_stub = _CrudProdutosStub(produto=produto)
        service = GenerationSchedulingService(
            schemas=_SchemasStub,
            models=_ModelsStub,
            product_repository=crud_stub,
            dispatcher_cls=dispatcher_cls or (lambda: _DispatcherStub(use_celery=False)),
        )
        return service, crud_stub

    def test_validate_product_access_not_found():
        """Run test validate product access not found in this workflow."""
        service, _ = _build_service(produto=None)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        with pytest.raises(HTTPException) as exc:
            service.validate_product_access(
                produto_id=10,
                current_user=user,
            )
    
        assert exc.value.status_code == 404

    def test_validate_product_access_forbidden():
        """Run test validate product access forbidden in this workflow."""
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
        """Run test validate product access success in this workflow."""
        produto = SimpleNamespace(user_id=1)
        service, _ = _build_service(produto=produto)
        user = SimpleNamespace(id=1, is_superuser=False)
    
        result = service.validate_product_access(
            produto_id=10,
            current_user=user,
        )
    
        assert result is produto

    def test_mark_pending_status_updates_expected_field():
        """Run test mark pending status updates expected field in this workflow."""
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
        """Run test enqueue generation task forwards expected kwargs in this workflow."""
        service, _ = _build_service(produto=SimpleNamespace(user_id=1))
        background_tasks = _BackgroundTasksStub()
    
        def _executor(**kwargs):
            """Run executor in this workflow."""
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

    def test_enqueue_generation_task_dispatches_celery_when_enabled():
        """Dispatch generation through Celery when the async backend is configured for it."""
        dispatcher = _DispatcherStub(use_celery=True)
        service, _ = _build_service(
            produto=SimpleNamespace(user_id=1),
            dispatcher_cls=lambda: dispatcher,
        )
        background_tasks = _BackgroundTasksStub()

        service.enqueue_generation_task(
            background_tasks=background_tasks,
            task_executor=lambda **kwargs: kwargs,
            user_id=7,
            produto_id=8,
            generation_type="titulo",
            generation_func=object(),
            generation_provider_key="openai_title",
            num_titulos=4,
        )

        assert background_tasks.calls == []
        assert dispatcher.named_calls == [
            (
                "generation.run",
                {
                    "user_id": 7,
                    "produto_id": 8,
                    "tipo_geracao_principal": "titulo",
                    "generation_provider_key": "openai_title",
                    "num_titulos": 4,
                    "tamanho_palavras": None,
                },
            )
        ]

    def test_enqueue_generation_task_dispatches_celery_with_templates():
        """Include optional templates in the serializable Celery payload when provided."""
        dispatcher = _DispatcherStub(use_celery=True)
        service, _ = _build_service(
            produto=SimpleNamespace(user_id=1),
            dispatcher_cls=lambda: dispatcher,
        )

        service.enqueue_generation_task(
            background_tasks=_BackgroundTasksStub(),
            task_executor=lambda **kwargs: kwargs,
            user_id=7,
            produto_id=8,
            generation_type="descricao",
            generation_func=object(),
            generation_provider_key="basic_description",
            tamanho_palavras=120,
            template_titulo="titulo livre",
            template_descricao="descricao livre",
        )

        assert dispatcher.named_calls == [
            (
                "generation.run",
                {
                    "user_id": 7,
                    "produto_id": 8,
                    "tipo_geracao_principal": "descricao",
                    "generation_provider_key": "basic_description",
                    "num_titulos": None,
                    "tamanho_palavras": 120,
                    "template_titulo": "titulo livre",
                    "template_descricao": "descricao livre",
                },
            )
        ]

_build_service = _TopLevelFunctionSurface._build_service
test_validate_product_access_not_found = _TopLevelFunctionSurface.test_validate_product_access_not_found
test_validate_product_access_forbidden = _TopLevelFunctionSurface.test_validate_product_access_forbidden
test_validate_product_access_success = _TopLevelFunctionSurface.test_validate_product_access_success
test_mark_pending_status_updates_expected_field = _TopLevelFunctionSurface.test_mark_pending_status_updates_expected_field
test_enqueue_generation_task_forwards_expected_kwargs = _TopLevelFunctionSurface.test_enqueue_generation_task_forwards_expected_kwargs
test_enqueue_generation_task_dispatches_celery_when_enabled = _TopLevelFunctionSurface.test_enqueue_generation_task_dispatches_celery_when_enabled
test_enqueue_generation_task_dispatches_celery_with_templates = _TopLevelFunctionSurface.test_enqueue_generation_task_dispatches_celery_with_templates










