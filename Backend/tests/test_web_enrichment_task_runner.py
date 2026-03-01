from __future__ import annotations

import pytest

from Backend.application.services.web_enrichment_task_runner import (
    WebEnrichmentTaskRunner,
)


class _TaskServiceStub:
    def __init__(self) -> None:
        self.calls = []

    async def execute(self, **kwargs):
        self.calls.append(kwargs)


def _build_runner() -> WebEnrichmentTaskRunner:
    return WebEnrichmentTaskRunner(
        logger=object(),
        SQLAlchemyError=Exception,
        user_repository=object(),
        product_repository=object(),
        usage_repository=object(),
        models=object(),
        schemas=object(),
        web_extractor=object(),
        settings=object(),
        json_module=object(),
        re_module=object(),
        normalize_human_text=object(),
        build_payload_enriquecimento_visivel=object(),
        extrair_dominio_fornecedor=object(),
        priorizar_urls_para_enriquecimento=object(),
        is_meaningful_extracted_text=object(),
        metadata_has_minimum_signal=object(),
        is_source_relevant_for_product=object(),
    )


@pytest.mark.asyncio
async def test_web_enrichment_task_runner_uses_single_oop_service():
    runner = _build_runner()
    service_stub = _TaskServiceStub()
    build_calls = []

    def _fake_build():
        build_calls.append("build")
        return service_stub

    runner._build = _fake_build  # type: ignore[attr-defined]

    await runner.execute(
        db_session_factory=lambda: None,
        produto_id=10,
        user_id=20,
        termos_busca_override="item x",
    )
    await runner.execute(
        db_session_factory=lambda: None,
        produto_id=30,
        user_id=40,
    )
    await runner.execute(
        db_session_factory=lambda: None,
        produto_id=11,
        user_id=21,
    )

    assert build_calls == ["build"]
    assert len(service_stub.calls) == 3
    assert service_stub.calls[0]["produto_id"] == 10
    assert service_stub.calls[1]["produto_id"] == 30
    assert service_stub.calls[2]["produto_id"] == 11


@pytest.mark.asyncio
async def test_web_enrichment_task_runner_execute_reuses_cached_service():
    runner = _build_runner()
    service_stub = _TaskServiceStub()
    build_calls = []

    def _fake_build():
        build_calls.append("build")
        return service_stub

    runner._build = _fake_build  # type: ignore[attr-defined]

    await runner.execute(
        db_session_factory=lambda: None,
        produto_id=91,
        user_id=42,
    )
    await runner.execute(
        db_session_factory=lambda: None,
        produto_id=92,
        user_id=43,
    )

    assert build_calls == ["build"]
    assert len(service_stub.calls) == 2
    assert service_stub.calls[0]["produto_id"] == 91
    assert service_stub.calls[1]["produto_id"] == 92
