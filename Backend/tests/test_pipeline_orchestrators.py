from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.contracts.pipeline_commands import (
    CatalogImportFinalizeCommand,
    WebEnrichmentStartCommand,
)
from Backend.application.orchestrators.catalog_import import (
    CatalogImportPipelineOrchestrator,
)
from Backend.application.orchestrators.web_enrichment import (
    WebEnrichmentPipelineOrchestrator,
)
from Backend.core.config import settings


async def _dummy_executor(**kwargs):
    return kwargs


@pytest.fixture(autouse=True)
def _restore_app_mode():
    original = settings.APP_MODE
    try:
        yield
    finally:
        settings.APP_MODE = original


def test_catalog_import_orchestrator_uses_legacy_in_shadow_mode():
    settings.APP_MODE = "shadow"
    orchestrator = CatalogImportPipelineOrchestrator(
        legacy_executor=_dummy_executor,
    )
    command = CatalogImportFinalizeCommand(
        file_id=123,
        user_id=456,
        product_type_id=7,
        fornecedor_id=8,
        mapping={"col_0": "sku"},
        pages=[12],
        region=[0.1, 0.2, 0.3, 0.4],
    )
    plan = orchestrator.select_finalize_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        command=command,
    )
    assert plan.executor_name == "legacy_catalog_import_task"
    assert plan.task_kwargs["file_id"] == 123
    assert plan.task_kwargs["fornecedor_id"] == 8


def test_catalog_import_orchestrator_uses_oop_in_oop_mode():
    settings.APP_MODE = "oop"
    orchestrator = CatalogImportPipelineOrchestrator(
        legacy_executor=_dummy_executor,
    )
    command = CatalogImportFinalizeCommand(
        file_id=1,
        user_id=2,
        product_type_id=3,
        fornecedor_id=4,
        mapping={"col_0": "sku"},
        pages=[1, 2, 3],
        region=[1.0, 2.0, 3.0, 4.0],
    )
    plan = orchestrator.select_finalize_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        command=command,
    )
    assert plan.executor_name == "oop_catalog_import_task"
    assert plan.task_kwargs["product_type_id"] == 3
    assert plan.task_kwargs["pages"] == [1, 2, 3]


def test_web_enrichment_orchestrator_uses_legacy_in_shadow_mode():
    settings.APP_MODE = "shadow"
    orchestrator = WebEnrichmentPipelineOrchestrator(
        legacy_executor=_dummy_executor,
    )
    command = WebEnrichmentStartCommand(
        produto_id=10,
        user_id=11,
        termos_busca_override="teste xyz",
    )
    plan = orchestrator.select_start_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        command=command,
    )
    assert plan.executor_name == "legacy_web_enrichment_task"
    assert plan.task_kwargs["produto_id"] == 10


def test_web_enrichment_orchestrator_uses_oop_in_oop_mode():
    settings.APP_MODE = "oop"
    orchestrator = WebEnrichmentPipelineOrchestrator(
        legacy_executor=_dummy_executor,
    )
    command = WebEnrichmentStartCommand(
        produto_id=10,
        user_id=11,
        termos_busca_override=None,
    )
    plan = orchestrator.select_start_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        command=command,
    )
    assert plan.executor_name == "oop_web_enrichment_task"
    assert plan.task_kwargs["user_id"] == 11
