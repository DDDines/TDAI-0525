from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace

from Backend.application.services.catalog_import_components import (
    CatalogImportAuditWriter,
    CatalogImportFileStateService,
    CatalogImportIssueTracker,
    CatalogImportOutcomeResolver,
    CatalogImportQualityAccumulator,
    CatalogImportResultBuilder,
)


class _TopLevelFunctionSurface:

    def test_issue_tracker_classifies_critical_vs_non_critical():
        tracker = CatalogImportIssueTracker(
            normalize_import_issue_item=lambda item: dict(item),
            extract_import_error_reason=lambda item: str(item.get("motivo", "")),
            is_non_critical_import_reason=lambda reason: reason.startswith("nc:"),
        )
    
        tracker.add_issue({"motivo": "nc:linha fraca"})
        tracker.add_issue({"motivo": "erro critico x"})
        tracker.add_quarantine_issue({"motivo": "quarentena: score baixo", "qualidade_score": 58})
    
        assert len(tracker.ignored_non_critical) == 1
        assert len(tracker.errors) == 1
        assert len(tracker.quarantine_non_critical) == 1
        assert tracker.quarantine_quality_scores == [58]
        assert tracker.top_error_reasons(limit=1)[0][0] == "erro critico x"
        assert tracker.top_ignored_reasons(limit=1)[0][0] == "nc:linha fraca"
        assert tracker.top_quarantine_reasons(limit=1)[0][0] == "quarentena: score baixo"

    def test_quality_accumulator_returns_averages():
        quality = CatalogImportQualityAccumulator()
        quality.add_accepted(90)
        quality.add_accepted(80.0)
        quality.add_quarantine(55)
        quality.add_quarantine(65.0)
    
        assert quality.accepted_avg == 85.0
        assert quality.quarantine_avg == 60.0

    def test_outcome_resolver_returns_failed_when_no_success():
        resolver = CatalogImportOutcomeResolver()
        status, partial = resolver.resolve(
            created_count=0,
            updated_count=0,
            errors_count=2,
            ignored_count=3,
            quarantine_count=1,
        )
        assert status == "FAILED"
        assert partial is False

    def test_outcome_resolver_returns_partial_when_has_success_and_errors():
        resolver = CatalogImportOutcomeResolver()
        status, partial = resolver.resolve(
            created_count=2,
            updated_count=1,
            errors_count=1,
            ignored_count=0,
            quarantine_count=0,
        )
        assert status == "PARTIAL"
        assert partial is True

    def test_file_state_service_persists_processing_and_final():
        repo = _FakeCatalogFileRepo()
        file_obj = _FakeCatalogFile()
    
        CatalogImportFileStateService.mark_processing(
            catalog_file_repo=repo,
            catalog_file=file_obj,
            fornecedor_id=9,
        )
        CatalogImportFileStateService.initialize_pages(
            catalog_file_repo=repo,
            catalog_file=file_obj,
            total_pages=10,
        )
        CatalogImportFileStateService.increment_page(
            catalog_file_repo=repo,
            catalog_file=file_obj,
        )
        CatalogImportFileStateService.mark_final(
            catalog_file_repo=repo,
            catalog_file=file_obj,
            final_status="IMPORTED",
            result_summary={"stats": {"ok": True}},
        )
    
        assert file_obj.status == "IMPORTED"
        assert file_obj.fornecedor_id == 9
        assert file_obj.total_pages == 10
        assert file_obj.pages_processed == 1
        assert file_obj.result_summary == {"stats": {"ok": True}}
        assert len(repo.saved) == 4
        assert repo.saved[-1] is file_obj

    def test_audit_writer_adds_usage_and_history_rows():
        class _Usage:
            def __init__(self, **kwargs):
                self.payload = kwargs
    
        class _History:
            def __init__(self, **kwargs):
                self.payload = kwargs
    
        class _Actions:
            CRIACAO_PRODUTO = "CRIACAO_PRODUTO"
    
        class _SysActions:
            CRIACAO = "CRIACAO"
    
        models = SimpleNamespace(
            RegistroUsoIA=_Usage,
            RegistroHistorico=_History,
            TipoAcaoEnum=_Actions,
            TipoAcaoSistemaEnum=_SysActions,
        )
        db = _FakeDB()
        writer = CatalogImportAuditWriter(models=models)
        produtos = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    
        writer.register_creation(session=db, user_id=42, produtos_criados=produtos)
    
        assert len(db.added) == 4
        assert db.added[0].payload["produto_id"] == 1
        assert db.added[1].payload["entity_id"] == 1
        assert db.added[2].payload["produto_id"] == 2
        assert db.added[3].payload["entity_id"] == 2

    def test_result_builder_generates_summary_and_report():
        class _ProdutoResponse:
            def __init__(self, payload):
                self._payload = payload
    
            @classmethod
            def model_validate(cls, payload):
                return cls(payload)
    
            def model_dump(self, mode="json"):
                return self._payload
    
        schemas = SimpleNamespace(ProdutoResponse=_ProdutoResponse)
        report_calls = []
        resolver = CatalogImportOutcomeResolver()
        builder = CatalogImportResultBuilder(
            schemas=schemas,
            normalize_import_text=lambda value: value,
            write_catalog_import_report=lambda **kwargs: report_calls.append(kwargs) or "r.json",
            outcome_resolver=resolver,
        )
        tracker = CatalogImportIssueTracker(
            normalize_import_issue_item=lambda item: item,
            extract_import_error_reason=lambda item: item.get("motivo_descarte", "x"),
            is_non_critical_import_reason=lambda reason: False,
        )
        tracker.add_issue({"motivo_descarte": "erro x"})
        quality = CatalogImportQualityAccumulator()
        quality.add_accepted(90)
    
        payload = builder.build(
            file_id=99,
            created=[{"id": 1}],
            updated=[],
            issue_tracker=tracker,
            quality_scores=quality,
            pages_processed=3,
            pages_total=10,
            ext=".pdf",
        )
    
        assert payload["final_status"] == "PARTIAL"
        assert payload["created_count"] == 1
        assert payload["errors_count"] == 1
        assert payload["result_summary"]["stats"]["pages_processed"] == 3
        assert payload["report_path"] == "r.json"
        assert len(report_calls) == 1

test_issue_tracker_classifies_critical_vs_non_critical = _TopLevelFunctionSurface.test_issue_tracker_classifies_critical_vs_non_critical
test_quality_accumulator_returns_averages = _TopLevelFunctionSurface.test_quality_accumulator_returns_averages
test_outcome_resolver_returns_failed_when_no_success = _TopLevelFunctionSurface.test_outcome_resolver_returns_failed_when_no_success
test_outcome_resolver_returns_partial_when_has_success_and_errors = _TopLevelFunctionSurface.test_outcome_resolver_returns_partial_when_has_success_and_errors
test_file_state_service_persists_processing_and_final = _TopLevelFunctionSurface.test_file_state_service_persists_processing_and_final
test_audit_writer_adds_usage_and_history_rows = _TopLevelFunctionSurface.test_audit_writer_adds_usage_and_history_rows
test_result_builder_generates_summary_and_report = _TopLevelFunctionSurface.test_result_builder_generates_summary_and_report








class _FakeDB:
    def __init__(self) -> None:
        self.commits = 0
        self.added = []

    def commit(self) -> None:
        self.commits += 1

    def add(self, item) -> None:
        self.added.append(item)


class _FakeCatalogFileRepo:
    def __init__(self) -> None:
        self.saved = []

    def update_catalog_file(self, *, catalog_file):
        self.saved.append(catalog_file)
        return catalog_file


@dataclass
class _FakeCatalogFile:
    status: str = "PENDING"
    fornecedor_id: int | None = None
    total_pages: int = 0
    pages_processed: int = 0
    stored_filename: str = "x.pdf"
    result_summary: dict | None = None






