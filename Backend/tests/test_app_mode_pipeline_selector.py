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


class _TopLevelFunctionSurface:

    async def _dummy_executor(**kwargs):
        return kwargs

    @pytest.fixture(autouse=True)
    def _restore_app_mode():
        original = settings.APP_MODE
        try:
            yield
        finally:
            settings.APP_MODE = original

    def test_get_app_mode_forces_oop_for_supported_values():
        settings.APP_MODE = "oop"
        assert get_app_mode() == AppMode.OOP

    def test_get_app_mode_is_oop_for_any_config():
        settings.APP_MODE = "any-value"
        assert get_app_mode() == AppMode.OOP

    def test_pipeline_selector_selects_oop_plan():
        settings.APP_MODE = "oop"
        oop_plan = WebEnrichmentTaskBuilder(
            OOPWebEnrichmentExecutor(WebEnrichmentProcessingUseCase(_dummy_executor))
        ).build_start_plan(
            db_session_factory=SimpleNamespace(name="db_factory"),
            produto_id=7,
            user_id=99,
            termos_busca_override="teste",
        )
        selected = PipelineSelector("web_enrichment.start").select(
            oop_plan=oop_plan,
        )
        assert selected.executor_name == "oop_web_enrichment_task"
        assert selected.task_kwargs["produto_id"] == 7

    def test_pipeline_selector_uses_oop_in_oop_mode():
        settings.APP_MODE = "oop"
        oop_plan = WebEnrichmentTaskBuilder(
            OOPWebEnrichmentExecutor(WebEnrichmentProcessingUseCase(_dummy_executor))
        ).build_start_plan(
            db_session_factory=SimpleNamespace(name="db_factory"),
            produto_id=7,
            user_id=99,
            termos_busca_override="teste",
        )
        selected = PipelineSelector("web_enrichment.start").select(
            oop_plan=oop_plan,
        )
        assert selected.executor_name == "oop_web_enrichment_task"

    def test_catalog_import_builder_generates_expected_kwargs():
        plan = CatalogImportTaskBuilder(
            OOPCatalogImportExecutor(CatalogImportProcessingUseCase(_dummy_executor))
        ).build_finalize_plan(
            db_session_factory=SimpleNamespace(name="db_factory"),
            file_id=123,
            user_id=456,
            product_type_id=4,
            fornecedor_id=9,
            mapping={"col_0": "sku"},
            pages=[12],
            region=[1.0, 2.0, 3.0, 4.0],
        )
        assert plan.executor_name == "oop_catalog_import_task"
        assert plan.task_kwargs["file_id"] == 123
        assert plan.task_kwargs["fornecedor_id"] == 9

_dummy_executor = _TopLevelFunctionSurface._dummy_executor
_restore_app_mode = _TopLevelFunctionSurface._restore_app_mode
test_get_app_mode_forces_oop_for_supported_values = _TopLevelFunctionSurface.test_get_app_mode_forces_oop_for_supported_values
test_get_app_mode_is_oop_for_any_config = _TopLevelFunctionSurface.test_get_app_mode_is_oop_for_any_config
test_pipeline_selector_selects_oop_plan = _TopLevelFunctionSurface.test_pipeline_selector_selects_oop_plan
test_pipeline_selector_uses_oop_in_oop_mode = _TopLevelFunctionSurface.test_pipeline_selector_uses_oop_in_oop_mode
test_catalog_import_builder_generates_expected_kwargs = _TopLevelFunctionSurface.test_catalog_import_builder_generates_expected_kwargs












