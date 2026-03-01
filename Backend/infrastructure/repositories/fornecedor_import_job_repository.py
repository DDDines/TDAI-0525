from __future__ import annotations

from typing import Any, Optional

from sqlalchemy.orm import Session

from Backend import models


class FornecedorImportJobRuntime:
    def create_import_job(
        self,
        *,
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
        *,
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
        *,
        db: Session,
        job: models.FornecedorImportJob,
        status: str,
    ) -> models.FornecedorImportJob:
        job.status = status
        db.add(job)
        db.commit()
        db.refresh(job)
        return job


class FornecedorImportJobRepository:
    """Repository OO para jobs de importacao de fornecedor.

    Suporta uso request-scoped (Session no __init__) e assinatura legada
    com `db` explicito para compatibilidade de transicao.
    """

    def __init__(
        self,
        db: Optional[Session] = None,
        *,
        runtime: Optional[Any] = None,
    ) -> None:
        self._db = db
        self._runtime = runtime or FornecedorImportJobRuntime()

    def _resolve_db(self, db: Optional[Session]) -> Session:
        active_db = db or self._db
        if active_db is None:
            raise ValueError("Session obrigatoria para operacoes de FornecedorImportJobRepository")
        return active_db

    def create_import_job(
        self,
        db: Optional[Session] = None,
        user_id: Optional[int] = None,
        result_summary: Optional[dict] = None,
    ) -> models.FornecedorImportJob:
        if user_id is None:
            raise ValueError("user_id obrigatorio")
        summary = result_summary or {}
        return self._runtime.create_import_job(
            db=self._resolve_db(db),
            user_id=user_id,
            result_summary=summary,
        )

    def get_import_job(
        self,
        db: Optional[Session] = None,
        job_id: Optional[int] = None,
    ) -> Optional[models.FornecedorImportJob]:
        if job_id is None:
            raise ValueError("job_id obrigatorio")
        return self._runtime.get_import_job(
            db=self._resolve_db(db),
            job_id=job_id,
        )

    def update_job_status(
        self,
        db: Optional[Session] = None,
        job: Optional[models.FornecedorImportJob] = None,
        status: Optional[str] = None,
    ) -> models.FornecedorImportJob:
        if job is None:
            raise ValueError("job obrigatorio")
        if not status:
            raise ValueError("status obrigatorio")
        return self._runtime.update_job_status(
            db=self._resolve_db(db),
            job=job,
            status=status,
        )
