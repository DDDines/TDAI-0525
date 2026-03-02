"""Module test catalog import task runner.

Contains backend logic related to test catalog import task runner and documents its role in the OOP architecture.
"""

from __future__ import annotations

import pytest

from Backend.application.services.catalog_import_task_runner import (
    CatalogImportTaskRunner,
)


class _TaskServiceStub:
    """Represent task service stub and centralize responsibilities for this module."""
    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.calls = []

    async def execute(self, **kwargs):
        """Run execute in this workflow."""
        self.calls.append(kwargs)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _build_runner() -> CatalogImportTaskRunner:
        """Run build runner in this workflow."""
        return CatalogImportTaskRunner(
            session_provider=type("SessionProviderStub", (), {"open_session": staticmethod(lambda: None)})(),
            logger=object(),
            catalog_logger=object(),
            models=object(),
            schemas=object(),
            product_repository_factory=object(),
            catalog_file_repository_factory=object(),
            file_processing_service=object(),
            validator_crew=object(),
            settings=object(),
            path_cls=object(),
            time_module=object(),
            counter_cls=object(),
            resolve_storage_path=object(),
            normalize_import_issue_item=object(),
            extract_import_error_reason=object(),
            is_non_critical_import_reason=object(),
            normalizar_dados_validados=object(),
            sanitize_produto_extraido=object(),
            classificar_qualidade_linha_produto=object(),
            write_catalog_import_report=object(),
            normalize_import_text=object(),
        )

    @pytest.mark.asyncio
    async def test_catalog_import_task_runner_uses_single_oop_service():
        """Run test catalog import task runner uses single oop service in this workflow."""
        runner = _build_runner()
        service_stub = _TaskServiceStub()
        build_calls = []
    
        def _fake_build():
            """Run fake build in this workflow."""
            build_calls.append("build")
            return service_stub
    
        runner._build = _fake_build  # type: ignore[attr-defined]
    
        await runner.execute(
            file_id=1,
            user_id=2,
            product_type_id=3,
            fornecedor_id=4,
            mapping={"a": "b"},
            pages=[1],
            region=[0.0, 0.0, 1.0, 1.0],
        )
        await runner.execute(
            file_id=9,
            user_id=0,
            product_type_id=None,
            fornecedor_id=0,
        )
        await runner.execute(
            file_id=10,
            user_id=20,
            product_type_id=None,
            fornecedor_id=40,
        )
    
        assert build_calls == ["build"]
        assert len(service_stub.calls) == 3
        assert service_stub.calls[0]["file_id"] == 1
        assert service_stub.calls[1]["file_id"] == 9
        assert service_stub.calls[2]["file_id"] == 10

    @pytest.mark.asyncio
    async def test_catalog_import_task_runner_execute_reuses_cached_service():
        """Run test catalog import task runner execute reuses cached service in this workflow."""
        runner = _build_runner()
        service_stub = _TaskServiceStub()
        build_calls = []
    
        def _fake_build():
            """Run fake build in this workflow."""
            build_calls.append("build")
            return service_stub
    
        runner._build = _fake_build  # type: ignore[attr-defined]
    
        await runner.execute(
            file_id=77,
            user_id=88,
            product_type_id=None,
            fornecedor_id=0,
        )
        await runner.execute(
            file_id=78,
            user_id=89,
            product_type_id=None,
            fornecedor_id=0,
        )
    
        assert build_calls == ["build"]
        assert len(service_stub.calls) == 2
        assert service_stub.calls[0]["file_id"] == 77
        assert service_stub.calls[1]["file_id"] == 78

_build_runner = _TopLevelFunctionSurface._build_runner
test_catalog_import_task_runner_uses_single_oop_service = _TopLevelFunctionSurface.test_catalog_import_task_runner_uses_single_oop_service
test_catalog_import_task_runner_execute_reuses_cached_service = _TopLevelFunctionSurface.test_catalog_import_task_runner_execute_reuses_cached_service




