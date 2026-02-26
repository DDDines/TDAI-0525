from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json


class CatalogImportDiagnosticsService:
    """Servicos de diagnostico da importacao (paths e relatorios detalhados)."""

    def __init__(
        self,
        *,
        catalog_log_dir: Path,
        logger: Any,
        sanitization_service: Any,
    ) -> None:
        self._catalog_log_dir = Path(catalog_log_dir)
        self._logger = logger
        self._sanitization_service = sanitization_service
        self._catalog_log_dir.mkdir(parents=True, exist_ok=True)

    def resolve_storage_path(self, path_value: Union[str, Path]) -> Path:
        """Resolve caminhos relativos de storage sem duplicar prefixo Backend."""
        path_obj = Path(path_value)
        if path_obj.is_absolute():
            return path_obj

        backend_root = Path(__file__).resolve().parents[2]
        project_root = backend_root.parent
        if path_obj.parts and path_obj.parts[0].lower() == "backend":
            return project_root / path_obj
        return backend_root / path_obj

    def write_catalog_import_report(
        self,
        *,
        file_id: int,
        status: str,
        created_count: int,
        updated_count: int,
        errors: List[Dict[str, Any]],
        ignored_count: int = 0,
        ignored_reasons: Optional[List[tuple[str, int]]] = None,
        ignored_samples: Optional[List[Dict[str, Any]]] = None,
        quarantine_count: int = 0,
        quarantine_reasons: Optional[List[tuple[str, int]]] = None,
        quarantine_samples: Optional[List[Dict[str, Any]]] = None,
        accepted_quality_avg: Optional[float] = None,
        quarantine_quality_avg: Optional[float] = None,
        pages_processed: int = 0,
        pages_total: int = 0,
        ext: str = "",
    ) -> Optional[Path]:
        """Persiste relatorio detalhado da importacao para diagnostico posterior."""
        try:
            report_dir = self._catalog_log_dir / "import_jobs"
            report_dir.mkdir(parents=True, exist_ok=True)
            reasons = Counter(
                self._sanitization_service.extract_import_error_reason(err)
                for err in errors
                if isinstance(err, dict)
            )
            payload = {
                "file_id": file_id,
                "status": status,
                "stats": {
                    "created": created_count,
                    "updated": updated_count,
                    "errors": len(errors),
                    "ignored_non_critical": ignored_count,
                    "quarantine_non_critical": quarantine_count,
                    "quality_score_avg_accepted": accepted_quality_avg,
                    "quality_score_avg_quarantine": quarantine_quality_avg,
                    "pages_processed": pages_processed,
                    "pages_total": pages_total,
                    "ext": ext,
                },
                "error_reasons_top": reasons.most_common(30),
                "ignored_reasons_top": ignored_reasons or [],
                "ignored_samples": ignored_samples or [],
                "quarantine_reasons_top": quarantine_reasons or [],
                "quarantine_samples": quarantine_samples or [],
                "errors": errors,
            }
            report_path = report_dir / f"import_{file_id}.json"
            report_path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            return report_path
        except Exception as report_err:
            self._logger.warning(
                "falha ao salvar relatorio detalhado file_id=%s erro=%s",
                file_id,
                report_err,
            )
            return None
