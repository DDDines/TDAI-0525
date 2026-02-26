from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker


class FornecedorImportJobService:
    """Coordena leitura e commit de jobs legados de importacao de fornecedor."""

    def __init__(
        self,
        *,
        crud_fornecedor_import_jobs: Any,
        crud_produtos: Any,
        produto_create_schema: Any,
    ) -> None:
        self._crud_fornecedor_import_jobs = crud_fornecedor_import_jobs
        self._crud_produtos = crud_produtos
        self._produto_create_schema = produto_create_schema

    def get_job_for_user_or_404(self, *, db: Any, job_id: int, user_id: int) -> Any:
        job = self._crud_fornecedor_import_jobs.get_import_job(db, job_id)
        if not job or job.user_id != user_id:
            raise HTTPException(status_code=404, detail="Job nao encontrado")
        return job

    def build_review_payload(self, *, job: Any) -> Any:
        return job.result_summary or {}

    def schedule_commit(
        self,
        *,
        background_tasks: Any,
        db: Any,
        job_id: int,
        user_id: int,
    ) -> None:
        db_session_factory = sessionmaker(bind=db.get_bind())
        background_tasks.add_task(
            self.commit_job_task,
            db_session_factory=db_session_factory,
            job_id=job_id,
            user_id=user_id,
        )

    def commit_job_task(self, *, db_session_factory: Any, job_id: int, user_id: int) -> None:
        db = db_session_factory()
        try:
            job = self._crud_fornecedor_import_jobs.get_import_job(db, job_id)
            if not job:
                return
            for prod_data in self._iter_summary_rows(job.result_summary):
                try:
                    produto_schema = self._produto_create_schema(**prod_data)
                except Exception:
                    continue
                self._crud_produtos.get_or_create_produto(db, produto_schema, user_id)
            self._crud_fornecedor_import_jobs.update_job_status(db, job, "COMPLETED")
        finally:
            db.close()

    @staticmethod
    def _iter_summary_rows(summary: Any) -> Iterable[dict[str, Any]]:
        if isinstance(summary, list):
            for item in summary:
                if isinstance(item, dict):
                    yield item
            return
        if isinstance(summary, dict):
            if isinstance(summary.get("produtos"), list):
                for item in summary.get("produtos", []):
                    if isinstance(item, dict):
                        yield item
                return
            if isinstance(summary.get("itens"), list):
                for item in summary.get("itens", []):
                    if isinstance(item, dict):
                        yield item
