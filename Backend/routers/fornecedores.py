"""Camada de transporte HTTP para o dominio 'fornecedores'."""
from collections import Counter
from pathlib import Path
from typing import List, Optional
import time
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session, sessionmaker
from Backend import database
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

    @staticmethod
    def _build_fornecedores_service_bundle():
        return _FornecedoresServiceBundle()

    @staticmethod
    def get_fornecedores_request_service():
        return FornecedoresRequestService(runtime=_FornecedoresServiceGateway())
logger = get_logger(__name__)
catalog_log_dir = Path(__file__).resolve().parent.parent / 'logs'
catalog_log_dir.mkdir(parents=True, exist_ok=True)
produto_repository = ProductRepository
fornecedor_repository = FornecedorRepository
catalog_file_repository = CatalogImportFileRepository

class _FornecedoresServiceBundle:
    """Componente OO principal '_FornecedoresServiceBundle' do modulo 'fornecedores'."""

    def __init__(self) -> None:
        self._service_container = ServiceContainer()
        self.file_processing_service = self._service_container.file_processing
        self.web_data_extractor_service = self._service_container.web_data_extractor
        self.catalog_quality_service = CatalogImportQualityService()
        self.catalog_sanitization_service = CatalogImportSanitizationService(quality_service=self.catalog_quality_service)
        self.catalog_import_diagnostics_service = CatalogImportDiagnosticsService(catalog_log_dir=catalog_log_dir, logger=logger, sanitization_service=self.catalog_sanitization_service)
        self.validator_crew = ValidatorCrewService(logger=logger)
        self.catalog_import_task_runner = CatalogImportTaskRunner(logger=logger, catalog_logger=logger, models=models, schemas=schemas, product_repository=produto_repository, catalog_file_repository=catalog_file_repository, file_processing_service=self.file_processing_service, validator_crew=self.validator_crew, settings=settings, path_cls=Path, time_module=time, counter_cls=Counter, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item, extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason, is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason, normalizar_dados_validados=self.catalog_sanitization_service.normalize_validated_data, sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product, classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality, write_catalog_import_report=self.catalog_import_diagnostics_service.write_catalog_import_report, normalize_import_text=self.catalog_sanitization_service.normalize_import_text)
        self.catalog_import_finalize_service = CatalogImportFinalizeService(oop_executor=self.catalog_import_task_runner.execute)
        self.catalog_import_start_service = CatalogImportStartService(models=models, fornecedor_repo=fornecedor_repository, catalog_file_repository=catalog_file_repository, settings=settings, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, finalize_service=self.catalog_import_finalize_service)
        self.fornecedor_catalog_process_service = FornecedorCatalogProcessService(models=models, fornecedor_repo=fornecedor_repository, catalog_import_start_service=self.catalog_import_start_service)
        self.fornecedor_import_job_service = FornecedorImportJobService(import_job_repository_cls=FornecedorImportJobRepository, produto_repository_cls=ProductRepository, produto_create_schema=schemas.ProdutoCreate)
        self.fornecedor_import_tracking_service = FornecedorImportTrackingService(
            models=models,
            process_pdf_extraction_task=TaskWorkflow().process_pdf_extraction_task,
            catalog_file_repository=catalog_file_repository,
        )
        self.fornecedor_preview_service = FornecedorPreviewService(file_processing_service=self.file_processing_service, web_data_extractor_service=self.web_data_extractor_service)
router = APIRouter(prefix='/fornecedores', tags=['fornecedores'], dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)])

class FornecedoresRequestService:
    """Workflow/escopo request-scoped para o fluxo de 'fornecedores'."""

    def __init__(self, runtime: Optional['_FornecedoresServiceGateway']=None) -> None:
        self._runtime = runtime or _FornecedoresServiceGateway()

    def create_fornecedor(self, fornecedor: schemas.FornecedorCreate, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        logger.info('Requisicao para criar fornecedor recebida.')
        return self._runtime.create_fornecedor(fornecedor=fornecedor, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def list_fornecedores_page(self, current_user: models.User, skip: int, limit: int, termo_busca: Optional[str], fornecedor_management_service: FornecedorManagementService) -> schemas.FornecedorPage:
        return self._runtime.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca, fornecedor_management_service=fornecedor_management_service)

    def read_fornecedor(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        return self._runtime.resolve_fornecedor_for_user(fornecedor_id=fornecedor_id, current_user=current_user, not_found_detail='Fornecedor nao encontrado ou nao pertence ao usuario', forbidden_detail='Nao autorizado a acessar este fornecedor.', fornecedor_management_service=fornecedor_management_service)

    def update_fornecedor(self, fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        return self._runtime.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def get_mapping(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> Optional[dict]:
        return self._runtime.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def update_mapping(self, fornecedor_id: int, mapping: Optional[dict], current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        return self._runtime.update_mapping(fornecedor_id=fornecedor_id, current_user=current_user, mapping=mapping, fornecedor_management_service=fornecedor_management_service)

    async def preview_pages(self, file: UploadFile):
        return await self._runtime.preview_pages(file=file)

    async def preview_pdf(self, fornecedor_id: int, file: UploadFile, db: Session, current_user: models.User, offset: int, limit: int, fornecedor_management_service: FornecedorManagementService) -> schemas.PdfPreviewResponse:
        _ = self._runtime.resolve_fornecedor_for_user(fornecedor_id=fornecedor_id, current_user=current_user, not_found_detail='Fornecedor nao encontrado', forbidden_detail='Nao autorizado a acessar este fornecedor.', fornecedor_management_service=fornecedor_management_service)
        return self._runtime.preview_pdf(db=db, file=file, fornecedor_id=fornecedor_id, user_id=current_user.id, offset=offset, limit=limit)

    def preview_catalog_from_region(self, preview_request: schemas.CatalogRegionPreviewRequest, db: Session) -> schemas.CatalogPreview:
        return self._runtime.preview_catalog_from_region(db=db, file_id=preview_request.file_id, page_number=preview_request.page_number, region=preview_request.region)

    def extract_data_from_pdf_bulk(self, background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest, db: Session):
        return self._runtime.extract_data_from_pdf_bulk(background_tasks=background_tasks, db=db, file_id=request.file_id, region=request.region, pages=request.pages, all_pages=request.all_pages)

    def get_import_progress(self, job_id: int, db: Session, current_user: models.User) -> dict:
        record = self._runtime.get_catalog_record_or_404(db=db, file_id=job_id, user_id=current_user.id, not_found_detail='Importacao nao encontrada')
        return self._runtime.build_progress_payload(record=record)

    async def process_full_catalog(self, background_tasks: BackgroundTasks, file_id: int, fornecedor_id: int, tipo_produto_id: int, start_page: int, region: Optional[List[float]], mapping: Optional[dict], db: Session, current_user: models.User):
        return await self._runtime.start_full_processing(background_tasks=background_tasks, db=db, current_user=current_user, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping)

    def extract_page_data(self, background_tasks: BackgroundTasks, file_id: int, page_number: int, db: Session, current_user: models.User) -> dict:
        record = self._runtime.get_catalog_record_or_404(db=db, file_id=file_id, user_id=current_user.id, not_found_detail='Arquivo nao encontrado')
        self._runtime.schedule_page_extraction(background_tasks=background_tasks, import_job_id=record.id, page_number=page_number, db_url=str(database.engine.url))
        return {'job_id': record.id, 'status': 'PROCESSING'}

    def delete_fornecedor(self, fornecedor_id: int, current_user: models.User, fornecedor_management_service: FornecedorManagementService) -> models.Fornecedor:
        return self._runtime.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=fornecedor_management_service)

    def review_import_job(self, job_id: int, db: Session, current_user: models.User) -> dict:
        job = self._runtime.get_job_for_user_or_404(db=db, job_id=job_id, user_id=current_user.id)
        return self._runtime.build_review_payload(job=job)

    def commit_import_job(self, background_tasks: BackgroundTasks, job_id: int, db: Session, current_user: models.User) -> dict:
        _ = self._runtime.get_job_for_user_or_404(db=db, job_id=job_id, user_id=current_user.id)
        self._runtime.schedule_commit(background_tasks=background_tasks, db=db, job_id=job_id, user_id=current_user.id)
        return {'status': 'PROCESSING', 'job_id': job_id}

    def get_import_job_status(self, job_id: int, db: Session, current_user: models.User) -> dict:
        record = self._runtime.get_catalog_record_or_404(db=db, file_id=job_id, user_id=current_user.id, not_found_detail='Job nao encontrado')
        return self._runtime.build_import_job_status_payload(record=record)

class _FornecedoresServiceGateway:
    """Runtime OO para integrações do router de fornecedores."""

    def __init__(self, *, services: Optional[_FornecedoresServiceBundle]=None) -> None:
        self._services = services or _FornecedoresDependencies._build_fornecedores_service_bundle()

    @staticmethod
    def _resolve_management_service(kwargs: dict) -> FornecedorManagementService:
        fornecedor_management_service = kwargs.pop('fornecedor_management_service', None)
        if fornecedor_management_service is not None:
            return fornecedor_management_service
        raise ValueError('fornecedor_management_service is required')

    def create_fornecedor(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.create_fornecedor(**kwargs)

    def list_fornecedores_page(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.list_fornecedores_page(**kwargs)

    def resolve_fornecedor_for_user(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.resolve_fornecedor_for_user(**kwargs)

    def update_fornecedor(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.update_fornecedor(**kwargs)

    def get_mapping(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.get_mapping(**kwargs)

    def update_mapping(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.update_mapping(**kwargs)

    async def preview_pages(self, **kwargs):
        return await self._services.fornecedor_preview_service.preview_pages(**kwargs)

    def preview_pdf(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['catalog_file_repo'] = CatalogImportFileRepository(db)
        return self._services.fornecedor_preview_service.preview_pdf(**kwargs)

    def preview_catalog_from_region(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['catalog_file_repo'] = CatalogImportFileRepository(db)
        return self._services.fornecedor_preview_service.preview_catalog_from_region(**kwargs)

    def extract_data_from_pdf_bulk(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['catalog_file_repo'] = CatalogImportFileRepository(db)
        return self._services.fornecedor_preview_service.extract_data_from_pdf_bulk(**kwargs)

    def get_catalog_record_or_404(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['catalog_file_repo'] = CatalogImportFileRepository(db)
        return self._services.fornecedor_import_tracking_service.get_catalog_record_or_404(**kwargs)

    def build_progress_payload(self, **kwargs):
        return self._services.fornecedor_import_tracking_service.build_progress_payload(**kwargs)

    async def start_full_processing(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['fornecedor_repo'] = FornecedorRepository(db)
            kwargs['catalog_file_repo'] = CatalogImportFileRepository(db)
            kwargs['db_session_factory'] = sessionmaker(bind=db.get_bind())
        return await self._services.fornecedor_catalog_process_service.start_full_processing(**kwargs)

    def schedule_page_extraction(self, **kwargs):
        return self._services.fornecedor_import_tracking_service.schedule_page_extraction(**kwargs)

    def delete_fornecedor(self, **kwargs):
        fornecedor_management_service = self._resolve_management_service(kwargs)
        return fornecedor_management_service.delete_fornecedor(**kwargs)

    def get_job_for_user_or_404(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['import_job_repo'] = FornecedorImportJobRepository(db)
        return self._services.fornecedor_import_job_service.get_job_for_user_or_404(**kwargs)

    def build_review_payload(self, **kwargs):
        return self._services.fornecedor_import_job_service.build_review_payload(**kwargs)

    def schedule_commit(self, **kwargs):
        db = kwargs.pop('db', None)
        if db is not None:
            kwargs['db_session_factory'] = sessionmaker(bind=db.get_bind())
        return self._services.fornecedor_import_job_service.schedule_commit(**kwargs)

    def build_import_job_status_payload(self, **kwargs):
        return self._services.fornecedor_import_tracking_service.build_import_job_status_payload(**kwargs)

class _FornecedoresRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'fornecedores'."""

    def __init__(self, *, db: Session, fornecedor_management_service: FornecedorManagementService) -> None:
        self._db = db
        self._fornecedor_management_service = fornecedor_management_service
        self._request_service = _FornecedoresDependencies.get_fornecedores_request_service()

    def create_fornecedor(self, *, fornecedor: schemas.FornecedorCreate, current_user: models.User) -> models.Fornecedor:
        return self._request_service.create_fornecedor(fornecedor=fornecedor, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def list_fornecedores_page(self, *, current_user: models.User, skip: int, limit: int, termo_busca: Optional[str]) -> schemas.FornecedorPage:
        return self._request_service.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca, fornecedor_management_service=self._fornecedor_management_service)

    def read_fornecedor(self, *, fornecedor_id: int, current_user: models.User) -> models.Fornecedor:
        return self._request_service.read_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def update_fornecedor(self, *, fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User) -> models.Fornecedor:
        return self._request_service.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def get_mapping(self, *, fornecedor_id: int, current_user: models.User) -> Optional[dict]:
        return self._request_service.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def update_mapping(self, *, fornecedor_id: int, mapping: Optional[dict], current_user: models.User) -> models.Fornecedor:
        return self._request_service.update_mapping(fornecedor_id=fornecedor_id, mapping=mapping, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    async def preview_pages(self, *, file: UploadFile):
        return await self._request_service.preview_pages(file=file)

    async def preview_pdf(self, *, fornecedor_id: int, file: UploadFile, current_user: models.User, offset: int, limit: int) -> schemas.PdfPreviewResponse:
        return await self._request_service.preview_pdf(fornecedor_id=fornecedor_id, file=file, db=self._db, current_user=current_user, offset=offset, limit=limit, fornecedor_management_service=self._fornecedor_management_service)

    def preview_catalog_from_region(self, *, preview_request: schemas.CatalogRegionPreviewRequest) -> schemas.CatalogPreview:
        return self._request_service.preview_catalog_from_region(preview_request=preview_request, db=self._db)

    def extract_data_from_pdf_bulk(self, *, background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest):
        return self._request_service.extract_data_from_pdf_bulk(background_tasks=background_tasks, request=request, db=self._db)

    def get_import_progress(self, *, job_id: int, current_user: models.User) -> dict:
        return self._request_service.get_import_progress(job_id=job_id, db=self._db, current_user=current_user)

    async def process_full_catalog(self, *, background_tasks: BackgroundTasks, file_id: int, fornecedor_id: int, tipo_produto_id: int, start_page: int, region: Optional[List[float]], mapping: Optional[dict], current_user: models.User):
        return await self._request_service.process_full_catalog(background_tasks=background_tasks, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping, db=self._db, current_user=current_user)

    def extract_page_data(self, *, background_tasks: BackgroundTasks, file_id: int, page_number: int, current_user: models.User) -> dict:
        return self._request_service.extract_page_data(background_tasks=background_tasks, file_id=file_id, page_number=page_number, db=self._db, current_user=current_user)

    def delete_fornecedor(self, *, fornecedor_id: int, current_user: models.User) -> models.Fornecedor:
        return self._request_service.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user, fornecedor_management_service=self._fornecedor_management_service)

    def review_import_job(self, *, job_id: int, current_user: models.User) -> dict:
        return self._request_service.review_import_job(job_id=job_id, db=self._db, current_user=current_user)

    def commit_import_job(self, *, background_tasks: BackgroundTasks, job_id: int, current_user: models.User) -> dict:
        return self._request_service.commit_import_job(background_tasks=background_tasks, job_id=job_id, db=self._db, current_user=current_user)

    def get_import_job_status(self, *, job_id: int, current_user: models.User) -> dict:
        return self._request_service.get_import_job_status(job_id=job_id, db=self._db, current_user=current_user)
_build_fornecedores_request_workflow = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _FornecedoresRequestScope(db=session, fornecedor_management_service=DependencyContainer.get_fornecedor_management_service(db=session)))

class _EndpointHandlers:

    @router.post('/', response_model=schemas.FornecedorResponse, status_code=status.HTTP_201_CREATED)
    def create_user_fornecedor(fornecedor: schemas.FornecedorCreate, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (create_user_fornecedor)."""
        try:
            return request_workflow.create_fornecedor(fornecedor=fornecedor, current_user=current_user)
        except HTTPException as exc:
            logger.warning('HTTPException ao criar fornecedor: %s', exc.detail)
            raise
        except Exception:
            logger.exception('Erro interno inesperado ao criar fornecedor')
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao criar fornecedor. Tente novamente mais tarde.')

    @router.get('/', response_model=schemas.FornecedorPage)
    def read_user_fornecedores(skip: int=Query(0, ge=0, description='Numero de itens para pular'), limit: int=Query(10, ge=1, le=100, description='Numero maximo de itens por pagina'), termo_busca: Optional[str]=Query(None, description='Termo para buscar no nome do fornecedor'), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_user_fornecedores)."""
        return request_workflow.list_fornecedores_page(current_user=current_user, skip=skip, limit=limit, termo_busca=termo_busca)

    @router.get('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def read_fornecedor(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_fornecedor)."""
        return request_workflow.read_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user)

    @router.put('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def update_fornecedor_endpoint(fornecedor_id: int, fornecedor_update: schemas.FornecedorUpdate, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (update_fornecedor_endpoint)."""
        try:
            return request_workflow.update_fornecedor(fornecedor_id=fornecedor_id, fornecedor_update=fornecedor_update, current_user=current_user)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao atualizar fornecedor.')

    @router.get('/{fornecedor_id}/mapping', response_model=Optional[dict])
    def get_mapping(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_mapping)."""
        return request_workflow.get_mapping(fornecedor_id=fornecedor_id, current_user=current_user)

    @router.put('/{fornecedor_id}/mapping', response_model=schemas.FornecedorResponse)
    def update_mapping(fornecedor_id: int, mapping: Optional[dict]=None, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (update_mapping)."""
        return request_workflow.update_mapping(fornecedor_id=fornecedor_id, mapping=mapping, current_user=current_user)

    @router.post('/import/preview-pages')
    async def preview_pages(file: UploadFile=File(...), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_pages)."""
        return await request_workflow.preview_pages(file=file)

    @router.post('/{fornecedor_id}/preview-pdf', response_model=schemas.PdfPreviewResponse)
    async def preview_pdf(fornecedor_id: int, file: UploadFile=File(...), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow), offset: int=Query(0, description='Pagina inicial para pre-visualizacao (base 0).'), limit: int=Query(20, description='Numero maximo de paginas para pre-visualizacao.')):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_pdf)."""
        return await request_workflow.preview_pdf(fornecedor_id=fornecedor_id, file=file, current_user=current_user, offset=offset, limit=limit)

    @router.post('/preview-catalog-region', response_model=schemas.CatalogPreview)
    def preview_catalog_from_region(preview_request: schemas.CatalogRegionPreviewRequest, request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (preview_catalog_from_region)."""
        return request_workflow.preview_catalog_from_region(preview_request=preview_request)

    @router.post('/extract_data_from_pdf_bulk', status_code=status.HTTP_202_ACCEPTED)
    def extract_data_from_pdf_bulk(background_tasks: BackgroundTasks, request: schemas.PdfRegionBulkRequest, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (extract_data_from_pdf_bulk)."""
        _ = current_user
        return request_workflow.extract_data_from_pdf_bulk(background_tasks=background_tasks, request=request)

    @router.get('/import/progress/{job_id}')
    def get_import_progress(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_import_progress)."""
        return request_workflow.get_import_progress(job_id=job_id, current_user=current_user)

    @router.post('/import/process-full-catalog', status_code=status.HTTP_202_ACCEPTED)
    async def process_full_catalog(background_tasks: BackgroundTasks, file_id: int=Body(..., embed=True), fornecedor_id: int=Body(..., embed=True), tipo_produto_id: int=Body(..., embed=True), start_page: int=Body(1, embed=True), region: Optional[List[float]]=Body(None, embed=True), mapping: Optional[dict]=Body(None), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (process_full_catalog)."""
        return await request_workflow.process_full_catalog(background_tasks=background_tasks, file_id=file_id, fornecedor_id=fornecedor_id, tipo_produto_id=tipo_produto_id, start_page=start_page, region=region, mapping=mapping, current_user=current_user)

    @router.get('/import/extract-page-data', status_code=status.HTTP_202_ACCEPTED)
    def extract_page_data(background_tasks: BackgroundTasks, file_id: int=Query(..., description='ID do arquivo importado'), page_number: int=Query(..., ge=1, description='Numero da pagina a extrair'), current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (extract_page_data)."""
        return request_workflow.extract_page_data(background_tasks=background_tasks, file_id=file_id, page_number=page_number, current_user=current_user)

    @router.delete('/{fornecedor_id}', response_model=schemas.FornecedorResponse)
    def delete_fornecedor_endpoint(fornecedor_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_fornecedor_endpoint)."""
        try:
            return request_workflow.delete_fornecedor(fornecedor_id=fornecedor_id, current_user=current_user)
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Erro interno ao deletar fornecedor.')

    @router.get('/import/review/{job_id}', response_model=dict)
    def review_import_job(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (review_import_job)."""
        return request_workflow.review_import_job(job_id=job_id, current_user=current_user)

    @router.post('/import/commit/{job_id}', status_code=status.HTTP_202_ACCEPTED)
    def commit_import_job(background_tasks: BackgroundTasks, job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (commit_import_job)."""
        return request_workflow.commit_import_job(background_tasks=background_tasks, job_id=job_id, current_user=current_user)

    @router.get('/import_job/{job_id}/status')
    def get_import_job_status(job_id: int, current_user: models.User=Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user), request_workflow: _FornecedoresRequestScope=Depends(_build_fornecedores_request_workflow)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (get_import_job_status)."""
        return request_workflow.get_import_job_status(job_id=job_id, current_user=current_user)

