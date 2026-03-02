"""Fornecedor import job service.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException


class FornecedorImportJobService:
    """Coordena leitura e commit de jobs de importacao via repositories OO."""

    def __init__(
        self,
        *,
        session_provider: Any,
        import_job_repository_factory: Any,
        produto_repository_factory: Any,
        produto_create_schema: Any,
    ) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._session_provider = session_provider
        self._import_job_repository_factory = import_job_repository_factory
        self._produto_repository_factory = produto_repository_factory
        self._produto_create_schema = produto_create_schema

    def _import_job_repo(self, session: Any) -> Any:
        """Process Import job repo."""
        return self._import_job_repository_factory(session)

    def _produto_repo(self, session: Any) -> Any:
        """Process Produto repo."""
        return self._produto_repository_factory(session)

    def get_job_for_user_or_404(self, *, job_id: int, user_id: int) -> Any:
        """Return Job for user or 404."""
        if self._session_provider is None:
            raise ValueError("session_provider is required for FornecedorImportJobService")
        session = self._session_provider.open_session()
        try:
            import_job_repo = self._import_job_repo(session)
            job = import_job_repo.get_import_job(job_id=job_id)
            if not job or job.user_id != user_id:
                raise HTTPException(status_code=404, detail="Job nao encontrado")
            return job
        finally:
            session.close()

    def build_review_payload(self, *, job: Any) -> Any:
        """Build review payload."""
        return job.result_summary or {}

    def schedule_commit(
        self,
        *,
        background_tasks: Any,
        job_id: int,
        user_id: int,
    ) -> None:
        """Process Schedule commit."""
        background_tasks.add_task(
            self.commit_job_task,
            job_id=job_id,
            user_id=user_id,
        )

    def commit_job_task(self, *, job_id: int, user_id: int) -> None:
        """Process Commit job task."""
        if self._session_provider is None:
            raise ValueError("session_provider is required for FornecedorImportJobService")
        session = self._session_provider.open_session()
        try:
            import_job_repo = self._import_job_repo(session)
            produto_repo = self._produto_repo(session)
            job = import_job_repo.get_import_job(job_id=job_id)
            if not job:
                return
            for prod_data in self._iter_summary_rows(job.result_summary):
                try:
                    produto_schema = self._produto_create_schema(**prod_data)
                except Exception:
                    continue
                produto_repo.get_or_create_produto(produto=produto_schema, user_id=user_id)
            import_job_repo.update_job_status(job=job, status="COMPLETED")
        finally:
            session.close()

    @staticmethod
    def _iter_summary_rows(summary: Any) -> Iterable[dict[str, Any]]:
        """Process Iter summary rows."""
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
