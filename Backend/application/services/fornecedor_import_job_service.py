"""Document fornecedor import job service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import HTTPException

from Backend.application.services.async_job_dispatcher import AsyncJobDispatcher


class FornecedorImportJobService:
    """Coordena leitura e commit de jobs de importacao via repositories OO."""

    def __init__(
        self,
        *,
        session_provider: Any,
        import_job_repository_factory: Any,
        produto_repository_factory: Any,
        produto_create_schema: Any,
        dispatcher_cls: Any = AsyncJobDispatcher,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedor Import Job Service."""
        self._session_provider = session_provider
        self._import_job_repository_factory = import_job_repository_factory
        self._produto_repository_factory = produto_repository_factory
        self._produto_create_schema = produto_create_schema
        self._dispatcher = dispatcher_cls()

    def _import_job_repo(self, session: Any) -> Any:
        """Execute import job repo as part of this module workflow."""
        return self._import_job_repository_factory(session)

    def _produto_repo(self, session: Any) -> Any:
        """Execute produto repo as part of this module workflow."""
        return self._produto_repository_factory(session)

    def get_job_for_user_or_404(self, *, job_id: int, user_id: int) -> Any:
        """Retrieve job for user or 404 using the current service dependencies."""
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
        """Build review payload from current inputs and configuration."""
        return job.result_summary or {}

    def schedule_commit(
        self,
        *,
        background_tasks: Any,
        job_id: int,
        user_id: int,
    ) -> None:
        """Execute schedule commit as part of this module workflow."""
        self._dispatcher.dispatch_named_or_background(
            background_tasks=background_tasks,
            task_name="fornecedor_import.commit",
            task_kwargs={
                "job_id": job_id,
                "user_id": user_id,
            },
            fallback_callable=self.commit_job_task,
        )

    def commit_job_task(self, *, job_id: int, user_id: int) -> None:
        """Execute commit job task as part of this module workflow."""
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
        """Execute iter summary rows as part of this module workflow."""
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
