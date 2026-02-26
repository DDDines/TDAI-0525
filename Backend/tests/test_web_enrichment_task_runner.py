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
        crud_users=object(),
        crud_produtos=object(),
        crud=object(),
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
async def test_web_enrichment_task_runner_dispatches_legacy_and_oop():
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
        produto_id=10,
        user_id=20,
        termos_busca_override="item x",
    )
    await runner.execute_oop(produto_id=30, user_id=40)
    await runner.execute_legacy(
        db_session_factory=lambda: None,
        produto_id=11,
        user_id=21,
    )

    assert build_calls == ["legacy", "oop"]
    assert len(legacy_stub.calls) == 2
    assert legacy_stub.calls[0]["produto_id"] == 10
    assert len(oop_stub.calls) == 1
    assert oop_stub.calls[0]["produto_id"] == 30
