"""Camada de transporte HTTP para o dominio 'produtos'."""
from collections import Counter
from logging import FileHandler, Formatter
from pathlib import Path
import inspect
import json
import logging
import time
from typing import Any, Dict, List, Optional, Union

import pdfplumber
from fastapi import APIRouter, BackgroundTasks, Body, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from Backend import models
from Backend import schemas
from Backend.application.services.catalog_import_diagnostics_service import CatalogImportDiagnosticsService
from Backend.application.services.catalog_import_file_service import CatalogImportFileService
from Backend.application.services.catalog_import_finalize_service import CatalogImportFinalizeService
from Backend.application.services.catalog_import_ingest_service import CatalogImportIngestService
from Backend.application.services.catalog_import_preview_service import CatalogImportPreviewService
from Backend.application.services.catalog_import_quality_service import CatalogImportQualityService
from Backend.application.services.catalog_import_sanitization_service import CatalogImportSanitizationService
from Backend.application.services.catalog_import_start_service import CatalogImportStartService
from Backend.application.services.catalog_import_status_service import CatalogImportStatusService
from Backend.application.services.catalog_import_task_runner import CatalogImportTaskRunner
from Backend.application.services.catalog_import_workflow_service import CatalogImportWorkflowService
from Backend.application.services.product_management_service import ProductManagementService
from Backend.application.services.product_media_service import ProductMediaService
from Backend.application.services.product_repositories import ProductRepositories
from Backend.application.services.service_container import DependencyContainer, ServiceContainer, ServiceContainerDependencySupport
from Backend.application.services.validator_crew_service import ValidatorCrewService
from Backend.core.config import settings
from Backend.infrastructure.repositories.catalog_import_file_repository import CatalogImportFileRepository
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import RegistroUsoIARepository

from . import auth_utils

_CURRENT_ACTIVE_USER_PROVIDER = auth_utils._AuthUtilsActiveUserDependency.get_current_active_user

router = APIRouter(
    prefix='/produtos',
    tags=['produtos'],
    dependencies=[Depends(_CURRENT_ACTIVE_USER_PROVIDER)],
)
logger = logging.getLogger(__name__)
catalog_log_dir = Path(__file__).resolve().parent.parent / 'logs'
catalog_log_dir.mkdir(parents=True, exist_ok=True)
catalog_logger = logging.getLogger('catalogo')
if not catalog_logger.handlers:
    file_handler = FileHandler(catalog_log_dir / 'catalogo.log', encoding='utf-8')
    file_handler.setFormatter(Formatter('%(asctime)s [%(levelname)s] %(message)s'))
    catalog_logger.addHandler(file_handler)
    catalog_logger.setLevel(logging.INFO)
produto_repository = ProductRepository
fornecedor_repository = FornecedorRepository
uso_ia_repository = RegistroUsoIARepository
historico_repository = HistoricoRepository
catalog_file_repository = CatalogImportFileRepository

class _ProdutosServiceBundle:
    """Componente OO principal '_ProdutosServiceBundle' do modulo 'produtos'."""

    def __init__(self, *, session_provider: Any | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Service Bundle."""
        self._service_container = ServiceContainer()
        self._session_provider = (
            session_provider
            or ServiceContainerDependencySupport.get_background_session_provider()
        )
        self.file_processing_service = self._service_container.file_processing
        self.catalog_quality_service = CatalogImportQualityService()
        self.catalog_sanitization_service = CatalogImportSanitizationService(quality_service=self.catalog_quality_service)
        self.catalog_import_diagnostics_service = CatalogImportDiagnosticsService(catalog_log_dir=catalog_log_dir, logger=catalog_logger, sanitization_service=self.catalog_sanitization_service)
        self.validator_crew = ValidatorCrewService(logger=logger)
        self.catalog_import_task_runner = CatalogImportTaskRunner(session_provider=self._session_provider, logger=logger, catalog_logger=catalog_logger, models=models, schemas=schemas, product_repository_factory=produto_repository, catalog_file_repository_factory=catalog_file_repository, file_processing_service=self.file_processing_service, validator_crew=self.validator_crew, settings=settings, path_cls=Path, time_module=time, counter_cls=Counter, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item, extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason, is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason, normalizar_dados_validados=self.catalog_sanitization_service.normalize_validated_data, sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product, classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality, write_catalog_import_report=self.catalog_import_diagnostics_service.write_catalog_import_report, normalize_import_text=self.catalog_sanitization_service.normalize_import_text)
        self.catalog_import_finalize_service = CatalogImportFinalizeService(
            oop_executor=self.catalog_import_task_runner.execute
        )
        self.catalog_import_start_service = CatalogImportStartService(models=models, fornecedor_repo=fornecedor_repository, catalog_file_repository=catalog_file_repository, settings=settings, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, finalize_service=self.catalog_import_finalize_service)
        self.catalog_import_status_service = CatalogImportStatusService(models=models, catalog_file_repository=catalog_file_repository)
        self.catalog_import_workflow_service = CatalogImportWorkflowService(start_service=self.catalog_import_start_service, status_service=self.catalog_import_status_service)
        self.catalog_import_file_service = CatalogImportFileService(models=models, file_processing_service=self.file_processing_service, catalog_import_start_service=self.catalog_import_start_service, catalog_file_repository=catalog_file_repository, fornecedor_repository=fornecedor_repository)
        self.catalog_import_preview_service = CatalogImportPreviewService(models=models, settings=settings, file_processing_service=self.file_processing_service, resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path, logger=logger, pdfplumber_module=pdfplumber, catalog_file_repository=catalog_file_repository)
        self.catalog_import_ingest_service = CatalogImportIngestService(schemas=schemas, models=models, fornecedor_repo=fornecedor_repository, produto_repo=produto_repository, uso_ia_repo=uso_ia_repository, historico_repo=historico_repository, file_processing_service=self.file_processing_service, normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item, extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason, is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason, sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product, classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality, json_module=json)

class _ProdutosCatalogService:
    """Runtime OO responsavel por integracoes e operacoes de 'produtos'."""

    def __init__(self, *, session: Session, services: Optional[_ProdutosServiceBundle]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Catalog Service."""
        self._session = session
        runtime_session_provider = (
            ServiceContainerDependencySupport.build_background_session_provider_from_session(
                session
            )
        )
        self._services = services or _ProdutosServiceBundle(
            session_provider=runtime_session_provider
        )
        self._catalog_file_repository = CatalogImportFileRepository(self._session)
        self._fornecedor_repository = FornecedorRepository(self._session)
        self._produto_repository = ProductRepository(self._session)
        self._uso_ia_repository = RegistroUsoIARepository(self._session)
        self._historico_repository = HistoricoRepository(self._session)
        self._catalog_import_start_service = CatalogImportStartService(
            models=models,
            fornecedor_repo=self._fornecedor_repository,
            catalog_file_repository=self._catalog_file_repository,
            settings=settings,
            resolve_storage_path=self._services.catalog_import_diagnostics_service.resolve_storage_path,
            finalize_service=self._services.catalog_import_finalize_service,
        )
        self._catalog_import_status_service = CatalogImportStatusService(
            models=models,
            catalog_file_repository=self._catalog_file_repository,
        )
        self._catalog_import_workflow_service = CatalogImportWorkflowService(
            start_service=self._catalog_import_start_service,
            status_service=self._catalog_import_status_service,
        )
        self._catalog_import_file_service = CatalogImportFileService(
            models=models,
            file_processing_service=self._services.file_processing_service,
            catalog_import_start_service=self._catalog_import_start_service,
            catalog_file_repository=self._catalog_file_repository,
            fornecedor_repository=self._fornecedor_repository,
        )
        self._catalog_import_preview_service = CatalogImportPreviewService(
            models=models,
            settings=settings,
            file_processing_service=self._services.file_processing_service,
            resolve_storage_path=self._services.catalog_import_diagnostics_service.resolve_storage_path,
            logger=logger,
            pdfplumber_module=pdfplumber,
            catalog_file_repository=self._catalog_file_repository,
        )
        self._catalog_import_ingest_service = CatalogImportIngestService(
            schemas=schemas,
            models=models,
            fornecedor_repo=self._fornecedor_repository,
            produto_repo=self._produto_repository,
            uso_ia_repo=self._uso_ia_repository,
            historico_repo=self._historico_repository,
            file_processing_service=self._services.file_processing_service,
            normalize_import_issue_item=self._services.catalog_sanitization_service.normalize_import_issue_item,
            extract_import_error_reason=self._services.catalog_sanitization_service.extract_import_error_reason,
            is_non_critical_import_reason=self._services.catalog_sanitization_service.is_non_critical_import_reason,
            sanitize_produto_extraido=self._services.catalog_sanitization_service.sanitize_extracted_product,
            classificar_qualidade_linha_produto=self._services.catalog_quality_service.classify_product_row_quality,
            json_module=json,
        )

    def _build_product_management_service(self) -> ProductManagementService:
        """Handle Build product management service in this request workflow."""
        repos = ProductRepositories.build_product_management_repositories(session=self._session)
        return ProductManagementService(models=models, schemas=schemas, **repos)

    def _build_product_media_service(self) -> ProductMediaService:
        """Handle Build product media service in this request workflow."""
        repos = ProductRepositories.build_product_media_repositories(session=self._session)
        return ProductMediaService(schemas=schemas, **repos)

    def create_produto(self, produto: schemas.ProdutoCreate, current_user: models.User) -> models.Produto:
        """Create produto and return the resulting payload or entity."""
        return self._build_product_management_service().create_produto(produto=produto, current_user=current_user)

    def list_catalog_import_files(self, user_id: int, fornecedor_id: Optional[int], skip: int, limit: int) -> schemas.CatalogImportFilePage:
        """Execute list catalog import files as part of this module workflow."""
        return self._catalog_import_file_service.list_user_files(user_id=user_id, fornecedor_id=fornecedor_id, skip=skip, limit=limit)

    def delete_catalog_import_file(self, file_id: int, user_id: int):
        """Execute delete catalog import file as part of this module workflow."""
        return self._catalog_import_file_service.delete_user_file(file_id=file_id, user_id=user_id)

    async def reprocess_catalog_import_file(self, background_tasks: BackgroundTasks, file_id: int, user_id: int, product_type_id: Optional[int], fornecedor_id: Optional[int], mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]]):
        """Handle Reprocess catalog import file in this request workflow."""
        return await self._catalog_import_file_service.reprocess_catalog_file(background_tasks=background_tasks, file_id=file_id, user_id=user_id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region)

    def read_produto(self, produto_id: int, current_user: models.User):
        """Handle Read produto in this request workflow."""
        return self._build_product_management_service().read_produto(produto_id=produto_id, current_user=current_user)

    def list_produtos(self, skip: int, limit: int, sort_by: Optional[str], sort_order: Optional[str], search: Optional[str], fornecedor_id: Optional[int], categoria: Optional[str], status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum], status_titulo_ia: Optional[models.StatusGeracaoIAEnum], status_descricao_ia: Optional[models.StatusGeracaoIAEnum], product_type_id: Optional[int], current_user: models.User):
        """Execute list produtos as part of this module workflow."""
        return self._build_product_management_service().list_produtos(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search, fornecedor_id=fornecedor_id, categoria=categoria, status_enriquecimento_web=status_enriquecimento_web, status_titulo_ia=status_titulo_ia, status_descricao_ia=status_descricao_ia, product_type_id=product_type_id, current_user=current_user)

    def update_produto(self, produto_id: int, produto_update: schemas.ProdutoUpdate, current_user: models.User):
        """Update produto and persist the resulting state changes."""
        return self._build_product_management_service().update_produto(produto_id=produto_id, produto_update=produto_update, current_user=current_user)

    def delete_produto(self, produto_id: int, current_user: models.User):
        """Execute delete produto as part of this module workflow."""
        return self._build_product_management_service().delete_produto(produto_id=produto_id, current_user=current_user)

    def batch_delete_produtos(self, produto_ids: List[int], current_user: models.User):
        """Handle Batch delete produtos in this request workflow."""
        return self._build_product_management_service().batch_delete_produtos(produto_ids=produto_ids, current_user=current_user)

    async def upload_produto_image(self, produto_id: int, file: UploadFile, current_user: models.User):
        """Handle Upload produto image in this request workflow."""
        return await self._build_product_media_service().upload_produto_image(produto_id=produto_id, file=file, current_user=current_user)

    async def importar_catalogo_preview(self, file: UploadFile, fornecedor_id: Optional[int], start_page: int, page_count: int, dpi: int, user_id: int) -> schemas.ImportPreviewResponse:
        """Handle Importar catalogo preview in this request workflow."""
        response_payload = await self._catalog_import_preview_service.importar_catalogo_preview(file=file, fornecedor_id=fornecedor_id, start_page=start_page, page_count=page_count, dpi=dpi, user_id=user_id)
        return schemas.ImportPreviewResponse(**response_payload)

    async def importar_catalogo_fornecedor(self, fornecedor_id: int, file: UploadFile, mapeamento_colunas_usuario: Optional[str], current_user: models.User):
        """Handle Importar catalogo fornecedor in this request workflow."""
        return await self._catalog_import_ingest_service.importar_catalogo_fornecedor(fornecedor_id=fornecedor_id, file=file, mapeamento_colunas_usuario=mapeamento_colunas_usuario, current_user=current_user)

    async def importar_catalogo_finalizar(self, background_tasks: BackgroundTasks, file_id: int, product_type_id: int, fornecedor_id: int, mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar in this request workflow."""
        return await self._catalog_import_workflow_service.importar_catalogo_finalizar(background_tasks=background_tasks, file_id=file_id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region, extraction_mode=extraction_mode, user_id=user_id)

    def importar_catalogo_status(self, file_id: int, user_id: int):
        """Handle Importar catalogo status in this request workflow."""
        return self._catalog_import_workflow_service.importar_catalogo_status(file_id=file_id, user_id=user_id)

    def importar_catalogo_status_simple(self, file_id: int, user_id: int):
        """Handle Importar catalogo status simple in this request workflow."""
        return self._catalog_import_workflow_service.importar_catalogo_status_simple(file_id=file_id, user_id=user_id)

    def importar_catalogo_result(self, file_id: int, user_id: int):
        """Handle Importar catalogo result in this request workflow."""
        return self._catalog_import_workflow_service.importar_catalogo_result(file_id=file_id, user_id=user_id)

    async def importar_catalogo_finalizar_todas_paginas(self, file_id: int, start_page: int, mapping: Optional[Dict[str, str]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar todas paginas in this request workflow."""
        return await self._catalog_import_workflow_service.importar_catalogo_finalizar_todas_paginas(file_id=file_id, start_page=start_page, mapping=mapping, extraction_mode=extraction_mode, user_id=user_id)

    async def selecionar_regiao(self, file_id: int, page: int, bbox: List[float], bbox_norm: Optional[List[float]], user_id: int):
        """Handle Selecionar regiao in this request workflow."""
        return self._catalog_import_preview_service.selecionar_regiao(file_id=file_id, page=page, bbox=bbox, bbox_norm=bbox_norm, user_id=user_id)

    async def extrair_pagina_unica(self, file_id: int, page_number: int, user_id: int):
        """Handle Extrair pagina unica in this request workflow."""
        return await self._catalog_import_preview_service.extrair_pagina_unica(file_id=file_id, page_number=page_number, user_id=user_id)

class ProdutosCatalogCoordinator:
    """Workflow/escopo request-scoped para o fluxo de 'produtos'."""

    def __init__(self, runtime: Optional[object]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Catalog Coordinator."""
        if runtime is None:
            raise RuntimeError("ProdutosCatalogCoordinator requires an explicit runtime instance.")
        self._runtime = runtime

    @staticmethod
    async def _await_if_needed(result: Any):
        """Handle Await if needed in this request workflow."""
        if inspect.isawaitable(result):
            return await result
        return result

    def create_produto(self, produto: schemas.ProdutoCreate, current_user: models.User) -> models.Produto:
        """Create produto and return the resulting payload or entity."""
        return self._runtime.create_produto(produto=produto, current_user=current_user)

    def list_catalog_import_files(self, user_id: int, fornecedor_id: Optional[int], skip: int, limit: int) -> schemas.CatalogImportFilePage:
        """Execute list catalog import files as part of this module workflow."""
        return self._runtime.list_catalog_import_files(
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )

    def delete_catalog_import_file(self, file_id: int, user_id: int):
        """Execute delete catalog import file as part of this module workflow."""
        return self._runtime.delete_catalog_import_file(file_id=file_id, user_id=user_id)

    async def reprocess_catalog_import_file(self, background_tasks: BackgroundTasks, file_id: int, user_id: int, product_type_id: Optional[int], fornecedor_id: Optional[int], mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]]):
        """Handle Reprocess catalog import file in this request workflow."""
        return await self._await_if_needed(
            self._runtime.reprocess_catalog_import_file(
                background_tasks=background_tasks,
                file_id=file_id,
                user_id=user_id,
                product_type_id=product_type_id,
                fornecedor_id=fornecedor_id,
                mapping=mapping,
                pages=pages,
                region=region,
            )
        )

    def read_produto(self, produto_id: int, current_user: models.User):
        """Handle Read produto in this request workflow."""
        return self._runtime.read_produto(produto_id=produto_id, current_user=current_user)

    def list_produtos(self, skip: int, limit: int, sort_by: Optional[str], sort_order: Optional[str], search: Optional[str], fornecedor_id: Optional[int], categoria: Optional[str], status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum], status_titulo_ia: Optional[models.StatusGeracaoIAEnum], status_descricao_ia: Optional[models.StatusGeracaoIAEnum], product_type_id: Optional[int], current_user: models.User):
        """Execute list produtos as part of this module workflow."""
        return self._runtime.list_produtos(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search, fornecedor_id=fornecedor_id, categoria=categoria, status_enriquecimento_web=status_enriquecimento_web, status_titulo_ia=status_titulo_ia, status_descricao_ia=status_descricao_ia, product_type_id=product_type_id, current_user=current_user)

    def update_produto(self, produto_id: int, produto_update: schemas.ProdutoUpdate, current_user: models.User):
        """Update produto and persist the resulting state changes."""
        return self._runtime.update_produto(
            produto_id=produto_id,
            produto_update=produto_update,
            current_user=current_user,
        )

    def delete_produto(self, produto_id: int, current_user: models.User):
        """Execute delete produto as part of this module workflow."""
        return self._runtime.delete_produto(produto_id=produto_id, current_user=current_user)

    def batch_delete_produtos(self, produto_ids: List[int], current_user: models.User):
        """Handle Batch delete produtos in this request workflow."""
        return self._runtime.batch_delete_produtos(produto_ids=produto_ids, current_user=current_user)

    async def upload_produto_image(self, produto_id: int, file: UploadFile, current_user: models.User):
        """Handle Upload produto image in this request workflow."""
        return await self._await_if_needed(
            self._runtime.upload_produto_image(
                produto_id=produto_id,
                file=file,
                current_user=current_user,
            )
        )

    async def importar_catalogo_preview(self, file: UploadFile, fornecedor_id: Optional[int], start_page: int, page_count: int, dpi: int, user_id: int) -> schemas.ImportPreviewResponse:
        """Handle Importar catalogo preview in this request workflow."""
        result = await self._await_if_needed(
            self._runtime.importar_catalogo_preview(
                file=file,
                fornecedor_id=fornecedor_id,
                start_page=start_page,
                page_count=page_count,
                dpi=dpi,
                user_id=user_id,
            )
        )
        if isinstance(result, schemas.ImportPreviewResponse):
            return result
        if isinstance(result, dict):
            return schemas.ImportPreviewResponse(**result)
        return result

    async def importar_catalogo_fornecedor(self, fornecedor_id: int, file: UploadFile, mapeamento_colunas_usuario: Optional[str], current_user: models.User):
        """Handle Importar catalogo fornecedor in this request workflow."""
        return await self._await_if_needed(
            self._runtime.importar_catalogo_fornecedor(
                fornecedor_id=fornecedor_id,
                file=file,
                mapeamento_colunas_usuario=mapeamento_colunas_usuario,
                current_user=current_user,
            )
        )

    async def importar_catalogo_finalizar(self, background_tasks: BackgroundTasks, file_id: int, product_type_id: int, fornecedor_id: int, mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar in this request workflow."""
        return await self._await_if_needed(
            self._runtime.importar_catalogo_finalizar(
                background_tasks=background_tasks,
                file_id=file_id,
                product_type_id=product_type_id,
                fornecedor_id=fornecedor_id,
                mapping=mapping,
                pages=pages,
                region=region,
                extraction_mode=extraction_mode,
                user_id=user_id,
            )
        )

    def importar_catalogo_status(self, file_id: int, user_id: int):
        """Handle Importar catalogo status in this request workflow."""
        return self._runtime.importar_catalogo_status(file_id=file_id, user_id=user_id)

    def importar_catalogo_status_simple(self, file_id: int, user_id: int):
        """Handle Importar catalogo status simple in this request workflow."""
        return self._runtime.importar_catalogo_status_simple(file_id=file_id, user_id=user_id)

    def importar_catalogo_result(self, file_id: int, user_id: int):
        """Handle Importar catalogo result in this request workflow."""
        return self._runtime.importar_catalogo_result(file_id=file_id, user_id=user_id)

    async def importar_catalogo_finalizar_todas_paginas(self, file_id: int, start_page: int, mapping: Optional[Dict[str, str]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar todas paginas in this request workflow."""
        return await self._await_if_needed(
            self._runtime.importar_catalogo_finalizar_todas_paginas(
                file_id=file_id,
                start_page=start_page,
                mapping=mapping,
                extraction_mode=extraction_mode,
                user_id=user_id,
            )
        )

    async def selecionar_regiao(self, file_id: int, page: int, bbox: List[float], bbox_norm: Optional[List[float]], user_id: int):
        """Handle Selecionar regiao in this request workflow."""
        return await self._await_if_needed(
            self._runtime.selecionar_regiao(
                file_id=file_id,
                page=page,
                bbox=bbox,
                bbox_norm=bbox_norm,
                user_id=user_id,
            )
        )

    async def extrair_pagina_unica(self, file_id: int, page_number: int, user_id: int):
        """Handle Extrair pagina unica in this request workflow."""
        return await self._await_if_needed(
            self._runtime.extrair_pagina_unica(
                file_id=file_id,
                page_number=page_number,
                user_id=user_id,
            )
        )
class _ProdutosRequestServices:
    """Componente OO principal '_ProdutosRequestServices' do modulo 'produtos'."""

    def __init__(self, *, product_management_service: ProductManagementService, product_media_service: ProductMediaService) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Request Services."""
        self.product_management_service = product_management_service
        self.product_media_service = product_media_service
_build_produtos_request_services = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _ProdutosRequestServices(product_management_service=DependencyContainer.get_product_management_service(session), product_media_service=DependencyContainer.get_product_media_service(session)))

class _ProdutosCatalogRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'produtos'."""

    def __init__(self, *, session: Session, workflow: ProdutosCatalogCoordinator | None=None) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Catalog Request Scope."""
        self._workflow = workflow or ProdutosCatalogCoordinator(runtime=_ProdutosCatalogService(session=session))

    def list_catalog_import_files(self, *, user_id: int, fornecedor_id: Optional[int], skip: int, limit: int) -> schemas.CatalogImportFilePage:
        """Execute list catalog import files as part of this module workflow."""
        return self._workflow.list_catalog_import_files(user_id=user_id, fornecedor_id=fornecedor_id, skip=skip, limit=limit)

    def delete_catalog_import_file(self, *, file_id: int, user_id: int):
        """Execute delete catalog import file as part of this module workflow."""
        return self._workflow.delete_catalog_import_file(file_id=file_id, user_id=user_id)

    async def reprocess_catalog_import_file(self, *, background_tasks: BackgroundTasks, file_id: int, user_id: int, product_type_id: Optional[int], fornecedor_id: Optional[int], mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]]):
        """Handle Reprocess catalog import file in this request workflow."""
        return await self._workflow.reprocess_catalog_import_file(background_tasks=background_tasks, file_id=file_id, user_id=user_id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region)

    async def importar_catalogo_preview(self, *, file: UploadFile, fornecedor_id: Optional[int], start_page: int, page_count: int, dpi: int, user_id: int) -> schemas.ImportPreviewResponse:
        """Handle Importar catalogo preview in this request workflow."""
        return await self._workflow.importar_catalogo_preview(file=file, fornecedor_id=fornecedor_id, start_page=start_page, page_count=page_count, dpi=dpi, user_id=user_id)

    async def importar_catalogo_fornecedor(self, *, fornecedor_id: int, file: UploadFile, mapeamento_colunas_usuario: Optional[str], current_user: models.User):
        """Handle Importar catalogo fornecedor in this request workflow."""
        return await self._workflow.importar_catalogo_fornecedor(fornecedor_id=fornecedor_id, file=file, mapeamento_colunas_usuario=mapeamento_colunas_usuario, current_user=current_user)

    async def importar_catalogo_finalizar(self, *, background_tasks: BackgroundTasks, file_id: int, product_type_id: int, fornecedor_id: int, mapping: Optional[Dict[str, str]], pages: Optional[List[int]], region: Optional[List[float]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar in this request workflow."""
        return await self._workflow.importar_catalogo_finalizar(background_tasks=background_tasks, file_id=file_id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region, extraction_mode=extraction_mode, user_id=user_id)

    def importar_catalogo_status(self, *, file_id: int, user_id: int):
        """Handle Importar catalogo status in this request workflow."""
        return self._workflow.importar_catalogo_status(file_id=file_id, user_id=user_id)

    def importar_catalogo_status_simple(self, *, file_id: int, user_id: int):
        """Handle Importar catalogo status simple in this request workflow."""
        return self._workflow.importar_catalogo_status_simple(file_id=file_id, user_id=user_id)

    def importar_catalogo_result(self, *, file_id: int, user_id: int):
        """Handle Importar catalogo result in this request workflow."""
        return self._workflow.importar_catalogo_result(file_id=file_id, user_id=user_id)

    async def importar_catalogo_finalizar_todas_paginas(self, *, file_id: int, start_page: int, mapping: Optional[Dict[str, str]], extraction_mode: str, user_id: int):
        """Handle Importar catalogo finalizar todas paginas in this request workflow."""
        return await self._workflow.importar_catalogo_finalizar_todas_paginas(file_id=file_id, start_page=start_page, mapping=mapping, extraction_mode=extraction_mode, user_id=user_id)

    async def selecionar_regiao(self, *, file_id: int, page: int, bbox: List[float], bbox_norm: Optional[List[float]], user_id: int):
        """Handle Selecionar regiao in this request workflow."""
        return await self._workflow.selecionar_regiao(file_id=file_id, page=page, bbox=bbox, bbox_norm=bbox_norm, user_id=user_id)

    async def extrair_pagina_unica(self, *, file_id: int, page_number: int, user_id: int):
        """Handle Extrair pagina unica in this request workflow."""
        return await self._workflow.extrair_pagina_unica(file_id=file_id, page_number=page_number, user_id=user_id)

class _ProdutosRequestContext:
    """Componente OO principal '_ProdutosRequestContext' do modulo 'produtos'."""

    def __init__(self, *, request_services: _ProdutosRequestServices, catalog_workflow: _ProdutosCatalogRequestScope) -> None:
        """Initialize injected dependencies and runtime configuration for Produtos Request Context."""
        self.request_services = request_services
        self.catalog_workflow = catalog_workflow
_build_produtos_request_context = ServiceContainerDependencySupport.build_request_scoped_dependency(lambda session: _ProdutosRequestContext(request_services=_build_produtos_request_services(session), catalog_workflow=_ProdutosCatalogRequestScope(session=session)))

class _EndpointHandlers:

    """Represent Endpoint Handlers and centralize its responsibilities inside this module."""
    @router.post('/', response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED)
    def create_produto(produto: schemas.ProdutoCreate, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (create_produto)."""
        return request_services.product_management_service.create_produto(produto=produto, current_user=current_user)

    @router.get('/catalog-import-files/', response_model=schemas.CatalogImportFilePage)
    def list_catalog_import_files(fornecedor_id: Optional[int]=Query(None, description='ID do fornecedor'), skip: int=Query(0, ge=0, description='Numero de itens para pular'), limit: int=Query(10, ge=1, le=100, description='Numero maximo de itens por pagina'), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (list_catalog_import_files)."""
        return request_context.catalog_workflow.list_catalog_import_files(user_id=current_user.id, fornecedor_id=fornecedor_id, skip=skip, limit=limit)

    @router.delete('/catalog-import-files/{file_id}/', response_model=schemas.CatalogImportFileResponse)
    def delete_catalog_import_file(file_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_catalog_import_file)."""
        return request_context.catalog_workflow.delete_catalog_import_file(file_id=file_id, user_id=current_user.id)

    @router.post('/catalog-import-files/{file_id}/reprocess/', status_code=status.HTTP_202_ACCEPTED)
    async def reprocess_catalog_import_file(background_tasks: BackgroundTasks, file_id: int, product_type_id: Optional[int]=Body(None, embed=True), fornecedor_id: Optional[int]=Body(None, embed=True), mapping: Optional[Dict[str, str]]=Body(None), pages: Optional[List[int]]=Body(None), region: Optional[List[float]]=Body(None), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (reprocess_catalog_import_file)."""
        return await request_context.catalog_workflow.reprocess_catalog_import_file(background_tasks=background_tasks, file_id=file_id, user_id=current_user.id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region)

    @router.get('/{produto_id}', response_model=schemas.ProdutoResponse)
    def read_produto(produto_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_produto)."""
        return request_services.product_management_service.read_produto(produto_id=produto_id, current_user=current_user)

    @router.get('/', response_model=schemas.ProdutoPage)
    def read_produtos(skip: int=Query(0, ge=0, description='Numero de itens para pular'), limit: int=Query(10, ge=1, le=200, description='Numero maximo de itens por pagina'), sort_by: Optional[str]=Query(None, description='Campo para ordenacao'), sort_order: Optional[str]=Query('asc', description='Ordem da ordenacao (asc/desc)'), search: Optional[str]=Query(None, description='Termo de busca para nome, descricao, SKU, EAN'), fornecedor_id: Optional[int]=Query(None, description='ID do fornecedor para filtrar produtos'), categoria: Optional[str]=Query(None, description='Categoria para filtrar produtos'), status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum]=Query(None, description='Filtrar por status de enriquecimento web'), status_titulo_ia: Optional[models.StatusGeracaoIAEnum]=Query(None, description='Filtrar por status de geracao de titulo por IA'), status_descricao_ia: Optional[models.StatusGeracaoIAEnum]=Query(None, description='Filtrar por status de geracao de descricao por IA'), product_type_id: Optional[int]=Query(None, description='ID do tipo de produto'), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (read_produtos)."""
        return request_services.product_management_service.list_produtos(skip=skip, limit=limit, sort_by=sort_by, sort_order=sort_order, search=search, fornecedor_id=fornecedor_id, categoria=categoria, status_enriquecimento_web=status_enriquecimento_web, status_titulo_ia=status_titulo_ia, status_descricao_ia=status_descricao_ia, product_type_id=product_type_id, current_user=current_user)

    @router.put('/{produto_id}', response_model=schemas.ProdutoResponse)
    def update_produto(produto_id: int, produto: schemas.ProdutoUpdate, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (update_produto)."""
        return request_services.product_management_service.update_produto(produto_id=produto_id, produto_update=produto, current_user=current_user)

    @router.delete('/{produto_id}', response_model=schemas.ProdutoResponse)
    def delete_produto(produto_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_produto)."""
        return request_services.product_management_service.delete_produto(produto_id=produto_id, current_user=current_user)

    @router.post('/batch-delete/', response_model=List[schemas.ProdutoResponse])
    def batch_delete_produtos(produto_ids: List[int]=Body(...), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (batch_delete_produtos)."""
        return request_services.product_management_service.batch_delete_produtos(produto_ids=produto_ids, current_user=current_user)

    @router.post('/upload-image/{produto_id}', response_model=schemas.ProdutoResponse)
    async def upload_produto_image(produto_id: int, file: UploadFile=File(...), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_services: _ProdutosRequestServices=Depends(_build_produtos_request_services)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (upload_produto_image)."""
        return await request_services.product_media_service.upload_produto_image(produto_id=produto_id, file=file, current_user=current_user)

    @router.post('/importar-catalogo-preview/', response_model=schemas.ImportPreviewResponse)
    async def importar_catalogo_preview(file: UploadFile=File(...), fornecedor_id: Optional[int]=Form(None), start_page: int=Form(1), page_count: int=Form(0), dpi: int=Form(72), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_preview)."""
        return await request_context.catalog_workflow.importar_catalogo_preview(file=file, fornecedor_id=fornecedor_id, start_page=start_page, page_count=page_count, dpi=dpi, user_id=current_user.id)

    @router.post('/importar-catalogo/{fornecedor_id}/', response_model=schemas.ImportCatalogoResponse)
    async def importar_catalogo_fornecedor(fornecedor_id: int, file: UploadFile=File(...), mapeamento_colunas_usuario: Optional[str]=Form(None), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_fornecedor)."""
        return await request_context.catalog_workflow.importar_catalogo_fornecedor(fornecedor_id=fornecedor_id, file=file, mapeamento_colunas_usuario=mapeamento_colunas_usuario, current_user=current_user)

    @router.post('/importar-catalogo-finalizar/{file_id}/', status_code=status.HTTP_202_ACCEPTED)
    async def importar_catalogo_finalizar(background_tasks: BackgroundTasks, file_id: int, product_type_id: int=Body(..., embed=True), fornecedor_id: int=Body(..., embed=True), mapping: Optional[Dict[str, str]]=Body(None), pages: Optional[List[int]]=Body(None), region: Optional[List[float]]=Body(None), extraction_mode: str=Body("ocr", embed=True), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_finalizar)."""
        return await request_context.catalog_workflow.importar_catalogo_finalizar(background_tasks=background_tasks, file_id=file_id, product_type_id=product_type_id, fornecedor_id=fornecedor_id, mapping=mapping, pages=pages, region=region, extraction_mode=extraction_mode, user_id=current_user.id)

    @router.get('/importar-catalogo-status/{file_id}/', response_model=schemas.CatalogImportFileResponse)
    def importar_catalogo_status(file_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_status)."""
        return request_context.catalog_workflow.importar_catalogo_status(file_id=file_id, user_id=current_user.id)

    @router.get('/importar-catalogo-status/{file_id}', response_model=schemas.CatalogImportStatus, include_in_schema=False)
    def importar_catalogo_status_simple(file_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_status_simple)."""
        return request_context.catalog_workflow.importar_catalogo_status_simple(file_id=file_id, user_id=current_user.id)

    @router.get('/importar-catalogo-result/{file_id}/', response_model=Union[schemas.CatalogImportResult, schemas.CatalogImportResultPending])
    def importar_catalogo_result(file_id: int, current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_result)."""
        return request_context.catalog_workflow.importar_catalogo_result(file_id=file_id, user_id=current_user.id)

    @router.post('/importar-catalogo-finalizar/', response_model=schemas.CatalogImportResult)
    async def importar_catalogo_finalizar_todas_paginas(file_id: int=Body(..., embed=True), start_page: int=Body(1, embed=True), mapping: Optional[Dict[str, str]]=Body(None), extraction_mode: str=Body("ocr", embed=True), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_finalizar_todas_paginas)."""
        return await request_context.catalog_workflow.importar_catalogo_finalizar_todas_paginas(file_id=file_id, start_page=start_page, mapping=mapping, extraction_mode=extraction_mode, user_id=current_user.id)

    @router.post('/selecionar-regiao/', response_model=schemas.RegionExtractionResponse)
    async def selecionar_regiao(file_id: int=Body(..., embed=True), page: int=Body(..., embed=True), bbox: List[float]=Body(..., embed=True), bbox_norm: Optional[List[float]]=Body(None, embed=True), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (selecionar_regiao)."""
        return await request_context.catalog_workflow.selecionar_regiao(file_id=file_id, page=page, bbox=bbox, bbox_norm=bbox_norm, user_id=current_user.id)

    @router.post('/extrair-pagina-unica/', response_model=schemas.SinglePageExtractionResponse)
    async def extrair_pagina_unica(file_id: int=Body(..., embed=True), page_number: int=Body(..., embed=True), current_user: models.User=Depends(_CURRENT_ACTIVE_USER_PROVIDER), request_context: _ProdutosRequestContext=Depends(_build_produtos_request_context)):
        """Endpoint HTTP que delega a execucao para workflow/servico OO (extrair_pagina_unica)."""
        return await request_context.catalog_workflow.extrair_pagina_unica(file_id=file_id, page_number=page_number, user_id=current_user.id)
router.add_api_route('/{produto_id}/', _EndpointHandlers.read_produto, methods=['GET'], response_model=schemas.ProdutoResponse, include_in_schema=False)
router.add_api_route('/{produto_id}/', _EndpointHandlers.update_produto, methods=['PUT'], response_model=schemas.ProdutoResponse, include_in_schema=False)
router.add_api_route('/{produto_id}/', _EndpointHandlers.delete_produto, methods=['DELETE'], response_model=schemas.ProdutoResponse, include_in_schema=False)



