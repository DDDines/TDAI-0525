"""Module fornecedor import job repository.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from Backend import models


class FornecedorImportJobRepository:
    """Repository OO para jobs de importacao de fornecedor."""

    def __init__(self, db: Session) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._db = db

    def create_import_job(
        self,
        *,
        user_id: int,
        result_summary: Optional[dict] = None,
    ) -> models.FornecedorImportJob:
        """Execute create_import_job.

        This callable is documented to make behavior explicit for readers.
        """
        job = models.FornecedorImportJob(
            user_id=user_id,
            result_summary=result_summary or {},
        )
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job

    def get_import_job(
        self,
        *,
        job_id: int,
    ) -> Optional[models.FornecedorImportJob]:
        """Execute get_import_job.

        This callable is documented to make behavior explicit for readers.
        """
        return (
            self._db.query(models.FornecedorImportJob)
            .filter(models.FornecedorImportJob.id == job_id)
            .first()
        )

    def update_job_status(
        self,
        *,
        job: models.FornecedorImportJob,
        status: str,
    ) -> models.FornecedorImportJob:
        """Execute update_job_status.

        This callable is documented to make behavior explicit for readers.
        """
        job.status = status
        self._db.add(job)
        self._db.commit()
        self._db.refresh(job)
        return job
