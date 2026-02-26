from __future__ import annotations

import pytest

from Backend.application.services.catalog_import_task_runner import (
    CatalogImportTaskRunner,
)


class _TaskServiceStub:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)


def _build_runner() -> CatalogImportTaskRunner:
    return CatalogImportTaskRunner(
        logger=object(),
        catalog_logger=object(),
        models=object(),
        schemas=object(),
        crud_produtos=object(),
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
async def test_catalog_import_task_runner_dispatches_legacy_and_oop():
    runner = _build_runner()
    legacy_stub = _TaskServiceStub()
    oop_stub = _TaskServiceStub()
    build_calls = []

    def _fake_build(*, pipeline_variant: str):
        build_calls.append(pipeline_variant)
        return legacy_stub if pipeline_variant == "legacy" else oop_stub

    runner._build = _fake_build  # type: ignore[attr-defined]

    await runner.execute_legacy(
        db_session_factory=lambda: None,
        file_id=1,
        user_id=2,
        product_type_id=3,
        fornecedor_id=4,
        mapping={"a": "b"},
        pages=[1],
        region=[0.0, 0.0, 1.0, 1.0],
    )
    await runner.execute_oop(file_id=9)
    await runner.execute_legacy(
        db_session_factory=lambda: None,
        file_id=10,
        user_id=20,
        product_type_id=None,
        fornecedor_id=40,
    )

    assert build_calls == ["legacy", "oop"]
    assert len(legacy_stub.calls) == 2
    assert legacy_stub.calls[0]["file_id"] == 1
    assert len(oop_stub.calls) == 1
    assert oop_stub.calls[0]["file_id"] == 9

