"""Camada de transporte HTTP para o dominio 'produtos'."""
# Backend/routers/produtos.py
from collections import Counter
from logging import FileHandler, Formatter
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import inspect
import json
import logging
import time

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
import pdfplumber
from sqlalchemy.orm import Session, sessionmaker

from Backend import models
from Backend import schemas
from Backend.application.services.catalog_import_diagnostics_service import (
    CatalogImportDiagnosticsService,
)
from Backend.application.services.catalog_import_file_service import (
    CatalogImportFileService,
)
from Backend.application.services.catalog_import_finalize_service import (
    CatalogImportFinalizeService,
)
from Backend.application.services.catalog_import_ingest_service import (
    CatalogImportIngestService,
)
from Backend.application.services.catalog_import_preview_service import (
    CatalogImportPreviewService,
)
from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)
from Backend.application.services.catalog_import_start_service import (
    CatalogImportStartService,
)
from Backend.application.services.catalog_import_status_service import (
    CatalogImportStatusService,
)
from Backend.application.services.catalog_import_task_runner import (
    CatalogImportTaskRunner,
)
from Backend.application.services.catalog_import_workflow_service import (
    CatalogImportWorkflowService,
)
from Backend.application.services.product_management_service import (
    ProductManagementService,
)
from Backend.application.services.product_media_service import (
    ProductMediaService,
)
from Backend.application.services.product_repositories import (
    build_product_management_repositories,
    build_product_media_repositories,
)
from Backend.application.services.validator_crew_service import (
    ValidatorCrewService,
)
from Backend.application.services.service_container import (
    DependencyContainer,
    ServiceContainer,
    build_request_scoped_dependency,
)
from Backend.core.config import settings
from Backend.infrastructure.repositories.catalog_import_file_repository import (
    CatalogImportFileRepository,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)

from . import auth_utils

router = APIRouter(
    prefix="/produtos",
    tags=["produtos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = logging.getLogger(__name__)

catalog_log_dir = Path(__file__).resolve().parent.parent / "logs"
catalog_log_dir.mkdir(parents=True, exist_ok=True)

catalog_logger = logging.getLogger("catalogo")
if not catalog_logger.handlers:
    file_handler = FileHandler(catalog_log_dir / "catalogo.log", encoding="utf-8")
    file_handler.setFormatter(Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    catalog_logger.addHandler(file_handler)
    catalog_logger.setLevel(logging.INFO)

produto_repository = ProductRepository
fornecedor_repository = FornecedorRepository
uso_ia_repository = RegistroUsoIARepository
historico_repository = HistoricoRepository
catalog_file_repository = CatalogImportFileRepository

class _ProdutosServiceBundle:
    """Componente OO principal '_ProdutosServiceBundle' do modulo 'produtos'."""
    def __init__(self) -> None:
        self._service_container = ServiceContainer()
        self.file_processing_service = self._service_container.file_processing
        self.catalog_quality_service = CatalogImportQualityService()
        self.catalog_sanitization_service = CatalogImportSanitizationService(
            quality_service=self.catalog_quality_service
        )
        self.catalog_import_diagnostics_service = CatalogImportDiagnosticsService(
            catalog_log_dir=catalog_log_dir,
            logger=catalog_logger,
            sanitization_service=self.catalog_sanitization_service,
        )
        self.validator_crew = ValidatorCrewService(logger=logger)

        self.catalog_import_task_runner = CatalogImportTaskRunner(
            logger=logger,
            catalog_logger=catalog_logger,
            models=models,
            schemas=schemas,
            product_repository=produto_repository,
            catalog_file_repository=catalog_file_repository,
            file_processing_service=self.file_processing_service,
            validator_crew=self.validator_crew,
            settings=settings,
            path_cls=Path,
            time_module=time,
            counter_cls=Counter,
            resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path,
            normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item,
            extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason,
            is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason,
            normalizar_dados_validados=self.catalog_sanitization_service.normalize_validated_data,
            sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product,
            classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality,
            write_catalog_import_report=self.catalog_import_diagnostics_service.write_catalog_import_report,
            normalize_import_text=self.catalog_sanitization_service.normalize_import_text,
        )
        self.catalog_import_finalize_service = CatalogImportFinalizeService(
            oop_executor=self.catalog_import_task_runner.execute,
        )
        self.catalog_import_start_service = CatalogImportStartService(
            models=models,
            fornecedor_repo=fornecedor_repository,
            catalog_file_repository=catalog_file_repository,
            settings=settings,
            resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path,
            finalize_service=self.catalog_import_finalize_service,
        )
        self.catalog_import_status_service = CatalogImportStatusService(
            models=models,
            catalog_file_repository=catalog_file_repository,
        )
        self.catalog_import_workflow_service = CatalogImportWorkflowService(
            start_service=self.catalog_import_start_service,
            status_service=self.catalog_import_status_service,
        )
        self.catalog_import_file_service = CatalogImportFileService(
            models=models,
            file_processing_service=self.file_processing_service,
            catalog_import_start_service=self.catalog_import_start_service,
            catalog_file_repository=catalog_file_repository,
        )
        self.catalog_import_preview_service = CatalogImportPreviewService(
            models=models,
            settings=settings,
            file_processing_service=self.file_processing_service,
            resolve_storage_path=self.catalog_import_diagnostics_service.resolve_storage_path,
            logger=logger,
            pdfplumber_module=pdfplumber,
            catalog_file_repository=catalog_file_repository,
        )
        self.catalog_import_ingest_service = CatalogImportIngestService(
            schemas=schemas,
            models=models,
            fornecedor_repo=fornecedor_repository,
            produto_repo=produto_repository,
            uso_ia_repo=uso_ia_repository,
            historico_repo=historico_repository,
            file_processing_service=self.file_processing_service,
            normalize_import_issue_item=self.catalog_sanitization_service.normalize_import_issue_item,
            extract_import_error_reason=self.catalog_sanitization_service.extract_import_error_reason,
            is_non_critical_import_reason=self.catalog_sanitization_service.is_non_critical_import_reason,
            sanitize_produto_extraido=self.catalog_sanitization_service.sanitize_extracted_product,
            classificar_qualidade_linha_produto=self.catalog_quality_service.classify_product_row_quality,
            json_module=json,
        )

class _ProdutosRouterRuntime:
    """Runtime OO responsavel por integracoes e operacoes de 'produtos'."""
    def __init__(self, *, services: Optional[_ProdutosServiceBundle] = None) -> None:
        self._services = services or _ProdutosServiceBundle()

    @staticmethod
    def _build_product_management_service(db: Session) -> ProductManagementService:
        repos = build_product_management_repositories(
            session=db,
        )
        return ProductManagementService(
            models=models,
            schemas=schemas,
            **repos,
        )

    @staticmethod
    def _build_product_media_service(db: Session) -> ProductMediaService:
        repos = build_product_media_repositories(
            session=db,
        )
        return ProductMediaService(
            schemas=schemas,
            **repos,
        )

    def create_produto(
        self,
        produto: schemas.ProdutoCreate,
        db: Session,
        current_user: models.User,
    ) -> models.Produto:
        return self._build_product_management_service(db).create_produto(
            produto=produto,
            current_user=current_user,
        )

    def list_catalog_import_files(
        self,
        db: Session,
        user_id: int,
        fornecedor_id: Optional[int],
        skip: int,
        limit: int,
    ) -> schemas.CatalogImportFilePage:
        return self._services.catalog_import_file_service.list_user_files(
            catalog_file_repo=CatalogImportFileRepository(db),
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )

    def delete_catalog_import_file(self, db: Session, file_id: int, user_id: int):
        return self._services.catalog_import_file_service.delete_user_file(
            catalog_file_repo=CatalogImportFileRepository(db),
            file_id=file_id,
            user_id=user_id,
        )

    async def reprocess_catalog_import_file(
        self,
        background_tasks: BackgroundTasks,
        db: Session,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: Optional[int],
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
    ):
        return await self._services.catalog_import_file_service.reprocess_catalog_file(
            background_tasks=background_tasks,
            catalog_file_repo=CatalogImportFileRepository(db),
            fornecedor_repo=FornecedorRepository(db),
            db_session_factory=sessionmaker(bind=db.get_bind()),
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

    def read_produto(self, db: Session, produto_id: int, current_user: models.User):
        return self._build_product_management_service(db).read_produto(
            produto_id=produto_id,
            current_user=current_user,
        )

    def list_produtos(
        self,
        db: Session,
        skip: int,
        limit: int,
        sort_by: Optional[str],
        sort_order: Optional[str],
        search: Optional[str],
        fornecedor_id: Optional[int],
        categoria: Optional[str],
        status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum],
        status_titulo_ia: Optional[models.StatusGeracaoIAEnum],
        status_descricao_ia: Optional[models.StatusGeracaoIAEnum],
        product_type_id: Optional[int],
        current_user: models.User,
    ):
        return self._build_product_management_service(db).list_produtos(
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
            product_type_id=product_type_id,
            current_user=current_user,
        )

    def update_produto(
        self,
        db: Session,
        produto_id: int,
        produto_update: schemas.ProdutoUpdate,
        current_user: models.User,
    ):
        return self._build_product_management_service(db).update_produto(
            produto_id=produto_id,
            produto_update=produto_update,
            current_user=current_user,
        )

    def delete_produto(self, db: Session, produto_id: int, current_user: models.User):
        return self._build_product_management_service(db).delete_produto(
            produto_id=produto_id,
            current_user=current_user,
        )

    def batch_delete_produtos(self, db: Session, produto_ids: List[int], current_user: models.User):
        return self._build_product_management_service(db).batch_delete_produtos(
            produto_ids=produto_ids,
            current_user=current_user,
        )

    async def upload_produto_image(
        self,
        db: Session,
        produto_id: int,
        file: UploadFile,
        current_user: models.User,
    ):
        return await self._build_product_media_service(db).upload_produto_image(
            produto_id=produto_id,
            file=file,
            current_user=current_user,
        )

    async def importar_catalogo_preview(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int],
        start_page: int,
        page_count: int,
        dpi: int,
        db: Session,
        user_id: int,
    ) -> schemas.ImportPreviewResponse:
        response_payload = await self._services.catalog_import_preview_service.importar_catalogo_preview(
            file=file,
            fornecedor_id=fornecedor_id,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
            catalog_file_repo=CatalogImportFileRepository(db),
            user_id=user_id,
        )
        return schemas.ImportPreviewResponse(**response_payload)

    async def importar_catalogo_fornecedor(
        self,
        fornecedor_id: int,
        file: UploadFile,
        mapeamento_colunas_usuario: Optional[str],
        db: Session,
        current_user: models.User,
    ):
        return await self._services.catalog_import_ingest_service.importar_catalogo_fornecedor(
            fornecedor_id=fornecedor_id,
            file=file,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            current_user=current_user,
            fornecedor_repo=FornecedorRepository(db),
            produto_repo=ProductRepository(db),
            uso_ia_repo=RegistroUsoIARepository(db),
            historico_repo=HistoricoRepository(db),
        )

    async def importar_catalogo_finalizar(
        self,
        background_tasks: BackgroundTasks,
        file_id: int,
        product_type_id: int,
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
        db: Session,
        user_id: int,
    ):
        return await self._services.catalog_import_workflow_service.importar_catalogo_finalizar(
            background_tasks=background_tasks,
            file_id=file_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            user_id=user_id,
            catalog_file_repo=CatalogImportFileRepository(db),
            fornecedor_repo=FornecedorRepository(db),
            db_session_factory=sessionmaker(bind=db.get_bind()),
        )

    def importar_catalogo_status(self, file_id: int, db: Session, user_id: int):
        return self._services.catalog_import_workflow_service.importar_catalogo_status(
            file_id=file_id,
            user_id=user_id,
            catalog_file_repo=CatalogImportFileRepository(db),
        )

    def importar_catalogo_status_simple(self, file_id: int, db: Session, user_id: int):
        return self._services.catalog_import_workflow_service.importar_catalogo_status_simple(
            file_id=file_id,
            user_id=user_id,
            catalog_file_repo=CatalogImportFileRepository(db),
        )

    def importar_catalogo_result(self, file_id: int, db: Session, user_id: int):
        return self._services.catalog_import_workflow_service.importar_catalogo_result(
            file_id=file_id,
            user_id=user_id,
            catalog_file_repo=CatalogImportFileRepository(db),
        )

    async def importar_catalogo_finalizar_todas_paginas(
        self,
        file_id: int,
        start_page: int,
        mapping: Optional[Dict[str, str]],
        db: Session,
        user_id: int,
    ):
        return await self._services.catalog_import_workflow_service.importar_catalogo_finalizar_todas_paginas(
            file_id=file_id,
            start_page=start_page,
            mapping=mapping,
            user_id=user_id,
            catalog_file_repo=CatalogImportFileRepository(db),
            fornecedor_repo=FornecedorRepository(db),
            db_session_factory=sessionmaker(bind=db.get_bind()),
        )

    async def selecionar_regiao(
        self,
        file_id: int,
        page: int,
        bbox: List[float],
        bbox_norm: Optional[List[float]],
        db: Session,
        user_id: int,
    ):
        return self._services.catalog_import_preview_service.selecionar_regiao(
            file_id=file_id,
            page=page,
            bbox=bbox,
            bbox_norm=bbox_norm,
            catalog_file_repo=CatalogImportFileRepository(db),
            user_id=user_id,
        )

    async def extrair_pagina_unica(
        self,
        file_id: int,
        page_number: int,
        db: Session,
        user_id: int,
    ):
        return await self._services.catalog_import_preview_service.extrair_pagina_unica(
            file_id=file_id,
            page_number=page_number,
            catalog_file_repo=CatalogImportFileRepository(db),
            user_id=user_id,
        )


class _ProdutosRouterWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'produtos'."""
    def __init__(self, runtime: Optional[object] = None) -> None:
        self._default_runtime = _ProdutosRouterRuntime()
        self._runtime = runtime or self._default_runtime

    def set_default_runtime(self, runtime: object) -> None:
        self._default_runtime = runtime

    def _runtime_method(self, method_name: str):
        runtime_method = getattr(self._runtime, method_name, None)
        if runtime_method is not None:
            return runtime_method
        return getattr(self._default_runtime, method_name)

    async def _invoke_async(self, method_name: str, **kwargs):
        result = self._runtime_method(method_name)(**kwargs)
        if inspect.isawaitable(result):
            return await result
        return result

    def create_produto(
        self,
        produto: schemas.ProdutoCreate,
        db: Session,
        current_user: models.User,
    ) -> models.Produto:
        return self._runtime_method("create_produto")(
            produto=produto,
            db=db,
            current_user=current_user,
        )

    def list_catalog_import_files(
        self,
        db: Session,
        user_id: int,
        fornecedor_id: Optional[int],
        skip: int,
        limit: int,
    ) -> schemas.CatalogImportFilePage:
        return self._runtime_method("list_catalog_import_files")(
            db=db,
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )

    def delete_catalog_import_file(self, db: Session, file_id: int, user_id: int):
        return self._runtime_method("delete_catalog_import_file")(
            db=db,
            file_id=file_id,
            user_id=user_id,
        )

    async def reprocess_catalog_import_file(
        self,
        background_tasks: BackgroundTasks,
        db: Session,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: Optional[int],
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
    ):
        return await self._invoke_async(
            "reprocess_catalog_import_file",
            background_tasks=background_tasks,
            db=db,
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

    def read_produto(self, db: Session, produto_id: int, current_user: models.User):
        return self._runtime_method("read_produto")(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )

    def list_produtos(
        self,
        db: Session,
        skip: int,
        limit: int,
        sort_by: Optional[str],
        sort_order: Optional[str],
        search: Optional[str],
        fornecedor_id: Optional[int],
        categoria: Optional[str],
        status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum],
        status_titulo_ia: Optional[models.StatusGeracaoIAEnum],
        status_descricao_ia: Optional[models.StatusGeracaoIAEnum],
        product_type_id: Optional[int],
        current_user: models.User,
    ):
        return self._runtime_method("list_produtos")(
            db=db,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
            product_type_id=product_type_id,
            current_user=current_user,
        )

    def update_produto(
        self,
        db: Session,
        produto_id: int,
        produto_update: schemas.ProdutoUpdate,
        current_user: models.User,
    ):
        return self._runtime_method("update_produto")(
            db=db,
            produto_id=produto_id,
            produto_update=produto_update,
            current_user=current_user,
        )

    def delete_produto(self, db: Session, produto_id: int, current_user: models.User):
        return self._runtime_method("delete_produto")(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )

    def batch_delete_produtos(self, db: Session, produto_ids: List[int], current_user: models.User):
        return self._runtime_method("batch_delete_produtos")(
            db=db,
            produto_ids=produto_ids,
            current_user=current_user,
        )

    async def upload_produto_image(
        self,
        db: Session,
        produto_id: int,
        file: UploadFile,
        current_user: models.User,
    ):
        return await self._invoke_async(
            "upload_produto_image",
            db=db,
            produto_id=produto_id,
            file=file,
            current_user=current_user,
        )

    async def importar_catalogo_preview(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int],
        start_page: int,
        page_count: int,
        dpi: int,
        db: Session,
        user_id: int,
    ) -> schemas.ImportPreviewResponse:
        result = await self._invoke_async(
            "importar_catalogo_preview",
            file=file,
            fornecedor_id=fornecedor_id,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
            db=db,
            user_id=user_id,
        )
        if isinstance(result, schemas.ImportPreviewResponse):
            return result
        if isinstance(result, dict):
            return schemas.ImportPreviewResponse(**result)
        return result

    async def importar_catalogo_fornecedor(
        self,
        fornecedor_id: int,
        file: UploadFile,
        mapeamento_colunas_usuario: Optional[str],
        db: Session,
        current_user: models.User,
    ):
        return await self._invoke_async(
            "importar_catalogo_fornecedor",
            fornecedor_id=fornecedor_id,
            file=file,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            db=db,
            current_user=current_user,
        )

    async def importar_catalogo_finalizar(
        self,
        background_tasks: BackgroundTasks,
        file_id: int,
        product_type_id: int,
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
        db: Session,
        user_id: int,
    ):
        return await self._invoke_async(
            "importar_catalogo_finalizar",
            background_tasks=background_tasks,
            file_id=file_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            db=db,
            user_id=user_id,
        )

    def importar_catalogo_status(self, file_id: int, db: Session, user_id: int):
        return self._runtime_method("importar_catalogo_status")(
            file_id=file_id,
            db=db,
            user_id=user_id,
        )

    def importar_catalogo_status_simple(self, file_id: int, db: Session, user_id: int):
        return self._runtime_method("importar_catalogo_status_simple")(
            file_id=file_id,
            db=db,
            user_id=user_id,
        )

    def importar_catalogo_result(self, file_id: int, db: Session, user_id: int):
        return self._runtime_method("importar_catalogo_result")(
            file_id=file_id,
            db=db,
            user_id=user_id,
        )

    async def importar_catalogo_finalizar_todas_paginas(
        self,
        file_id: int,
        start_page: int,
        mapping: Optional[Dict[str, str]],
        db: Session,
        user_id: int,
    ):
        return await self._invoke_async(
            "importar_catalogo_finalizar_todas_paginas",
            file_id=file_id,
            start_page=start_page,
            mapping=mapping,
            db=db,
            user_id=user_id,
        )

    async def selecionar_regiao(
        self,
        file_id: int,
        page: int,
        bbox: List[float],
        bbox_norm: Optional[List[float]],
        db: Session,
        user_id: int,
    ):
        return await self._invoke_async(
            "selecionar_regiao",
            file_id=file_id,
            page=page,
            bbox=bbox,
            bbox_norm=bbox_norm,
            db=db,
            user_id=user_id,
        )

    async def extrair_pagina_unica(
        self,
        file_id: int,
        page_number: int,
        db: Session,
        user_id: int,
    ):
        return await self._invoke_async(
            "extrair_pagina_unica",
            file_id=file_id,
            page_number=page_number,
            db=db,
            user_id=user_id,
        )


ProdutosRouterWorkflow = _ProdutosRouterWorkflow


class _ProdutosRequestServices:
    """Componente OO principal '_ProdutosRequestServices' do modulo 'produtos'."""
    def __init__(
        self,
        *,
        product_management_service: ProductManagementService,
        product_media_service: ProductMediaService,
    ) -> None:
        self.product_management_service = product_management_service
        self.product_media_service = product_media_service


_build_produtos_request_services = build_request_scoped_dependency(
    lambda session: _ProdutosRequestServices(
        product_management_service=DependencyContainer.get_product_management_service(
            db=session
        ),
        product_media_service=DependencyContainer.get_product_media_service(db=session),
    )
)


class _ProdutosCatalogRequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'produtos'."""
    def __init__(self, *, db: Session, workflow: ProdutosRouterWorkflow | None = None) -> None:
        self._db = db
        self._workflow = workflow or ProdutosRouterWorkflow()

    def list_catalog_import_files(
        self,
        *,
        user_id: int,
        fornecedor_id: Optional[int],
        skip: int,
        limit: int,
    ) -> schemas.CatalogImportFilePage:
        return self._workflow.list_catalog_import_files(
            db=self._db,
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )

    def delete_catalog_import_file(self, *, file_id: int, user_id: int):
        return self._workflow.delete_catalog_import_file(
            db=self._db,
            file_id=file_id,
            user_id=user_id,
        )

    async def reprocess_catalog_import_file(
        self,
        *,
        background_tasks: BackgroundTasks,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: Optional[int],
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
    ):
        return await self._workflow.reprocess_catalog_import_file(
            background_tasks=background_tasks,
            db=self._db,
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )

    async def importar_catalogo_preview(
        self,
        *,
        file: UploadFile,
        fornecedor_id: Optional[int],
        start_page: int,
        page_count: int,
        dpi: int,
        user_id: int,
    ) -> schemas.ImportPreviewResponse:
        return await self._workflow.importar_catalogo_preview(
            file=file,
            fornecedor_id=fornecedor_id,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
            db=self._db,
            user_id=user_id,
        )

    async def importar_catalogo_fornecedor(
        self,
        *,
        fornecedor_id: int,
        file: UploadFile,
        mapeamento_colunas_usuario: Optional[str],
        current_user: models.User,
    ):
        return await self._workflow.importar_catalogo_fornecedor(
            fornecedor_id=fornecedor_id,
            file=file,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            db=self._db,
            current_user=current_user,
        )

    async def importar_catalogo_finalizar(
        self,
        *,
        background_tasks: BackgroundTasks,
        file_id: int,
        product_type_id: int,
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]],
        pages: Optional[List[int]],
        region: Optional[List[float]],
        user_id: int,
    ):
        return await self._workflow.importar_catalogo_finalizar(
            background_tasks=background_tasks,
            file_id=file_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            db=self._db,
            user_id=user_id,
        )

    def importar_catalogo_status(self, *, file_id: int, user_id: int):
        return self._workflow.importar_catalogo_status(
            file_id=file_id,
            db=self._db,
            user_id=user_id,
        )

    def importar_catalogo_status_simple(self, *, file_id: int, user_id: int):
        return self._workflow.importar_catalogo_status_simple(
            file_id=file_id,
            db=self._db,
            user_id=user_id,
        )

    def importar_catalogo_result(self, *, file_id: int, user_id: int):
        return self._workflow.importar_catalogo_result(
            file_id=file_id,
            db=self._db,
            user_id=user_id,
        )

    async def importar_catalogo_finalizar_todas_paginas(
        self,
        *,
        file_id: int,
        start_page: int,
        mapping: Optional[Dict[str, str]],
        user_id: int,
    ):
        return await self._workflow.importar_catalogo_finalizar_todas_paginas(
            file_id=file_id,
            start_page=start_page,
            mapping=mapping,
            db=self._db,
            user_id=user_id,
        )

    async def selecionar_regiao(
        self,
        *,
        file_id: int,
        page: int,
        bbox: List[float],
        bbox_norm: Optional[List[float]],
        user_id: int,
    ):
        return await self._workflow.selecionar_regiao(
            file_id=file_id,
            page=page,
            bbox=bbox,
            bbox_norm=bbox_norm,
            db=self._db,
            user_id=user_id,
        )

    async def extrair_pagina_unica(
        self,
        *,
        file_id: int,
        page_number: int,
        user_id: int,
    ):
        return await self._workflow.extrair_pagina_unica(
            file_id=file_id,
            page_number=page_number,
            db=self._db,
            user_id=user_id,
        )


class _ProdutosRequestContext:
    """Componente OO principal '_ProdutosRequestContext' do modulo 'produtos'."""
    def __init__(
        self,
        *,
        request_services: _ProdutosRequestServices,
        catalog_workflow: _ProdutosCatalogRequestScope,
    ) -> None:
        self.request_services = request_services
        self.catalog_workflow = catalog_workflow


_build_produtos_request_context = build_request_scoped_dependency(
    lambda session: _ProdutosRequestContext(
        request_services=_build_produtos_request_services(session),
        catalog_workflow=_ProdutosCatalogRequestScope(db=session),
    )
)


@router.post("/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED)
def create_produto(
    produto: schemas.ProdutoCreate,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (create_produto)."""
    return request_services.product_management_service.create_produto(
        produto=produto,
        current_user=current_user,
    )


@router.get("/catalog-import-files/", response_model=schemas.CatalogImportFilePage)
def list_catalog_import_files(
    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor"),
    skip: int = Query(0, ge=0, description="Numero de itens para pular"),
    limit: int = Query(10, ge=1, le=100, description="Numero maximo de itens por pagina"),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (list_catalog_import_files)."""
    return request_context.catalog_workflow.list_catalog_import_files(

        user_id=current_user.id,
        fornecedor_id=fornecedor_id,
        skip=skip,
        limit=limit,
    )


@router.delete("/catalog-import-files/{file_id}/", response_model=schemas.CatalogImportFileResponse)
def delete_catalog_import_file(
    file_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_catalog_import_file)."""
    return request_context.catalog_workflow.delete_catalog_import_file(

        file_id=file_id,
        user_id=current_user.id,
    )


@router.post("/catalog-import-files/{file_id}/reprocess/", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_catalog_import_file(
    background_tasks: BackgroundTasks,
    file_id: int,
    product_type_id: Optional[int] = Body(None, embed=True),
    fornecedor_id: Optional[int] = Body(None, embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    pages: Optional[List[int]] = Body(None),
    region: Optional[List[float]] = Body(None),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (reprocess_catalog_import_file)."""
    return await request_context.catalog_workflow.reprocess_catalog_import_file(
        background_tasks=background_tasks,

        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,
    )


@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)
def read_produto(
    produto_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (read_produto)."""
    return request_services.product_management_service.read_produto(
        produto_id=produto_id,
        current_user=current_user,
    )


router.add_api_route(
    "/{produto_id}/",
    read_produto,
    methods=["GET"],
    response_model=schemas.ProdutoResponse,
    include_in_schema=False,
)


@router.get("/", response_model=schemas.ProdutoPage)
def read_produtos(
    skip: int = Query(0, ge=0, description="Numero de itens para pular"),
    limit: int = Query(10, ge=1, le=200, description="Numero maximo de itens por pagina"),
    sort_by: Optional[str] = Query(None, description="Campo para ordenacao"),
    sort_order: Optional[str] = Query("asc", description="Ordem da ordenacao (asc/desc)"),
    search: Optional[str] = Query(None, description="Termo de busca para nome, descricao, SKU, EAN"),
    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor para filtrar produtos"),
    categoria: Optional[str] = Query(None, description="Categoria para filtrar produtos"),
    status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum] = Query(
        None,
        description="Filtrar por status de enriquecimento web",
    ),
    status_titulo_ia: Optional[models.StatusGeracaoIAEnum] = Query(
        None,
        description="Filtrar por status de geracao de titulo por IA",
    ),
    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = Query(
        None,
        description="Filtrar por status de geracao de descricao por IA",
    ),
    product_type_id: Optional[int] = Query(None, description="ID do tipo de produto"),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (read_produtos)."""
    return request_services.product_management_service.list_produtos(
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        fornecedor_id=fornecedor_id,
        categoria=categoria,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
        product_type_id=product_type_id,
        current_user=current_user,
    )


@router.put("/{produto_id}", response_model=schemas.ProdutoResponse)
def update_produto(
    produto_id: int,
    produto: schemas.ProdutoUpdate,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (update_produto)."""
    return request_services.product_management_service.update_produto(
        produto_id=produto_id,
        produto_update=produto,
        current_user=current_user,
    )


@router.delete("/{produto_id}", response_model=schemas.ProdutoResponse)
def delete_produto(
    produto_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (delete_produto)."""
    return request_services.product_management_service.delete_produto(
        produto_id=produto_id,
        current_user=current_user,
    )


router.add_api_route(
    "/{produto_id}/",
    update_produto,
    methods=["PUT"],
    response_model=schemas.ProdutoResponse,
    include_in_schema=False,
)

router.add_api_route(
    "/{produto_id}/",
    delete_produto,
    methods=["DELETE"],
    response_model=schemas.ProdutoResponse,
    include_in_schema=False,
)


@router.post("/batch-delete/", response_model=List[schemas.ProdutoResponse])
def batch_delete_produtos(
    produto_ids: List[int] = Body(...),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (batch_delete_produtos)."""
    return request_services.product_management_service.batch_delete_produtos(
        produto_ids=produto_ids,
        current_user=current_user,
    )


@router.post("/upload-image/{produto_id}", response_model=schemas.ProdutoResponse)
async def upload_produto_image(
    produto_id: int,
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_services: _ProdutosRequestServices = Depends(_build_produtos_request_services),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (upload_produto_image)."""
    return await request_services.product_media_service.upload_produto_image(
        produto_id=produto_id,
        file=file,
        current_user=current_user,
    )


@router.post("/importar-catalogo-preview/", response_model=schemas.ImportPreviewResponse)
async def importar_catalogo_preview(
    file: UploadFile = File(...),
    fornecedor_id: Optional[int] = Form(None),
    start_page: int = Form(1),
    page_count: int = Form(0),
    dpi: int = Form(72),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_preview)."""
    return await request_context.catalog_workflow.importar_catalogo_preview(
        file=file,
        fornecedor_id=fornecedor_id,
        start_page=start_page,
        page_count=page_count,
        dpi=dpi,

        user_id=current_user.id,
    )


@router.post("/importar-catalogo/{fornecedor_id}/", response_model=schemas.ImportCatalogoResponse)
async def importar_catalogo_fornecedor(
    fornecedor_id: int,
    file: UploadFile = File(...),
    mapeamento_colunas_usuario: Optional[str] = Form(None),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_fornecedor)."""
    return await request_context.catalog_workflow.importar_catalogo_fornecedor(
        fornecedor_id=fornecedor_id,
        file=file,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,

        current_user=current_user,
    )


@router.post("/importar-catalogo-finalizar/{file_id}/", status_code=status.HTTP_202_ACCEPTED)
async def importar_catalogo_finalizar(
    background_tasks: BackgroundTasks,
    file_id: int,
    product_type_id: int = Body(..., embed=True),
    fornecedor_id: int = Body(..., embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    pages: Optional[List[int]] = Body(None),
    region: Optional[List[float]] = Body(None),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_finalizar)."""
    return await request_context.catalog_workflow.importar_catalogo_finalizar(
        background_tasks=background_tasks,
        file_id=file_id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,

        user_id=current_user.id,
    )


@router.get("/importar-catalogo-status/{file_id}/", response_model=schemas.CatalogImportFileResponse)
def importar_catalogo_status(
    file_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_status)."""
    return request_context.catalog_workflow.importar_catalogo_status(
        file_id=file_id,

        user_id=current_user.id,
    )


@router.get(
    "/importar-catalogo-status/{file_id}",
    response_model=schemas.CatalogImportStatus,
    include_in_schema=False,
)
def importar_catalogo_status_simple(
    file_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_status_simple)."""
    return request_context.catalog_workflow.importar_catalogo_status_simple(
        file_id=file_id,

        user_id=current_user.id,
    )


@router.get(
    "/importar-catalogo-result/{file_id}/",
    response_model=Union[schemas.CatalogImportResult, schemas.CatalogImportResultPending],
)
def importar_catalogo_result(
    file_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_result)."""
    return request_context.catalog_workflow.importar_catalogo_result(
        file_id=file_id,

        user_id=current_user.id,
    )


@router.post("/importar-catalogo-finalizar/", response_model=schemas.CatalogImportResult)
async def importar_catalogo_finalizar_todas_paginas(
    file_id: int = Body(..., embed=True),
    start_page: int = Body(1, embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (importar_catalogo_finalizar_todas_paginas)."""
    return await request_context.catalog_workflow.importar_catalogo_finalizar_todas_paginas(
        file_id=file_id,
        start_page=start_page,
        mapping=mapping,

        user_id=current_user.id,
    )


@router.post("/selecionar-regiao/", response_model=schemas.RegionExtractionResponse)
async def selecionar_regiao(
    file_id: int = Body(..., embed=True),
    page: int = Body(..., embed=True),
    bbox: List[float] = Body(..., embed=True),
    bbox_norm: Optional[List[float]] = Body(None, embed=True),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (selecionar_regiao)."""
    return await request_context.catalog_workflow.selecionar_regiao(
        file_id=file_id,
        page=page,
        bbox=bbox,
        bbox_norm=bbox_norm,

        user_id=current_user.id,
    )


@router.post("/extrair-pagina-unica/", response_model=schemas.SinglePageExtractionResponse)
async def extrair_pagina_unica(
    file_id: int = Body(..., embed=True),
    page_number: int = Body(..., embed=True),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_context: _ProdutosRequestContext = Depends(_build_produtos_request_context),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (extrair_pagina_unica)."""
    return await request_context.catalog_workflow.extrair_pagina_unica(
        file_id=file_id,
        page_number=page_number,

        user_id=current_user.id,
    )








