import logging
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend import models
from Backend.application.services.service_container import service_container
from Backend.core.config import settings

logger = logging.getLogger(__name__)
file_processing_service = service_container.file_processing


def _process_pdf_extraction_task_impl(import_job_id: int, page_number: int, db_url: str) -> None:
    engine = create_engine(db_url)
    session_local = sessionmaker(bind=engine)
    db = session_local()
    job = None
    try:
        job = (
            db.query(models.CatalogImportFile)
            .filter(models.CatalogImportFile.id == import_job_id)
            .first()
        )
        if not job:
            logger.error("CatalogImportFile %s not found", import_job_id)
            return
        job.status = "PROCESSING"
        db.commit()

        file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / job.stored_filename
        if not file_path.is_absolute():
            file_path = (
                Path(__file__).resolve().parent
                / "static"
                / "uploads"
                / "catalogs"
                / job.stored_filename
            )
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        result = file_processing_service.extract_data_from_single_page(
            str(file_path),
            page_number,
        )
        job.resultado_json = result
        job.status = "COMPLETED"
        db.commit()
    except Exception as exc:
        logger.exception("Failed to process PDF extraction job")
        if job:
            job.status = "FAILED"
            job.result_summary = {"error": str(exc)}
            db.commit()
    finally:
        db.close()


class _TaskWorkflow:
    def process_pdf_extraction_task(
        self,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ) -> None:
        _process_pdf_extraction_task_impl(
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )


_task_workflow = _TaskWorkflow()


def process_pdf_extraction_task(import_job_id: int, page_number: int, db_url: str) -> None:
    _task_workflow.process_pdf_extraction_task(
        import_job_id=import_job_id,
        page_number=page_number,
        db_url=db_url,
    )


class TaskLegacyService:
    def process_pdf_extraction_task(self, *args, **kwargs):
        return process_pdf_extraction_task(*args, **kwargs)


task_legacy_service = TaskLegacyService()
