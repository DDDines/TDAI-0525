from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from Backend.application.services.catalog_import_components import (
    CatalogImportFileStateService,
    CatalogImportIssueTracker,
    CatalogImportQualityAccumulator,
    CatalogImportResultBuilder,
)


class _RepoStub:
    def __init__(self) -> None:
        self.saved = []

    def update_catalog_file(self, *, catalog_file):
        self.saved.append(catalog_file)
        return catalog_file


@dataclass
class _CatalogFileStub:
    status: str = "PENDING"
    fornecedor_id: int | None = None
    total_pages: int = 0
    pages_processed: int = 0
    result_summary: dict | None = None


class _ProdutoResponse:
    def __init__(self, payload):
        self._payload = payload

    @classmethod
    def model_validate(cls, payload):
        return cls(payload)

    def model_dump(self, mode="json"):
        _ = mode
        return self._payload


def _build_tracker():
    return CatalogImportIssueTracker(
        normalize_import_issue_item=lambda item: dict(item),
        extract_import_error_reason=lambda item: str(item.get("motivo_descarte") or item.get("motivo") or ""),
        is_non_critical_import_reason=lambda reason: reason.startswith("nc:"),
    )


def _build_result_builder(*, report_path=None):
    return CatalogImportResultBuilder(
        schemas=SimpleNamespace(ProdutoResponse=_ProdutoResponse),
        normalize_import_text=lambda value: str(value).strip().upper(),
        write_catalog_import_report=lambda **kwargs: report_path,
        outcome_resolver=SimpleNamespace(
            resolve=lambda **kwargs: (
                "FAILED" if kwargs["created_count"] == 0 and kwargs["updated_count"] == 0 else "PARTIAL",
                kwargs["errors_count"] > 0 and (kwargs["created_count"] + kwargs["updated_count"]) > 0,
            )
        ),
    )


def test_issue_tracker_caps_samples_and_skips_non_numeric_quarantine_scores():
    tracker = _build_tracker()

    for idx in range(35):
        tracker.add_issue({"motivo": f"nc:{idx}"})
        tracker.add_quarantine_issue({"motivo": f"q:{idx}", "qualidade_score": "ruim"})

    tracker.add_issue({"motivo": "erro-critico"})
    tracker.errors.append("nao-dict")

    assert len(tracker.ignored_non_critical) == 35
    assert len(tracker.ignored_samples) == 30
    assert tracker.quarantine_quality_scores == []
    assert len(tracker.quarantine_samples) == 30
    assert tracker.top_error_reasons(limit=5) == [("erro-critico", 1)]


def test_quality_accumulator_ignores_non_numeric_scores():
    quality = CatalogImportQualityAccumulator()

    quality.add_accepted("90")
    quality.add_quarantine(None)

    assert quality.accepted_avg is None
    assert quality.quarantine_avg is None


def test_file_state_service_marks_missing_and_failure():
    repo = _RepoStub()
    service = CatalogImportFileStateService(catalog_file_repository=repo)
    file_obj = _CatalogFileStub()

    service.mark_file_missing(
        catalog_file=file_obj,
        file_id=7,
        stored_filename="catalogo-ausente.pdf",
    )
    assert file_obj.status == "FAILED"
    assert file_obj.result_summary["errors"][0]["stored_filename"] == "catalogo-ausente.pdf"

    service.mark_failure_with_exception(
        catalog_file=file_obj,
        file_id=8,
        error=RuntimeError("boom"),
    )
    assert file_obj.result_summary["errors"][0]["erro_processamento"] == "boom"
    assert len(repo.saved) == 2


def test_result_builder_covers_unknown_status_zero_progress_and_quarantine_logs():
    tracker = _build_tracker()
    tracker.add_quarantine_issue({"motivo_descarte": "baixou score", "qualidade_score": 12})
    quality = CatalogImportQualityAccumulator()
    quality.add_quarantine(12)
    builder = _build_result_builder(report_path=None)

    payload = builder.build(
        file_id=1,
        created=[],
        updated=[],
        issue_tracker=tracker,
        quality_scores=quality,
        pages_processed=0,
        pages_total=0,
        ext=".pdf",
    )

    assert builder._status_label("UNKNOWN") == "Importacao finalizada"
    assert builder._progress_pct(pages_processed=4, pages_total=0) == 0.0
    assert payload["final_status"] == "FAILED"
    assert payload["result_summary"]["output"]["status_label"] == "Importacao falhou"
    assert "Top linhas em quarentena" in payload["result_summary"]["log"][3]
    assert "Score medio de qualidade (quarentena): 12.0" in payload["result_summary"]["log"][4]
    assert all("Relatorio detalhado" not in line for line in payload["result_summary"]["log"])


def test_result_builder_appends_report_log_when_path_exists():
    tracker = _build_tracker()
    builder = _build_result_builder(report_path="relatorio.json")

    payload = builder.build(
        file_id=2,
        created=[{"id": 1}],
        updated=[],
        issue_tracker=tracker,
        quality_scores=CatalogImportQualityAccumulator(),
        pages_processed=2,
        pages_total=4,
        ext=".csv",
    )

    assert payload["result_summary"]["output"]["status"] == "PARTIAL"
    assert payload["report_path"] == "relatorio.json"
    assert payload["result_summary"]["log"][-1] == "Relatorio detalhado: relatorio.json"


def test_result_builder_covers_imported_status_and_ignored_reason_log():
    tracker = _build_tracker()
    tracker.add_issue({"motivo": "nc:linha fraca"})
    builder = CatalogImportResultBuilder(
        schemas=SimpleNamespace(ProdutoResponse=_ProdutoResponse),
        normalize_import_text=lambda value: value,
        write_catalog_import_report=lambda **kwargs: "",
        outcome_resolver=SimpleNamespace(resolve=lambda **kwargs: ("IMPORTED", False)),
    )

    payload = builder.build(
        file_id=3,
        created=[{"id": 1}],
        updated=[{"id": 2}],
        issue_tracker=tracker,
        quality_scores=CatalogImportQualityAccumulator(),
        pages_processed=1,
        pages_total=1,
        ext=".xlsx",
    )

    assert builder._status_label("IMPORTED") == "Importacao concluida"
    assert "concluida com sucesso" in payload["result_summary"]["output"]["headline"]
    assert "Top descartes nao criticos: nc:linha fraca (1)" in payload["result_summary"]["log"][-1]
