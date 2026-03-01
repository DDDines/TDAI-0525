from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from fastapi.responses import JSONResponse


class CatalogImportStatusService:
    """Encapsula leitura de status/resultado da importacao de catalogo."""

    _TERMINAL_STATUSES = {"IMPORTED", "PARTIAL", "DONE", "FAILED"}

    def __init__(
        self,
        *,
        models: Any,
        catalog_file_repository: Any | None = None,
    ) -> None:
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._catalog_file_repository = catalog_file_repository

    def _resolve_catalog_file_repo(
        self,
        *,
        catalog_file_repo: Any | None = None,
    ) -> Any:
        if catalog_file_repo is not None:
            return catalog_file_repo
        if self._catalog_file_repository is None:
            raise ValueError("catalog_file_repo is required")
        if isinstance(self._catalog_file_repository, type):
            raise ValueError("catalog_file_repo instance is required")
        return self._catalog_file_repository

    def get_record_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
        catalog_file_repo: Any | None = None,
    ) -> Any:
        repo = self._resolve_catalog_file_repo(
            catalog_file_repo=catalog_file_repo,
        )
        record = repo.get_catalog_file_for_user(
            file_id=file_id,
            user_id=user_id,
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
