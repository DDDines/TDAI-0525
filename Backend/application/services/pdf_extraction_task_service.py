"""Module pdf extraction task service.

Contains backend logic related to pdf extraction task service and documents its role in the OOP architecture.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from sqlalchemy.orm import Session

from Backend.core.config import settings
from Backend.infrastructure.repositories.catalog_import_file_repository import (
    CatalogImportFileRepository,
)
from Backend.application.services.service_container import SessionProviderPort

logger = logging.getLogger(__name__)


class PdfExtractionTaskService:
    """Service OO para extracao de pagina PDF em processamento de background."""

    def __init__(
        self,
        *,
        session_provider: SessionProviderPort,
        catalog_import_file_repository_factory: Callable[[Session], CatalogImportFileRepository] = CatalogImportFileRepository,
        file_processing_service: Any,
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._session_provider = session_provider
        self._catalog_import_file_repository_factory = catalog_import_file_repository_factory
        self._file_processing_service = file_processing_service

    def _resolve_catalog_file_path(self, stored_filename: str) -> Path:
        """Run resolve catalog file path in this workflow."""
        file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / stored_filename
        if file_path.is_absolute():
            return file_path
        return (
            Path(__file__).resolve().parents[2]
            / "static"
            / "uploads"
            / "catalogs"
            / stored_filename
        )

    def process_pdf_extraction_task(
        self,
        *,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        """Process pdf extraction task for this workflow."""
        _ = db_url
        session = self._session_provider.open_session()
        catalog_file_repo = self._catalog_import_file_repository_factory(session)
        job = None
        try:
            job = catalog_file_repo.get_catalog_file(file_id=import_job_id)
            if not job:
                logger.error("CatalogImportFile %s not found", import_job_id)
                return
            job.status = "PROCESSING"
            catalog_file_repo.update_catalog_file(catalog_file=job)
            file_path = self._resolve_catalog_file_path(job.stored_filename)
            if not file_path.exists():
                raise FileNotFoundError(str(file_path))
            result = self._file_processing_service.extract_data_from_single_page(
                str(file_path),
                page_number,
            )
            job.resultado_json = result
            job.status = "COMPLETED"
            catalog_file_repo.update_catalog_file(catalog_file=job)
        except Exception as exc:
            logger.exception("Failed to process PDF extraction job")
            if job:
                job.status = "FAILED"
                job.result_summary = {"error": str(exc)}
                catalog_file_repo.update_catalog_file(catalog_file=job)
        finally:
            session.close()
