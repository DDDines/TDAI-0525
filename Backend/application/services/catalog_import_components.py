"""Catalog import components.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from collections import Counter
from typing import Any, Callable, Dict, List, Optional, Tuple


class CatalogImportIssueTracker:
    """Centraliza coleta/classificação de erros, descartes e quarentena."""

    def __init__(
        self,
        *,
        normalize_import_issue_item: Callable[[Dict[str, Any]], Dict[str, Any]],
        extract_import_error_reason: Callable[[Dict[str, Any]], str],
        is_non_critical_import_reason: Callable[[str], bool],
    ) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._normalize_import_issue_item = normalize_import_issue_item
        self._extract_import_error_reason = extract_import_error_reason
        self._is_non_critical_import_reason = is_non_critical_import_reason

        self.errors: List[Dict[str, Any]] = []
        self.ignored_non_critical: List[Dict[str, Any]] = []
        self.ignored_reason_counter: Counter[str] = Counter()
        self.ignored_samples: List[Dict[str, Any]] = []

        self.quarantine_non_critical: List[Dict[str, Any]] = []
        self.quarantine_reason_counter: Counter[str] = Counter()
        self.quarantine_samples: List[Dict[str, Any]] = []
        self.quarantine_quality_scores: List[int] = []

    def add_issue(self, item: Dict[str, Any]) -> None:
        """Process Add issue."""
        normalized_item = self._normalize_import_issue_item(item)
        reason = self._extract_import_error_reason(normalized_item)
        if self._is_non_critical_import_reason(reason):
            self.ignored_non_critical.append(normalized_item)
            self.ignored_reason_counter[reason] += 1
            if len(self.ignored_samples) < 30:
                self.ignored_samples.append(normalized_item)
            return
        self.errors.append(normalized_item)

    def add_quarantine_issue(self, item: Dict[str, Any]) -> None:
        """Process Add quarantine issue."""
        normalized_item = self._normalize_import_issue_item(item)
        reason = self._extract_import_error_reason(normalized_item)
        self.quarantine_non_critical.append(normalized_item)
        self.quarantine_reason_counter[reason] += 1
        score_value = normalized_item.get("qualidade_score")
        if isinstance(score_value, (int, float)):
            self.quarantine_quality_scores.append(int(score_value))
        if len(self.quarantine_samples) < 30:
            self.quarantine_samples.append(normalized_item)

    def top_error_reasons(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Process Top error reasons."""
        reasons = Counter(
            self._extract_import_error_reason(err)
            for err in self.errors
            if isinstance(err, dict)
        )
        return reasons.most_common(limit)

    def top_ignored_reasons(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Process Top ignored reasons."""
        return self.ignored_reason_counter.most_common(limit)

    def top_quarantine_reasons(self, limit: int = 10) -> List[Tuple[str, int]]:
        """Process Top quarantine reasons."""
        return self.quarantine_reason_counter.most_common(limit)


class CatalogImportQualityAccumulator:
    """Agrega scores de qualidade para estatísticas finais."""

    def __init__(self) -> None:
        """Initialize required dependencies and runtime configuration."""
        self.accepted_scores: List[int] = []
        self.quarantine_scores: List[int] = []

    def add_accepted(self, score: Any) -> None:
        """Process Add accepted."""
        if isinstance(score, (int, float)):
            self.accepted_scores.append(int(score))

    def add_quarantine(self, score: Any) -> None:
        """Process Add quarantine."""
        if isinstance(score, (int, float)):
            self.quarantine_scores.append(int(score))

    @staticmethod
    def _avg(values: List[int]) -> Optional[float]:
        """Process Avg."""
        return round(sum(values) / len(values), 2) if values else None

    @property
    def accepted_avg(self) -> Optional[float]:
        """Process Accepted avg."""
        return self._avg(self.accepted_scores)

    @property
    def quarantine_avg(self) -> Optional[float]:
        """Process Quarantine avg."""
        return self._avg(self.quarantine_scores)


class CatalogImportOutcomeResolver:
    """Resolve status final da importacao com base no resultado consolidado."""

    def resolve(
        self,
        *,
        created_count: int,
        updated_count: int,
        errors_count: int,
        ignored_count: int,
        quarantine_count: int,
    ) -> Tuple[str, bool]:
        """Process Resolve."""
        total_success = created_count + updated_count
        has_partial_success = total_success > 0 and errors_count > 0
        final_status = "IMPORTED"
        if total_success == 0 and (errors_count > 0 or ignored_count > 0 or quarantine_count > 0):
            final_status = "FAILED"
        elif has_partial_success:
            final_status = "PARTIAL"
        return final_status, has_partial_success


class CatalogImportFileStateService:
    """Encapsula persistencia de status/paginas do CatalogImportFile."""

    def __init__(self, *, catalog_file_repository: Any) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._catalog_file_repository = catalog_file_repository

    def _repo(self) -> Any:
        """Process Repo."""
        return self._catalog_file_repository

    def mark_processing(self, *, catalog_file: Any, fornecedor_id: int) -> None:
        """Mark processing."""
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        self._repo().update_catalog_file(catalog_file=catalog_file)

    def mark_file_missing(
        self,
        *,
        catalog_file: Any,
        file_id: int,
        stored_filename: str,
    ) -> None:
        """Mark file missing."""
        catalog_file.status = "FAILED"
        catalog_file.result_summary = {
            "created": [],
            "updated": [],
            "errors": [
                {
                    "erro_processamento": "Arquivo de catalogo nao encontrado no armazenamento.",
                    "file_id": file_id,
                    "stored_filename": stored_filename,
                }
            ],
        }
        self._repo().update_catalog_file(catalog_file=catalog_file)

    def initialize_pages(
        self,
        *,
        catalog_file: Any,
        total_pages: int,
    ) -> None:
        """Process Initialize pages."""
        catalog_file.total_pages = total_pages
        catalog_file.pages_processed = 0
        self._repo().update_catalog_file(catalog_file=catalog_file)

    def increment_page(self, *, catalog_file: Any) -> None:
        """Process Increment page."""
        catalog_file.pages_processed = (catalog_file.pages_processed or 0) + 1
        self._repo().update_catalog_file(catalog_file=catalog_file)

    def mark_final(
        self,
        *,
        catalog_file: Any,
        final_status: str,
        result_summary: Dict[str, Any],
    ) -> None:
        """Mark final."""
        catalog_file.status = final_status
        catalog_file.result_summary = result_summary
        self._repo().update_catalog_file(catalog_file=catalog_file)

    def mark_failure_with_exception(
        self,
        *,
        catalog_file: Any,
        file_id: int,
        error: Exception,
    ) -> None:
        """Mark failure with exception."""
        catalog_file.status = "FAILED"
        catalog_file.result_summary = {
            "created": [],
            "updated": [],
            "errors": [
                {
                    "erro_processamento": str(error),
                    "file_id": file_id,
                }
            ],
        }
        self._repo().update_catalog_file(catalog_file=catalog_file)


class CatalogImportAuditWriter:
    """Registra auditoria de criacao dos produtos em lote."""

    def __init__(self, *, models: Any) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._models = models

    def register_creation(
        self,
        *,
        user_id: int,
        produtos_criados: List[Any],
        session: Any,
    ) -> None:
        """Process Register creation."""
        for db_produto in produtos_criados:
            session.add(
                self._models.RegistroUsoIA(
                    user_id=user_id,
                    produto_id=db_produto.id,
                    tipo_acao=self._models.TipoAcaoEnum.CRIACAO_PRODUTO,
                    creditos_consumidos=0,
                )
            )
            session.add(
                self._models.RegistroHistorico(
                    user_id=user_id,
                    entidade="Produto",
                    acao=self._models.TipoAcaoSistemaEnum.CRIACAO,
                    entity_id=db_produto.id,
                )
            )


class CatalogImportResultBuilder:
    """Monta summary final da importacao (stats/log/report) de forma consistente."""

    def __init__(
        self,
        *,
        schemas: Any,
        normalize_import_text: Callable[[str], str],
        write_catalog_import_report: Callable[..., Any],
        outcome_resolver: CatalogImportOutcomeResolver,
    ) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._schemas = schemas
        self._normalize_import_text = normalize_import_text
        self._write_catalog_import_report = write_catalog_import_report
        self._outcome_resolver = outcome_resolver

    def build(
        self,
        *,
        file_id: int,
        created: List[Any],
        updated: List[Any],
        issue_tracker: CatalogImportIssueTracker,
        quality_scores: CatalogImportQualityAccumulator,
        pages_processed: int,
        pages_total: int,
        ext: str,
    ) -> Dict[str, Any]:
        """Process Build."""
        created_count = len(created)
        updated_count = len(updated)
        errors_count = len(issue_tracker.errors)
        ignored_count = len(issue_tracker.ignored_non_critical)
        quarantine_count = len(issue_tracker.quarantine_non_critical)
        final_status, has_partial_success = self._outcome_resolver.resolve(
            created_count=created_count,
            updated_count=updated_count,
            errors_count=errors_count,
            ignored_count=ignored_count,
            quarantine_count=quarantine_count,
        )

        top_reasons = issue_tracker.top_error_reasons(limit=10)
        top_ignored_reasons = issue_tracker.top_ignored_reasons(limit=10)
        top_quarantine_reasons = issue_tracker.top_quarantine_reasons(limit=10)
        accepted_quality_avg = quality_scores.accepted_avg
        quarantine_quality_avg = quality_scores.quarantine_avg

        result_summary: Dict[str, Any] = {
            "created": [
                self._schemas.ProdutoResponse.model_validate(p).model_dump(mode="json")
                for p in created
            ],
            "updated": [
                self._schemas.ProdutoResponse.model_validate(p).model_dump(mode="json")
                for p in updated
            ],
            "errors": issue_tracker.errors,
            "ignored_non_critical": issue_tracker.ignored_non_critical,
            "quarantine_non_critical": issue_tracker.quarantine_non_critical,
            "stats": {
                "produtos_criados": created_count,
                "produtos_atualizados": updated_count,
                "erros": errors_count,
                "critical_errors": errors_count,
                "descartes_nao_criticos": ignored_count,
                "quarentena_nao_critica": quarantine_count,
                "qualidade_score_medio_aceitas": accepted_quality_avg,
                "qualidade_score_medio_quarentena": quarantine_quality_avg,
                "partial_success": has_partial_success,
                "pages_processed": pages_processed or 0,
                "pages_total": pages_total or 0,
                "ext": ext,
            },
            "log": [
                f"Resumo final: status={final_status}",
                (
                    f"Criados={created_count}, Atualizados={updated_count}, "
                    f"Erros={errors_count}, Descartes não críticos={ignored_count}, "
                    f"Quarentena não crítica={quarantine_count}"
                ),
            ],
        }
        if top_reasons:
            top_reasons_log = "; ".join(
                [f"{self._normalize_import_text(reason)} ({count})" for reason, count in top_reasons]
            )
            result_summary["log"].append(f"Top motivos de erro: {top_reasons_log}")
        if top_ignored_reasons:
            top_ignored_log = "; ".join(
                [f"{self._normalize_import_text(reason)} ({count})" for reason, count in top_ignored_reasons]
            )
            result_summary["log"].append(f"Top descartes não críticos: {top_ignored_log}")
        if top_quarantine_reasons:
            top_quarantine_log = "; ".join(
                [
                    f"{self._normalize_import_text(reason)} ({count})"
                    for reason, count in top_quarantine_reasons
                ]
            )
            result_summary["log"].append(f"Top linhas em quarentena: {top_quarantine_log}")
        if accepted_quality_avg is not None:
            result_summary["log"].append(
                f"Score médio de qualidade (aceitas): {accepted_quality_avg}"
            )
        if quarantine_quality_avg is not None:
            result_summary["log"].append(
                f"Score médio de qualidade (quarentena): {quarantine_quality_avg}"
            )
        if has_partial_success:
            result_summary["log"].append(
                "Importação concluída com sucesso parcial: produtos foram gravados, mas houve erros críticos."
            )

        report_path = self._write_catalog_import_report(
            file_id=file_id,
            status=final_status,
            created_count=created_count,
            updated_count=updated_count,
            errors=issue_tracker.errors,
            ignored_count=ignored_count,
            ignored_reasons=top_ignored_reasons,
            ignored_samples=issue_tracker.ignored_samples,
            quarantine_count=quarantine_count,
            quarantine_reasons=top_quarantine_reasons,
            quarantine_samples=issue_tracker.quarantine_samples,
            accepted_quality_avg=accepted_quality_avg,
            quarantine_quality_avg=quarantine_quality_avg,
            pages_processed=pages_processed or 0,
            pages_total=pages_total or 0,
            ext=ext,
        )
        if report_path:
            result_summary["log"].append(f"Relatório detalhado: {report_path}")

        return {
            "final_status": final_status,
            "result_summary": result_summary,
            "created_count": created_count,
            "updated_count": updated_count,
            "errors_count": errors_count,
            "ignored_count": ignored_count,
            "quarantine_count": quarantine_count,
            "top_reasons": top_reasons,
            "top_ignored_reasons": top_ignored_reasons,
            "top_quarantine_reasons": top_quarantine_reasons,
            "accepted_quality_avg": accepted_quality_avg,
            "quarantine_quality_avg": quarantine_quality_avg,
            "report_path": report_path,
        }
