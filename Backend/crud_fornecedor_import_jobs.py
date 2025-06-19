import logging
from sqlalchemy.orm import Session
from typing import Optional

from Backend import models

logger = logging.getLogger(__name__)


def create_import_job(
    db: Session, user_id: int, result_summary: dict
) -> models.FornecedorImportJob:
    job = models.FornecedorImportJob(user_id=user_id, result_summary=result_summary)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def get_import_job(db: Session, job_id: int) -> Optional[models.FornecedorImportJob]:
    return (
        db.query(models.FornecedorImportJob)
        .filter(models.FornecedorImportJob.id == job_id)
        .first()
    )


def update_job_status(
    db: Session, job: models.FornecedorImportJob, status: str
) -> models.FornecedorImportJob:
    job.status = status
    db.add(job)
    db.commit()
    db.refresh(job)
    return job
