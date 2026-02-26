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
        reasons = Counter(
            self._extract_import_error_reason(err)
            for err in self.errors
            if isinstance(err, dict)
        )
        return reasons.most_common(limit)

    def top_ignored_reasons(self, limit: int = 10) -> List[Tuple[str, int]]:
        return self.ignored_reason_counter.most_common(limit)

    def top_quarantine_reasons(self, limit: int = 10) -> List[Tuple[str, int]]:
        return self.quarantine_reason_counter.most_common(limit)


class CatalogImportQualityAccumulator:
    """Agrega scores de qualidade para estatísticas finais."""

    def __init__(self) -> None:
        self.accepted_scores: List[int] = []
        self.quarantine_scores: List[int] = []

    def add_accepted(self, score: Any) -> None:
        if isinstance(score, (int, float)):
            self.accepted_scores.append(int(score))

    def add_quarantine(self, score: Any) -> None:
        if isinstance(score, (int, float)):
            self.quarantine_scores.append(int(score))

    @staticmethod
    def _avg(values: List[int]) -> Optional[float]:
        return round(sum(values) / len(values), 2) if values else None

    @property
    def accepted_avg(self) -> Optional[float]:
        return self._avg(self.accepted_scores)

    @property
    def quarantine_avg(self) -> Optional[float]:
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

    @staticmethod
    def mark_processing(*, db: Any, catalog_file: Any, fornecedor_id: int) -> None:
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        db.commit()

    @staticmethod
    def mark_file_missing(
        *,
        db: Any,
        catalog_file: Any,
        file_id: int,
        stored_filename: str,
    ) -> None:
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
        db.commit()

    @staticmethod
    def initialize_pages(*, db: Any, catalog_file: Any, total_pages: int) -> None:
        catalog_file.total_pages = total_pages
        catalog_file.pages_processed = 0
        db.commit()

    @staticmethod
    def increment_page(*, db: Any, catalog_file: Any) -> None:
        catalog_file.pages_processed = (catalog_file.pages_processed or 0) + 1
        db.commit()

    @staticmethod
    def mark_final(
        *,
        db: Any,
        catalog_file: Any,
        final_status: str,
        result_summary: Dict[str, Any],
    ) -> None:
        catalog_file.status = final_status
        catalog_file.result_summary = result_summary
        db.add(catalog_file)
        db.commit()

    @staticmethod
    def mark_failure_with_exception(
        *,
        db: Any,
        catalog_file: Any,
        file_id: int,
        error: Exception,
    ) -> None:
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
        db.commit()


class CatalogImportAuditWriter:
    """Registra auditoria de criacao dos produtos em lote."""

    def __init__(self, *, models: Any) -> None:
        self._models = models

    def register_creation(self, *, db: Any, user_id: int, produtos_criados: List[Any]) -> None:
        for db_produto in produtos_criados:
            db.add(
                self._models.RegistroUsoIA(
                    user_id=user_id,
                    produto_id=db_produto.id,
                    tipo_acao=self._models.TipoAcaoEnum.CRIACAO_PRODUTO,
                    creditos_consumidos=0,
                )
            )
            db.add(
                self._models.RegistroHistorico(
                    user_id=user_id,
                    entidade="Produto",
                    acao=self._models.TipoAcaoSistemaEnum.CRIACAO,
                    entity_id=db_produto.id,
                )
            )
