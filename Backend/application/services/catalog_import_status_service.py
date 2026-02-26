from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class CatalogImportStatusService:
    """Encapsula leitura de status/resultado da importacao de catalogo."""

    _TERMINAL_STATUSES = {"IMPORTED", "PARTIAL", "DONE", "FAILED"}

    def __init__(self, *, models: Any) -> None:
        self._models = models

    def get_record_or_404(self, *, db: Any, file_id: int, user_id: int) -> Any:
        record = (
            db.query(self._models.CatalogImportFile)
            .filter_by(id=file_id, user_id=user_id)
            .first()
        )
        if not record:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return record

    def build_simple_status(self, *, record: Any) -> dict[str, Any]:
        record_status = record.status or "PROCESSING"
        if record_status in {"IMPORTED", "DONE"}:
            status_value = "DONE"
        elif record_status == "PARTIAL":
            status_value = "PARTIAL"
        elif record_status == "FAILED":
            status_value = "FAILED"
        else:
            status_value = "PROCESSING"

        total_pages = record.total_pages or 0
        return {
            "status": status_value,
            "total_pages": total_pages,
            "pages_total": total_pages,
            "pages_processed": record.pages_processed or 0,
            "result_ready": bool(record_status in self._TERMINAL_STATUSES and record.result_summary),
        }

    def build_result_response(self, *, record: Any) -> Any:
        record_status = record.status or "PROCESSING"
        terminal_status = record_status in self._TERMINAL_STATUSES
        if not terminal_status or not record.result_summary:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={
                    "ready": False,
                    "status": record_status,
                    "detail": "Resultados ainda nao disponiveis",
                },
            )
        return record.result_summary
