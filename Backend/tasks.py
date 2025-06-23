import logging
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.core.config import settings
from Backend import models
from Backend.services import file_processing_service

logger = logging.getLogger(__name__)


def process_pdf_extraction_task(import_job_id: int, page_number: int, db_url: str) -> None:
    """Processa extração de dados de uma página de PDF em segundo plano."""
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    job = None
    try:
        job = db.query(models.CatalogImportFile).filter(models.CatalogImportFile.id == import_job_id).first()
        if not job:
            logger.error("CatalogImportFile %s not found", import_job_id)
            return
        job.status = "PROCESSING"
        db.commit()

        file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / job.stored_filename
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parent / "static" / "uploads" / "catalogs" / job.stored_filename
        if not file_path.exists():
            raise FileNotFoundError(str(file_path))

        result = file_processing_service.extract_data_from_single_page(str(file_path), page_number)
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
