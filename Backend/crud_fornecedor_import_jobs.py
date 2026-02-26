import logging
from typing import Optional

from sqlalchemy.orm import Session

from Backend import models

logger = logging.getLogger(__name__)


def _create_import_job_impl(
    db: Session,
    user_id: int,
    result_summary: dict,
) -> models.FornecedorImportJob:
    job = models.FornecedorImportJob(user_id=user_id, result_summary=result_summary)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _get_import_job_impl(
    db: Session,
    job_id: int,
) -> Optional[models.FornecedorImportJob]:
    return (
        db.query(models.FornecedorImportJob)
        .filter(models.FornecedorImportJob.id == job_id)
        .first()
    )


def _update_job_status_impl(
    db: Session,
    job: models.FornecedorImportJob,
    status: str,
) -> models.FornecedorImportJob:
    job.status = status
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


class _FornecedorImportJobWorkflow:
    def create_import_job(
        self,
        db: Session,
        user_id: int,
        result_summary: dict,
    ) -> models.FornecedorImportJob:
        return _create_import_job_impl(db=db, user_id=user_id, result_summary=result_summary)

    def get_import_job(
        self,
        db: Session,
        job_id: int,
    ) -> Optional[models.FornecedorImportJob]:
        return _get_import_job_impl(db=db, job_id=job_id)

    def update_job_status(
        self,
        db: Session,
        job: models.FornecedorImportJob,
        status: str,
    ) -> models.FornecedorImportJob:
        return _update_job_status_impl(db=db, job=job, status=status)


_fornecedor_import_job_workflow = _FornecedorImportJobWorkflow()


def create_import_job(
    db: Session,
    user_id: int,
    result_summary: dict,
) -> models.FornecedorImportJob:
    return _fornecedor_import_job_workflow.create_import_job(
        db=db,
        user_id=user_id,
        result_summary=result_summary,
    )


def get_import_job(db: Session, job_id: int) -> Optional[models.FornecedorImportJob]:
    return _fornecedor_import_job_workflow.get_import_job(db=db, job_id=job_id)


def update_job_status(
    db: Session,
    job: models.FornecedorImportJob,
    status: str,
) -> models.FornecedorImportJob:
    return _fornecedor_import_job_workflow.update_job_status(
        db=db,
        job=job,
        status=status,
    )


class FornecedorImportJobLegacyService:
    def create_import_job(self, *args, **kwargs):
        return create_import_job(*args, **kwargs)

    def get_import_job(self, *args, **kwargs):
        return get_import_job(*args, **kwargs)

    def update_job_status(self, *args, **kwargs):
        return update_job_status(*args, **kwargs)


fornecedor_import_job_legacy_service = FornecedorImportJobLegacyService()
