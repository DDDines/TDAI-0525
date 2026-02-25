from types import SimpleNamespace

import pytest

from Backend.application.pipeline_selector import PipelineSelector
from Backend.application.pipelines.catalog_import import (
    CatalogImportTaskBuilder,
    OOPCatalogImportExecutor,
)
from Backend.application.pipelines.web_enrichment import (
    OOPWebEnrichmentExecutor,
    WebEnrichmentTaskBuilder,
)
from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)
from Backend.core.app_mode import AppMode, get_app_mode
from Backend.core.config import settings
from Backend.legacy.pipelines.catalog_import import LegacyCatalogImportTaskBuilder
from Backend.legacy.pipelines.web_enrichment import LegacyWebEnrichmentTaskBuilder


async def _dummy_executor(**kwargs):
    return kwargs


@pytest.fixture(autouse=True)
def _restore_app_mode():
    original = settings.APP_MODE
    try:
        yield
    finally:
        settings.APP_MODE = original


def test_get_app_mode_accepts_valid_values():
    settings.APP_MODE = "legacy"
    assert get_app_mode() == AppMode.LEGACY
    settings.APP_MODE = "oop"
    assert get_app_mode() == AppMode.OOP
    settings.APP_MODE = "shadow"
    assert get_app_mode() == AppMode.SHADOW


def test_get_app_mode_falls_back_to_legacy_on_invalid_value():
    settings.APP_MODE = "invalid-mode"
    assert get_app_mode() == AppMode.LEGACY


def test_pipeline_selector_uses_legacy_in_shadow_mode():
    settings.APP_MODE = "shadow"
    legacy_plan = LegacyCatalogImportTaskBuilder(_dummy_executor).build_finalize_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        file_id=1,
        user_id=10,
        product_type_id=2,
        fornecedor_id=3,
        mapping={"col_0": "sku"},
        pages=[1, 2],
        region=[0.1, 0.2, 0.3, 0.4],
    )
    oop_plan = CatalogImportTaskBuilder(
        OOPCatalogImportExecutor(CatalogImportProcessingUseCase(_dummy_executor))
    ).build_finalize_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        file_id=1,
        user_id=10,
        product_type_id=2,
        fornecedor_id=3,
        mapping={"col_0": "sku"},
        pages=[1, 2],
        region=[0.1, 0.2, 0.3, 0.4],
    )
    selected = PipelineSelector("catalog_import.finalize").select(
        legacy_plan=legacy_plan,
        oop_plan=oop_plan,
    )
    assert selected.executor_name == "legacy_catalog_import_task"


def test_pipeline_selector_uses_oop_in_oop_mode():
    settings.APP_MODE = "oop"
    legacy_plan = LegacyWebEnrichmentTaskBuilder(_dummy_executor).build_start_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        produto_id=7,
        user_id=99,
        termos_busca_override="teste",
    )
    oop_plan = WebEnrichmentTaskBuilder(
        OOPWebEnrichmentExecutor(WebEnrichmentProcessingUseCase(_dummy_executor))
    ).build_start_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        produto_id=7,
        user_id=99,
        termos_busca_override="teste",
    )
    selected = PipelineSelector("web_enrichment.start").select(
        legacy_plan=legacy_plan,
        oop_plan=oop_plan,
    )
    assert selected.executor_name == "oop_web_enrichment_task"


def test_builders_generate_compatible_kwargs():
    settings.APP_MODE = "legacy"
    legacy_plan = LegacyCatalogImportTaskBuilder(_dummy_executor).build_finalize_plan(
        db_session_factory=SimpleNamespace(name="db_factory"),
        file_id=123,
        user_id=456,
        product_type_id=4,
        fornecedor_id=9,
        mapping={"col_0": "sku"},
        pages=[12],
        region=[1.0, 2.0, 3.0, 4.0],
    )
    oop_plan = CatalogImportTaskBuilder(
        OOPCatalogImportExecutor(CatalogImportProcessingUseCase(_dummy_executor))
    ).build_finalize_plan(
        db_session_factory=legacy_plan.task_kwargs["db_session_factory"],
        file_id=123,
        user_id=456,
        product_type_id=4,
        fornecedor_id=9,
        mapping={"col_0": "sku"},
        pages=[12],
        region=[1.0, 2.0, 3.0, 4.0],
    )
    assert legacy_plan.task_kwargs == oop_plan.task_kwargs
