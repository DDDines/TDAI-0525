"""Tests for Celery configuration and task wrappers."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend import celery_app as celery_app_module
from Backend import celery_tasks


def test_celery_app_factory_builds_expected_config(monkeypatch):
    monkeypatch.setattr(
        celery_app_module,
        "settings",
        SimpleNamespace(
            CELERY_BROKER_URL="redis://broker/0",
            CELERY_RESULT_BACKEND="redis://backend/1",
            CELERY_TASK_ALWAYS_EAGER=True,
        ),
    )

    app = celery_app_module.CeleryAppFactory.build()

    assert app.conf["broker_url"] == "redis://broker/0"
    assert app.conf["result_backend"] == "redis://backend/1"
    assert app.conf["task_always_eager"] is True
    assert "Backend.celery_tasks" in app.conf["imports"]


def test_celery_task_wrappers_delegate_to_runtimes(monkeypatch):
    calls = []

    class _WebRunner:
        async def execute(self, **kwargs):
            calls.append(("web", kwargs))

    class _CatalogRunner:
        async def execute(self, **kwargs):
            calls.append(("catalog", kwargs))

    class _GenerationService:
        async def run_generation_task(self, **kwargs):
            calls.append(("generation", kwargs))

    class _TaskWorkflowStub:
        def process_pdf_extraction_task(self, **kwargs):
            calls.append(("pdf-page", kwargs))

    class _CommitService:
        def commit_job_task(self, **kwargs):
            calls.append(("commit", kwargs))

    monkeypatch.setattr(celery_tasks, "build_web_enrichment_task_runner", lambda: _WebRunner())
    monkeypatch.setattr(celery_tasks, "build_catalog_import_task_runner", lambda: _CatalogRunner())
    monkeypatch.setattr(celery_tasks, "build_generation_task_service", lambda: _GenerationService())
    monkeypatch.setattr(celery_tasks, "resolve_generation_callable", lambda key: f"callable:{key}")
    monkeypatch.setattr(celery_tasks, "TaskWorkflow", lambda: _TaskWorkflowStub())
    monkeypatch.setattr(celery_tasks, "build_pdf_region_extractor", lambda: lambda **kwargs: calls.append(("pdf-region", kwargs)))
    monkeypatch.setattr(celery_tasks, "build_fornecedor_import_job_service", lambda: _CommitService())

    celery_tasks.run_web_enrichment_start_task.run(produto_id=1, user_id=2, termos_busca_override="busca")
    celery_tasks.run_catalog_import_finalize_task.run(
        file_id=3,
        user_id=4,
        product_type_id=5,
        fornecedor_id=6,
        mapping={"sku": "SKU"},
        pages=[1],
        region=[0.1, 0.2, 0.3, 0.4],
        extraction_mode="ocr",
    )
    celery_tasks.run_generation_task.run(
        user_id=7,
        produto_id=8,
        tipo_geracao_principal="titulo",
        generation_provider_key="openai_title",
        num_titulos=4,
    )
    celery_tasks.run_pdf_page_extraction_task.run(import_job_id=9, page_number=10)
    celery_tasks.run_pdf_region_extraction_task.run(file_path="/tmp/catalog.pdf", page_number=11, region=[1, 2, 3, 4])
    celery_tasks.run_fornecedor_import_commit_task.run(job_id=12, user_id=13)

    assert calls == [
        ("web", {"produto_id": 1, "user_id": 2, "termos_busca_override": "busca"}),
        (
            "catalog",
            {
                "file_id": 3,
                "user_id": 4,
                "product_type_id": 5,
                "fornecedor_id": 6,
                "mapping": {"sku": "SKU"},
                "pages": [1],
                "region": [0.1, 0.2, 0.3, 0.4],
                "extraction_mode": "ocr",
            },
        ),
        (
            "generation",
            {
                "user_id": 7,
                "produto_id": 8,
                "tipo_geracao_principal": "titulo",
                "funcao_geracao_ia_no_servico": "callable:openai_title",
                "num_titulos": 4,
                "tamanho_palavras": None,
                "template_titulo": None,
                "template_descricao": None,
            },
        ),
        ("pdf-page", {"import_job_id": 9, "page_number": 10}),
        ("pdf-region", {"file_path": "/tmp/catalog.pdf", "page_number": 11, "region": [1, 2, 3, 4]}),
        ("commit", {"job_id": 12, "user_id": 13}),
    ]


def test_resolve_task_returns_registered_task():
    task = celery_tasks.resolve_task("generation.run")

    assert task.name == celery_tasks.run_generation_task.name


def test_resolve_task_raises_for_missing_name():
    with pytest.raises(LookupError):
        celery_tasks.resolve_task("missing.task")
