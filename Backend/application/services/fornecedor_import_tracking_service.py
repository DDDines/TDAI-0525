"""Document fornecedor import tracking service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException

from Backend.application.services.async_job_dispatcher import AsyncJobDispatcher


class FornecedorImportTrackingService:
    """Centraliza leitura/schedule de status de importacao no fluxo de fornecedores."""

    def __init__(
        self,
        *,
        models: Any,
        process_pdf_extraction_task: Any,
        catalog_file_repository: Any,
        dispatcher_cls: Any = AsyncJobDispatcher,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedor Import Tracking Service."""
        self._models = models
        self._process_pdf_extraction_task = process_pdf_extraction_task
        self._catalog_file_repository = catalog_file_repository
        self._dispatcher = dispatcher_cls()

    def get_catalog_record_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
        not_found_detail: str,
    ) -> Any:
        """Retrieve catalog record or 404 using the current service dependencies."""
        record = self._catalog_file_repository.get_catalog_file_for_user(
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail=not_found_detail)
        return record

    @staticmethod
    def build_progress_payload(*, record: Any) -> dict[str, Any]:
        """Build progress payload from current inputs and configuration."""
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
    ) -> None:
        """Execute schedule page extraction as part of this module workflow."""
        self._dispatcher.dispatch_named_or_background(
            background_tasks=background_tasks,
            task_name="pdf_extraction.page",
            task_kwargs={
                "import_job_id": import_job_id,
                "page_number": page_number,
            },
            fallback_callable=self._process_pdf_extraction_task,
        )

    @staticmethod
    def build_import_job_status_payload(*, record: Any) -> dict[str, Any]:
        """Build import job status payload from current inputs and configuration."""
        response = {"status": record.status}
        if record.status == "COMPLETED":
            response["resultado_json"] = record.resultado_json
        return response
