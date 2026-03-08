"""Celery tasks wrapping the heavy background runners."""

from __future__ import annotations

import asyncio
from typing import Any

from Backend.application.services.background_runtime_factories import (
    build_catalog_import_task_runner,
    build_fornecedor_import_job_service,
    build_generation_task_service,
    build_pdf_region_extractor,
    build_web_enrichment_task_runner,
    resolve_generation_callable,
)
from Backend.celery_app import celery_app
from Backend.tasks import TaskWorkflow


class CeleryTaskRuntime:
    """Implement Celery-backed wrappers for heavy background flows."""

    @staticmethod
    def _run_async(awaitable: Any) -> Any:
        """Execute awaitables from Celery's synchronous worker context."""
        return asyncio.run(awaitable)

    @staticmethod
    def run_web_enrichment_start_task(
        *,
        produto_id: int,
        user_id: int,
        termos_busca_override: str | None = None,
    ) -> None:
        """Execute the web enrichment pipeline through Celery."""
        runner = build_web_enrichment_task_runner()
        CeleryTaskRuntime._run_async(
            runner.execute(
                produto_id=produto_id,
                user_id=user_id,
                termos_busca_override=termos_busca_override,
            )
        )

    @staticmethod
    def run_catalog_import_finalize_task(
        *,
        file_id: int,
        user_id: int,
        product_type_id: int | None,
        fornecedor_id: int,
        mapping: dict[str, str] | None = None,
        pages: list[int] | None = None,
        region: list[float] | None = None,
        extraction_mode: str = "ocr",
    ) -> None:
        """Execute catalog import finalization through Celery."""
        runner = build_catalog_import_task_runner()
        CeleryTaskRuntime._run_async(
            runner.execute(
                file_id=file_id,
                user_id=user_id,
                product_type_id=product_type_id,
                fornecedor_id=fornecedor_id,
                mapping=mapping,
                pages=pages,
                region=region,
                extraction_mode=extraction_mode,
            )
        )

    @staticmethod
    def run_generation_task(
        *,
        user_id: int,
        produto_id: int,
        tipo_geracao_principal: str,
        generation_provider_key: str,
        num_titulos: int | None = None,
        tamanho_palavras: int | None = None,
        template_titulo: str | None = None,
        template_descricao: str | None = None,
    ) -> None:
        """Execute generation tasks through Celery using provider keys."""
        generation_service = build_generation_task_service()
        generation_callable = resolve_generation_callable(generation_provider_key)
        CeleryTaskRuntime._run_async(
            generation_service.run_generation_task(
                user_id=user_id,
                produto_id=produto_id,
                tipo_geracao_principal=tipo_geracao_principal,
                funcao_geracao_ia_no_servico=generation_callable,
                num_titulos=num_titulos,
                tamanho_palavras=tamanho_palavras,
                template_titulo=template_titulo,
                template_descricao=template_descricao,
            )
        )

    @staticmethod
    def run_pdf_page_extraction_task(*, import_job_id: int, page_number: int) -> None:
        """Execute tracked single-page PDF extraction through Celery."""
        TaskWorkflow().process_pdf_extraction_task(
            import_job_id=import_job_id,
            page_number=page_number,
        )

    @staticmethod
    def run_pdf_region_extraction_task(
        *,
        file_path: str,
        page_number: int,
        region: list[float] | None = None,
    ) -> None:
        """Execute raw PDF region extraction through Celery."""
        extractor = build_pdf_region_extractor()
        extractor(
            file_path=file_path,
            page_number=page_number,
            region=region,
        )

    @staticmethod
    def run_fornecedor_import_commit_task(*, job_id: int, user_id: int) -> None:
        """Execute import commit review task through Celery."""
        service = build_fornecedor_import_job_service()
        service.commit_job_task(
            job_id=job_id,
            user_id=user_id,
        )

    @staticmethod
    def resolve_task(task_name: str) -> Any:
        """Resolve a Celery task by name from the application registry."""
        task = celery_app.tasks.get(task_name)
        if task is None:
            raise LookupError(f"Celery task not registered: {task_name}")
        return task


run_web_enrichment_start_task = celery_app.task(name="web_enrichment.start")(CeleryTaskRuntime.run_web_enrichment_start_task)
run_catalog_import_finalize_task = celery_app.task(name="catalog_import.finalize")(CeleryTaskRuntime.run_catalog_import_finalize_task)
run_generation_task = celery_app.task(name="generation.run")(CeleryTaskRuntime.run_generation_task)
run_pdf_page_extraction_task = celery_app.task(name="pdf_extraction.page")(CeleryTaskRuntime.run_pdf_page_extraction_task)
run_pdf_region_extraction_task = celery_app.task(name="pdf_extraction.region")(CeleryTaskRuntime.run_pdf_region_extraction_task)
run_fornecedor_import_commit_task = celery_app.task(name="fornecedor_import.commit")(CeleryTaskRuntime.run_fornecedor_import_commit_task)
resolve_task = CeleryTaskRuntime.resolve_task
