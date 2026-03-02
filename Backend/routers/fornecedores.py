"""Camada de transporte HTTP para o dominio 'fornecedores'."""
from collections import Counter
from pathlib import Path
from typing import Any, List, Optional
import time
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session
from Backend import models
from Backend import schemas
from Backend.application.services.fornecedor_catalog_process_service import FornecedorCatalogProcessService
from Backend.application.services.fornecedor_import_job_service import FornecedorImportJobService
from Backend.application.services.fornecedor_import_tracking_service import FornecedorImportTrackingService
from Backend.application.services.fornecedor_management_service import FornecedorManagementService
from Backend.application.services.fornecedor_preview_service import FornecedorPreviewService
from Backend.application.services.catalog_import_diagnostics_service import CatalogImportDiagnosticsService
from Backend.application.services.catalog_import_finalize_service import CatalogImportFinalizeService
from Backend.application.services.catalog_import_quality_service import CatalogImportQualityService
from Backend.application.services.catalog_import_sanitization_service import CatalogImportSanitizationService
from Backend.application.services.catalog_import_start_service import CatalogImportStartService
from Backend.application.services.catalog_import_task_runner import CatalogImportTaskRunner
from Backend.application.services.validator_crew_service import ValidatorCrewService
from Backend.application.services.service_container import DependencyContainer, ServiceContainer, ServiceContainerDependencySupport
from Backend.core.config import settings
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.catalog_import_file_repository import CatalogImportFileRepository
from Backend.infrastructure.repositories.fornecedor_import_job_repository import FornecedorImportJobRepository
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.tasks import TaskWorkflow
from . import auth_utils

class _FornecedoresDependencies:

    """Represent Fornecedores Dependencies and centralize its responsibilities inside this module."""
    @staticmethod
    def _build_fornecedores_service_bundle():
        """Handle Build fornecedores service bundle in this request workflow."""
        return _FornecedoresServiceBundle()

    @staticmethod
    def get_fornecedores_request_service(session: Session):
        """Retrieve fornecedores request service using the current service dependencies."""
        return FornecedoresRequestService(runtime=_FornecedoresServiceGateway(session=session))
logger = get_logger(__name__)
catalog_log_dir = Path(__file__).resolve().parent.parent / 'logs'
catalog_log_dir.mkdir(parents=True, exist_ok=True)
produto_repository = ProductRepository
fornecedor_repository = FornecedorRepository
catalog_file_repository = CatalogImportFileRepository

class _FornecedoresServiceBundle:
    """Componente OO principal '_FornecedoresServiceBundle' do modulo 'fornecedores'."""

    def __init__(self, *, session_provider: Any | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedores Service Bundle."""
        self._service_container = ServiceContainer()
        self._session_provider = (
            session_provider
            or ServiceContainerDependencySupport.get_background_session_provider()
        )
        self.file_processing_service = self._service_container.file_processing
        self.web_data_extractor_service = self._service_container.web_data_extractor
        self.catalog_quality_service = CatalogImportQualityService()
        self.catalog_sanitization_service = CatalogImportSanitizationService(quality_service=self.catalog_quality_service)
        self.catalog_import_diagnostics_service = CatalogImportDiagnosticsService(catalog_log_dir=catalog_log_dir, logger=logger, sanitization_service=self.catalog_sanitization_service)
        self.validator_crew = ValidatorCrewService(logger=logger)
        self.catalog_import_task_runner = CatalogImportTaskRunner(session_provider=self._session_provider, logger=logger, catalog_logger=logger, models=models, schemas=schemas, product_repository_factory=produto_repository, catalog_file_repository_factory=catalog_file_repository, file_processing_service=self.file_processing_service, validator_crew=self.validator_crew, settings=settings, path_cls=Path, time_module=time, counter_cls=Counter, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item, extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason, is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason, normalizar_dados_validados=self.catalog_sanitization_service.normalize_validated_data, sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product, classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality, write_catalog_import_report=self.catalog_import_diagnostics_service.write_catalog_import_report, normalize_import_text=self.catalog_sanitization_service.normalize_import_text)
        self.catalog_import_finalize_service = CatalogImportFinalizeService(
            oop_executor=self.catalog_import_task_runner.execute
        )
        self.catalog_import_start_service = CatalogImportStartService(models=models, fornecedor_repo=fornecedor_repository, catalog_file_repository=catalog_file_repository, settings=settings, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, finalize_service=self.catalog_import_finalize_service)
        self.fornecedor_catalog_process_service = FornecedorCatalogProcessService(models=models, fornecedor_repo=fornecedor_repository, catalog_file_repository=catalog_file_repository, catalog_import_start_service=self.catalog_import_start_service)
        self.fornecedor_import_job_service = FornecedorImportJobService(
            session_provider=self._session_provider,
            import_job_repository_factory=FornecedorImportJobRepository,
            produto_repository_factory=ProductRepository,
            produto_create_schema=schemas.ProdutoCreate,
        )
        self.fornecedor_import_tracking_service = FornecedorImportTrackingService(
            models=models,
            process_pdf_extraction_task=TaskWorkflow().process_pdf_extraction_task,
            catalog_file_repository=catalog_file_repository,
        )
        self.fornecedor_preview_service = FornecedorPreviewService(file_processing_service=self.file_processing_service, web_data_extractor_service=self.web_data_extractor_service, catalog_file_repository=catalog_file_repository)
router = APIRouter(prefix='/fornecedores', tags=['fornecedores'], dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)])

class FornecedoresRequestService:
    """Workflow/escopo request-scoped para o fluxo de 'fornecedores'."""

    def __init__(self, runtime: '_FornecedoresServiceGateway') -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedores Request Service."""
        self._runtime = runtime

    def create_fornecedor(self, fornecedor: schemas.FornecedorCreate, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        """Create fornecedor and return the resulting payload or entity."""
        logger.info('Requisicao para criar fornecedor recebida.')
        return self._runtime.create_fornecedor(fornecedor=fornecedor, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def list_fornecedores_page(self, current_user: models.User, skip: int, limit: int, termo_busca: Optional[str], fornecedor_management_service: FornecedorManagementService) -> schemas.FornecedorPage:
        """Execute list fornecedores page as part of this module workflow."""
        return self._runtime.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca, fornecedor_management_service=fornecedor_management_service)

    def read_fornecedor(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        """Handle Read fornecedor in this request workflow."""
        return self._runtime.resolve_fornecedor_for_user(fornecedor_id=fornecedor_id, current_user=current_user, not_found_detail='Fornecedor nao encontrado ou nao pertence ao usuario', forbidden_detail='Nao autorizado a acessar este fornecedor.', fornecedor_management_service=fornecedor_management_service)

    def update_fornecedor(self, fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        """Update fornecedor and persist the resulting state changes."""
        return self._runtime.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def get_mapping(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> Optional[dict]:
        """Retrieve mapping using the current service dependencies."""
        return self._runtime.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def update_mapping(self, fornecedor_id: int, mapping: Optional[dict], current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        """Update mapping and persist the resulting state changes."""
        return self._runtime.update_mapping(fornecedor_id=fornecedor_id, current_user=current_user, mapping=mapping, fornecedor_management_service=fornecedor_management_service)

    async def preview_pages(self, file: UploadFile):
        """Handle Preview pages in this request workflow."""
        return await self._runtime.preview_pages(file=file)

    async def preview_pdf(self, fornecedor_id: int, file: UploadFile, current_user: models.User, offset: int, limit: int, fornecedor_management_service: FornecedorManagementService) -> schemas.PdfPreviewResponse:
        """Handle Preview pdf in this request workflow."""
        _ = self._runtime.resolve_fornecedor_for_user(fornecedor_id=fornecedor_id, current_user=current_user, not_found_detail='Fornecedor nao encontrado', forbidden_detail='Nao autorizado a acessar este fornecedor.', fornecedor_management_service=fornecedor_management_service)
        return self._runtime.preview_pdf(file=file, fornecedor_id=fornecedor_id, user_id=current_user.id, offset=offset, limit=limit)

    def preview_catalog_from_region(self, preview_request: schemas.CatalogRegionPreviewRequest) -> schemas.CatalogPreview:
        """Handle Preview catalog from region in this request workflow."""
        return self._runtime.preview_catalog_from_region(file_id=preview_request.file_id, page_number=preview_request.page_number, region=preview_request.region)

    def extract_data_from_pdf_bulk(self, background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest):
        """Extract data from pdf bulk."""
        return self._runtime.extract_data_from_pdf_bulk(background_tasks=background_tasks, file_id=request.file_id, region=request.region, pages=request.pages, all_pages=request.all_pages)

    def get_import_progress(self, job_id: int, current_user: models.User) -> dict:
        """Retrieve import progress using the current service dependencies."""
        record = self._runtime.get_catalog_record_or_404(file_id=job_id, user_id=current_user.id, not_found_detail='Importacao nao encontrada')
        return self._runtime.build_progress_payload(record=record)

    async def process_full_catalog(self, background_tasks: BackgroundTasks, file_id: int, fornecedor_id: int, tipo_produto_id: int, start_page: int, region: Optional[List[float]], mapping: Optional[dict], current_user: models.User):
        """Handle full catalog in this request workflow."""
        return await self._runtime.start_full_processing(background_tasks=background_tasks, current_user=current_user, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping)

    def extract_page_data(self, background_tasks: BackgroundTasks, file_id: int, page_number: int, current_user: models.User) -> dict:
        """Execute extract page data as part of this module workflow."""
        record = self._runtime.get_catalog_record_or_404(file_id=file_id, user_id=current_user.id, not_found_detail='Arquivo nao encontrado')
        self._runtime.schedule_page_extraction(background_tasks=background_tasks, import_job_id=record.id, page_number=page_number, db_url=self._runtime.get_database_url())
        return {'job_id': record.id, 'status': 'PROCESSING'}

    def delete_fornecedor(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        """Execute delete fornecedor as part of this module workflow."""
        return self._runtime.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def review_import_job(self, job_id: int, current_user: models.User) -> dict:
        """Handle Review import job in this request workflow."""
        job = self._runtime.get_job_for_user_or_404(job_id=job_id, user_id=current_user.id)
        return self._runtime.build_review_payload(job=job)

    def commit_import_job(self, background_tasks: BackgroundTasks, job_id: int, current_user: models.User) -> dict:
        """Handle Commit import job in this request workflow."""
        _ = self._runtime.get_job_for_user_or_404(job_id=job_id, user_id=current_user.id)
        self._runtime.schedule_commit(background_tasks=background_tasks, job_id=job_id, user_id=current_user.id)
        return {'status': 'PROCESSING', 'job_id': job_id}

    def get_import_job_status(self, job_id: int, current_user: models.User) -> dict:
        """Retrieve import job status using the current service dependencies."""
        record = self._runtime.get_catalog_record_or_404(file_id=job_id, user_id=current_user.id, not_found_detail='Job nao encontrado')
        return self._runtime.build_import_job_status_payload(record=record)

class _FornecedoresServiceGateway:
    """Runtime OO para integrações do router de fornecedores."""

    def __init__(self, *, session: Session, services: Optional[_FornecedoresServiceBundle]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedores Service Gateway."""
        self._session = session
        runtime_session_provider = (
            ServiceContainerDependencySupport.build_background_session_provider_from_session(
                session
            )
        )
        self._services = services or _FornecedoresServiceBundle(
            session_provider=runtime_session_provider
        )
        self._catalog_file_repo = CatalogImportFileRepository(session)
        self._fornecedor_repo = FornecedorRepository(session)
        self._catalog_import_start_service = CatalogImportStartService(
            models=models,
            fornecedor_repo=self._fornecedor_repo,
            catalog_file_repository=self._catalog_file_repo,
            settings=settings,
            resolve_storage_path=self._services.catalog_import_diagnostics_service.resolve_storage_path,
            finalize_service=self._services.catalog_import_finalize_service,
        )
        self._fornecedor_catalog_process_service = FornecedorCatalogProcessService(
            models=models,
            fornecedor_repo=self._fornecedor_repo,
            catalog_file_repository=self._catalog_file_repo,
            catalog_import_start_service=self._catalog_import_start_service,
        )
        self._fornecedor_import_tracking_service = FornecedorImportTrackingService(
            models=models,
            process_pdf_extraction_task=TaskWorkflow().process_pdf_extraction_task,
            catalog_file_repository=self._catalog_file_repo,
        )
        self._fornecedor_preview_service = FornecedorPreviewService(
            file_processing_service=self._services.file_processing_service,
            web_data_extractor_service=self._services.web_data_extractor_service,
            catalog_file_repository=self._catalog_file_repo,
        )
        self._fornecedor_import_job_service = self._services.fornecedor_import_job_service

    def create_fornecedor(
        self,
        *,
        fornecedor: schemas.FornecedorCreate,
        current_user: models.User,
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Create fornecedor and return the resulting payload or entity."""
        return fornecedor_management_service.create_fornecedor(
            fornecedor=fornecedor,
            current_user=current_user,
        )

    def list_fornecedores_page(
        self,
        *,
        current_user: models.User,
        skip: int,
        limit: int,
        termo_busca: Optional[str],
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Execute list fornecedores page as part of this module workflow."""
        return fornecedor_management_service.list_fornecedores_page(
            current_user=current_user,
            skip=skip,
            limit=limit,
            termo_busca=termo_busca,
        )

    def resolve_fornecedor_for_user(
        self,
        *,
        fornecedor_id: int,
        current_user: models.User,
        not_found_detail: str,
        forbidden_detail: str,
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Resolve fornecedor for user from injected repositories or runtime context."""
        return fornecedor_management_service.resolve_fornecedor_for_user(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail=not_found_detail,
            forbidden_detail=forbidden_detail,
        )

    def update_fornecedor(
        self,
        *,
        fornecedor_id: int,
        fornecedor_update: schemas.FornecedorUpdate,
        current_user: models.User,
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Update fornecedor and persist the resulting state changes."""
        return fornecedor_management_service.update_fornecedor(
            fornecedor_id=fornecedor_id,
            fornecedor_update=fornecedor_update,
            current_user=current_user,
        )

    def get_mapping(
        self,
        *,
        fornecedor_id: int,
        current_user: models.User,
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Retrieve mapping using the current service dependencies."""
        return fornecedor_management_service.get_mapping(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )

    def update_mapping(
        self,
        *,
        fornecedor_id: int,
        current_user: models.User,
        mapping: Optional[dict],
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Update mapping and persist the resulting state changes."""
        return fornecedor_management_service.update_mapping(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            mapping=mapping,
        )

    async def preview_pages(
        self,
        *,
        file: UploadFile,
    ):
        """Handle Preview pages in this request workflow."""
        return await self._fornecedor_preview_service.preview_pages(file=file)

    def preview_pdf(
        self,
        *,
        file: UploadFile,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ):
        """Handle Preview pdf in this request workflow."""
        return self._fornecedor_preview_service.preview_pdf(
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    def preview_catalog_from_region(
        self,
        *,
        file_id: int,
        page_number: int,
        region: list[float],
    ):
        """Handle Preview catalog from region in this request workflow."""
        return self._fornecedor_preview_service.preview_catalog_from_region(
            file_id=file_id,
            page_number=page_number,
            region=region,
        )

    def extract_data_from_pdf_bulk(
        self,
        *,
        background_tasks: BackgroundTasks,
        file_id: int,
        region: list[float],
        pages: Optional[List[int]],
        all_pages: bool,
    ):
        """Extract data from pdf bulk."""
        return self._fornecedor_preview_service.extract_data_from_pdf_bulk(
            background_tasks=background_tasks,
            file_id=file_id,
            region=region,
            pages=pages,
            all_pages=all_pages,
        )

    def get_catalog_record_or_404(
        self,
        *,
        file_id: int,
        user_id: int,
        not_found_detail: str,
    ):
        """Retrieve catalog record or 404 using the current service dependencies."""
        return self._fornecedor_import_tracking_service.get_catalog_record_or_404(
            file_id=file_id,
            user_id=user_id,
            not_found_detail=not_found_detail,
        )

    def build_progress_payload(
        self,
        *,
        record: Any,
    ):
        """Build progress payload from current inputs and configuration."""
        return self._fornecedor_import_tracking_service.build_progress_payload(
            record=record
        )

    async def start_full_processing(
        self,
        *,
        background_tasks: BackgroundTasks,
        current_user: models.User,
        file_id: int,
        fornecedor_id: int,
        tipo_produto_id: int,
        start_page: int,
        region: Optional[List[float]],
        mapping: Optional[dict],
    ):
        """Handle Start full processing in this request workflow."""
        return await self._fornecedor_catalog_process_service.start_full_processing(
            background_tasks=background_tasks,
            current_user=current_user,
            file_id=file_id,
            fornecedor_id=fornecedor_id,
            tipo_produto_id=tipo_produto_id,
            start_page=start_page,
            region=region,
            mapping=mapping,
        )

    def schedule_page_extraction(
        self,
        *,
        background_tasks: BackgroundTasks,
        import_job_id: int,
        page_number: int,
        db_url: str,
    ):
        """Handle Schedule page extraction in this request workflow."""
        return self._fornecedor_import_tracking_service.schedule_page_extraction(
            background_tasks=background_tasks,
            import_job_id=import_job_id,
            page_number=page_number,
            db_url=db_url,
        )

    def delete_fornecedor(
        self,
        *,
        fornecedor_id: int,
        current_user: models.User,
        fornecedor_management_service: FornecedorManagementService,
    ):
        """Execute delete fornecedor as part of this module workflow."""
        return fornecedor_management_service.delete_fornecedor(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )

    def get_job_for_user_or_404(
        self,
        *,
        job_id: int,
        user_id: int,
    ):
        """Retrieve job for user or 404 using the current service dependencies."""
        return self._fornecedor_import_job_service.get_job_for_user_or_404(
            job_id=job_id,
            user_id=user_id,
        )

    def build_review_payload(
        self,
        *,
        job: Any,
    ):
        """Build review payload from current inputs and configuration."""
        return self._fornecedor_import_job_service.build_review_payload(job=job)

    def schedule_commit(
        self,
        *,
        background_tasks: BackgroundTasks,
        job_id: int,
        user_id: int,
    ):
        """Handle Schedule commit in this request workflow."""
        return self._fornecedor_import_job_service.schedule_commit(
            background_tasks=background_tasks,
            job_id=job_id,
            user_id=user_id,
        )

    def build_import_job_status_payload(
        self,
        *,
        record: Any,
    ):
        """Build import job status payload from current inputs and configuration."""
        return self._fornecedor_import_tracking_service.build_import_job_status_payload(
            record=record
        )

    def get_database_url(self) -> str:
        """Retrieve database url using the current service dependencies."""
        bind = self._session.get_bind()
        return str(bind.url)

class _FornecedoresRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'fornecedores'."""

    def __init__(self, *, session: Session, fornecedor_management_service: FornecedorManagementService) -> None:
        """Initialize injected dependencies and runtime configuration for Fornecedores Request Scope."""
        self._fornecedor_management_service = fornecedor_management_service
        self._request_service = _FornecedoresDependencies.get_fornecedores_request_service(session)

    def create_fornecedor(self, *, fornecedor: schemas.FornecedorCreate, current_user: models.User) -> models.Fornecedor:
        """Create fornecedor and return the resulting payload or entity."""
        return self._request_service.create_fornecedor(fornecedor=fornecedor, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def list_fornecedores_page(self, *, current_user: models.User, skip: int, limit: int, termo_busca: Optional[str]) -> schemas.FornecedorPage:
        """Execute list fornecedores page as part of this module workflow."""
        return self._request_service.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca, fornecedor_management_service=self._fornecedor_management_service)

    def read_fornecedor(self, *, fornecedor_id: int, current_user: models.User) -> models.Fornecedor:
        """Handle Read fornecedor in this request workflow."""
        return self._request_service.read_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def update_fornecedor(self, *, fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User) -> models.Fornecedor:
        """Update fornecedor and persist the resulting state changes."""
        return self._request_service.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def get_mapping(self, *, fornecedor_id: int, current_user: models.User) -> Optional[dict]:
        """Retrieve mapping using the current service dependencies."""
        return self._request_service.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def update_mapping(self, *, fornecedor_id: int, mapping: Optional[dict], current_user: models.User) -> models.Fornecedor:
        """Update mapping and persist the resulting state changes."""
        return self._request_service.update_mapping(fornecedor_id=fornecedor_id, mapping=mapping, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    async def preview_pages(self, *, file: UploadFile):
        """Handle Preview pages in this request workflow."""
        return await self._request_service.preview_pages(file=file)

    async def preview_pdf(self, *, fornecedor_id: int, file: UploadFile, current_user: models.User, offset: int, limit: int) -> schemas.PdfPreviewResponse:
        """Handle Preview pdf in this request workflow."""
        return await self._request_service.preview_pdf(fornecedor_id=fornecedor_id, file=file, current_user=current_user, offset=offset, limit=limit, fornecedor_management_service=self._fornecedor_management_service)

    def preview_catalog_from_region(self, *, preview_request: schemas.CatalogRegionPreviewRequest) -> schemas.CatalogPreview:
        """Handle Preview catalog from region in this request workflow."""
        return self._request_service.preview_catalog_from_region(preview_request=preview_request)

    def extract_data_from_pdf_bulk(self, *, background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest):
        """Extract data from pdf bulk."""
        return self._request_service.extract_data_from_pdf_bulk(background_tasks=background_tasks, request=request)

    def get_import_progress(self, *, job_id: int, current_user: models.User) -> dict:
        """Retrieve import progress using the current service dependencies."""
        return self._request_service.get_import_progress(job_id=job_id, current_user=current_user)

    async def process_full_catalog(self, *, background_tasks: BackgroundTasks, file_id: int, fornecedor_id: int, tipo_produto_id: int, start_page: int, region: Optional[List[float]], mapping: Optional[dict], current_user: models.User):
        """Handle full catalog in this request workflow."""
        return await self._request_service.process_full_catalog(background_tasks=background_tasks, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping, current_user=current_user)

    def extract_page_data(self, *, background_tasks: BackgroundTasks, file_id: int, page_number: int, current_user: models.User) -> dict:
        """Execute extract page data as part of this module workflow."""
        return self._request_service.extract_page_data(background_tasks=background_tasks, file_id=file_id, page_number=page_number, current_user=current_user)

    def delete_fornecedor(self, *, fornecedor_id: int, current_user: models.User) -> models.Fornecedor:
        """Execute delete fornecedor as part of this module workflow."""
        return self._request_service.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def review_import_job(self, *, job_id: int, current_user: models.User) -> dict:
        """Handle Review import job in this request workflow."""
        return self._request_service.review_import_job(job_id=job_id, current_user=current_user)

    def commit_import_job(self, *, background_tasks: BackgroundTasks, job_id: int, current_user: models.User) -> dict:
        """Handle Commit import job in this request workflow."""
        return self._request_service.commit_import_job(background_tasks=background_tasks, job_id=job_id, current_user=current_user)

    def get_import_job_status(self, *, job_id: int, current_user: models.User) -> dict:
        """Retrieve import job status using the current service dependencies."""
        return self._request_service.get_import_job_status(job_id=job_id, current_user=current_user)
_build_fornecedores_request_scope = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _FornecedoresRequestScope(session=session, fornecedor_management_service=DependencyContainer.get_fornecedor_management_service(session)))

class _EndpointHandlers:

    """Represent Endpoint Handlers and centralize its responsibilities inside this module."""
    @router.post('/', response_model=schemas.FornecedorResponse, status_code=status.HTTP_201_CREATED)
    def create_user_fornecedor(fornecedor: schemas.FornecedorCreate, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (create_user_fornecedor)."""
        try:
            return request_scope.create_fornecedor(fornecedor=fornecedor, current_user=current_user)
        except HTTPException as exc:
            logger.warning('HTTPException ao criar fornecedor: %s', exc.detail)
            raise
        except Exception:
            logger.exception('Erro interno inesperado ao criar fornecedor')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao criar fornecedor. Tente novamente mais tarde.')

    @router.get('/', response_model=schemas.FornecedorPage)
    def read_user_fornecedores(skip: int=Query(0, ge=0, description='Numero de itens para pular'), limit: int=Query(10, ge=1, le=100, description='Numero maximo de itens por pagina'), termo_busca: Optional[str]=Query(None, description='Termo para buscar no nome do fornecedor'), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_user_fornecedores)."""
        return request_scope.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca)

    @router.get('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def read_fornecedor(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_fornecedor)."""
        return request_scope.read_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user)

    @router.put('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def update_fornecedor_endpoint(fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (update_fornecedor_endpoint)."""
        try:
            return request_scope.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao atualizar fornecedor.')

    @router.get('/{fornecedor_id}/mapping', response_model=Optional[dict])
    def get_mapping(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_mapping)."""
        return request_scope.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user)

    @router.put('/{fornecedor_id}/mapping', response_model=schemas.FornecedorResponse)
    def update_mapping(fornecedor_id: int, mapping: Optional[dict]=None, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (update_mapping)."""
        return request_scope.update_mapping(fornecedor_id=fornecedor_id, mapping=mapping, current_user=current_user)

    @router.post('/import/preview-pages')
    async def preview_pages(file: UploadFile=File(...), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_pages)."""
        return await request_scope.preview_pages(file=file)

    @router.post('/{fornecedor_id}/preview-pdf', response_model=schemas.PdfPreviewResponse)
    async def preview_pdf(fornecedor_id: int, file: UploadFile=File(...), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope), offset: int=Query(0, description='Pagina inicial para pre-visualizacao (base 0).'), limit: int=Query(20, description='Numero maximo de paginas para pre-visualizacao.')):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_pdf)."""
        return await request_scope.preview_pdf(fornecedor_id=fornecedor_id, file=file, current_user=current_user, offset=offset, limit=limit)

    @router.post('/preview-catalog-region', response_model=schemas.CatalogPreview)
    def preview_catalog_from_region(preview_request: schemas.CatalogRegionPreviewRequest, request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_catalog_from_region)."""
        return request_scope.preview_catalog_from_region(preview_request=preview_request)

    @router.post('/extract_data_from_pdf_bulk', status_code=status.HTTP_202_ACCEPTED)
    def extract_data_from_pdf_bulk(background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (extract_data_from_pdf_bulk)."""
        _ = current_user
        return request_scope.extract_data_from_pdf_bulk(background_tasks=background_tasks, request=request)

    @router.get('/import/progress/{job_id}')
    def get_import_progress(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_import_progress)."""
        return request_scope.get_import_progress(job_id=job_id, current_user=current_user)

    @router.post('/import/process-full-catalog', status_code=status.HTTP_202_ACCEPTED)
    async def process_full_catalog(background_tasks: BackgroundTasks, file_id: int=Body(..., embed=True), fornecedor_id: int=Body(..., embed=True), tipo_produto_id: int=Body(..., embed=True), start_page: int=Body(1, embed=True), region: Optional[List[float]]=Body(None, embed=True), mapping: Optional[dict]=Body(None), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (process_full_catalog)."""
        return await request_scope.process_full_catalog(background_tasks=background_tasks, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping, current_user=current_user)

    @router.get('/import/extract-page-data', status_code=status.HTTP_202_ACCEPTED)
    def extract_page_data(background_tasks: BackgroundTasks, file_id: int=Query(..., description='ID do arquivo importado'), page_number: int=Query(..., ge=1, description='Numero da pagina a extrair'), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (extract_page_data)."""
        return request_scope.extract_page_data(background_tasks=background_tasks, file_id=file_id, page_number=page_number, current_user=current_user)

    @router.delete('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def delete_fornecedor_endpoint(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_fornecedor_endpoint)."""
        try:
            return request_scope.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao deletar fornecedor.')

    @router.get('/import/review/{job_id}', response_model=dict)
    def review_import_job(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (review_import_job)."""
        return request_scope.review_import_job(job_id=job_id, current_user=current_user)

    @router.post('/import/commit/{job_id}', status_code=status.HTTP_202_ACCEPTED)
    def commit_import_job(background_tasks: BackgroundTasks, job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (commit_import_job)."""
        return request_scope.commit_import_job(background_tasks=background_tasks, job_id=job_id, current_user=current_user)

    @router.get('/import_job/{job_id}/status')
    def get_import_job_status(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_scope: _FornecedoresRequestScope=Depends(_build_fornecedores_request_scope)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_import_job_status)."""
        return request_scope.get_import_job_status(job_id=job_id, current_user=current_user)


