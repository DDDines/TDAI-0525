"""Additional detail tests for generation scheduling service."""

from __future__ import annotations

from types import SimpleNamespace

from Backend.application.services.generation_scheduling_service import (
    GenerationSchedulingService,
)


class _CrudProdutosStub:
    """Product repo stub for scheduling detail tests."""

    def __init__(self, produto=None):
        self.produto = produto
        self.updated = []

    def get_produto(self, *, produto_id):
        _ = produto_id
        return self.produto

    def update_produto(self, *, db_produto, produto_update):
        self.updated.append((db_produto, produto_update))


class _SchemasStub:
    """Minimal schema stub."""

    class ProdutoUpdate:
        def __init__(self, **kwargs):
            self.payload = kwargs


class _ModelsStub:
    """Minimal model enum stub."""

    class StatusGeracaoIAEnum:
        PENDENTE = "PENDENTE"


class _BackgroundTasksStub:
    """Background task stub."""

    def __init__(self):
        self.calls = []

    def add_task(self, task_executor, **kwargs):
        self.calls.append((task_executor, kwargs))


def _build_service(produto=None):
    """Build the scheduling service."""
    repo = _CrudProdutosStub(produto=produto)
    service = GenerationSchedulingService(
        schemas=_SchemasStub,
        models=_ModelsStub,
        product_repository=repo,
    )
    return service, repo


def test_validate_product_access_allows_superuser_and_mark_pending_ignores_unknown_generation_type():
    """Cover superuser access and unknown generation-type no-op."""
    produto = SimpleNamespace(user_id=999)
    service, repo = _build_service(produto=produto)
    found = service.validate_product_access(
        produto_id=10,
        current_user=SimpleNamespace(id=1, is_superuser=True),
    )
    assert found is produto

    service.mark_pending_status(db_produto=produto, generation_type="inexistente")
    assert repo.updated == []


def test_enqueue_generation_task_includes_optional_templates():
    """Cover optional template payload branches for scheduling."""
    service, _ = _build_service(produto=SimpleNamespace(user_id=1))
    background = _BackgroundTasksStub()

    def _executor(**kwargs):
        return kwargs

    service.enqueue_generation_task(
        background_tasks=background,
        task_executor=_executor,
        user_id=7,
        produto_id=8,
        generation_type="titulo",
        generation_func=object(),
        num_titulos=5,
        template_titulo="{nome_base}",
        template_descricao="{descricao_web}",
    )

    _, kwargs = background.calls[0]
    assert kwargs["num_titulos"] == 5
    assert kwargs["template_titulo"] == "{nome_base}"
    assert kwargs["template_descricao"] == "{descricao_web}"
