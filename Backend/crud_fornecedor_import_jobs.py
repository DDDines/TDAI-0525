import logging
from typing import Optional

from sqlalchemy.orm import Session

from Backend import models

logger = logging.getLogger(__name__)


class _FornecedorImportJobWorkflow:
    def __init__(
        self,
        runtime: Optional["_FornecedorImportJobRuntime"] = None,
    ) -> None:
        self._runtime = runtime or _FornecedorImportJobRuntime()

    def create_import_job(
        self,
        db: Session,
        user_id: int,
        result_summary: dict,
    ) -> models.FornecedorImportJob:
        return self._runtime.create_import_job(
            db=db,
            user_id=user_id,
            result_summary=result_summary,
        )

    def get_import_job(
        self,
        db: Session,
        job_id: int,
    ) -> Optional[models.FornecedorImportJob]:
        return self._runtime.get_import_job(db=db, job_id=job_id)

    def update_job_status(
        self,
        db: Session,
        job: models.FornecedorImportJob,
        status: str,
    ) -> models.FornecedorImportJob:
        return self._runtime.update_job_status(
            db=db,
            job=job,
            status=status,
        )


class _FornecedorImportJobRuntime:
    def create_import_job(
        self,
        db: Session,
        user_id: int,
        result_summary: dict,
    ) -> models.FornecedorImportJob:
        job = models.FornecedorImportJob(user_id=user_id, result_summary=result_summary)
        db.add(job)
        db.commit()
        db.refresh(job)
        return job

    def get_import_job(
        self,
        db: Session,
        job_id: int,
    ) -> Optional[models.FornecedorImportJob]:
        return (
            db.query(models.FornecedorImportJob)
            .filter(models.FornecedorImportJob.id == job_id)
            .first()
        )

    def update_job_status(
        self,
        db: Session,
        job: models.FornecedorImportJob,
        status: str,
    ) -> models.FornecedorImportJob:
        job.status = status
        db.add(job)
        db.commit()
        db.refresh(job)
        return job


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




