from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import (
    call_repository_method,
)


class FornecedorImportTrackingService:
    """Centraliza leitura/schedule de status de importacao no fluxo de fornecedores."""

    def __init__(
        self,
        *,
        models: Any,
        process_pdf_extraction_task: Any,
        catalog_file_repository: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        if catalog_file_repository is None:
            catalog_file_repository = legacy_kwargs.pop("catalog_file_repository", None)
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._process_pdf_extraction_task = process_pdf_extraction_task
        self._catalog_file_repository = catalog_file_repository

    def get_catalog_record_or_404(
        self,
        *,
        catalog_file_repo: Any,
        file_id: int,
        user_id: int,
        not_found_detail: str,
    ) -> Any:
        record = call_repository_method(
            catalog_file_repo,
            "get_catalog_file_for_user",
            db=getattr(catalog_file_repo, "_db", None),
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail=not_found_detail)
        return record

    @staticmethod
    def build_progress_payload(*, record: Any) -> dict[str, Any]:
        return {
            "status": record.status,
            "progress": record.pages_processed,
            "pages_processed": record.pages_processed,
            "total_pages": record.total_pages or 0,
        }

    def schedule_page_extraction(
        self,
        *,
        background_tasks: Any,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        background_tasks.add_task(
            self._process_pdf_extraction_task,
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )

    @staticmethod
    def build_import_job_status_payload(*, record: Any) -> dict[str, Any]:
        response = {"status": record.status}
        if record.status == "COMPLETED":
            response["resultado_json"] = record.resultado_json
        return response
