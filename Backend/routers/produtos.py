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
from sqlalchemy.orm import Session

from Backend import crud
from Backend import crud_fornecedores
from Backend import crud_historico
from Backend import crud_product_types
from Backend import crud_produtos
from Backend import database
from Backend import models
from Backend import schemas
from Backend.application.services import (
    CatalogImportDiagnosticsService,
    CatalogImportFileService,
    CatalogImportFinalizeService,
    CatalogImportLegacyIngestService,
    CatalogImportPreviewService,
    CatalogImportQualityService,
    CatalogImportSanitizationService,
    CatalogImportStartService,
    CatalogImportStatusService,
    CatalogImportTaskRunner,
    CatalogImportWorkflowService,
    ProductManagementService,
    ProductMediaService,
    ValidatorCrewFacade,
)
from Backend.application.services.service_container import service_container
from Backend.core.config import settings

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

catalog_quality_service = CatalogImportQualityService()
catalog_sanitization_service = CatalogImportSanitizationService(
    quality_service=catalog_quality_service
)
file_processing_service = service_container.file_processing


def _is_non_critical_import_reason(reason: str) -> bool:
    return catalog_sanitization_service.is_non_critical_import_reason(reason)


def _avaliar_qualidade_linha_produto(data: Dict[str, Any]) -> Optional[str]:
    return catalog_quality_service.evaluate_product_row_quality(data)


def _classificar_qualidade_linha_produto(data: Dict[str, Any]) -> Dict[str, Any]:
    return catalog_quality_service.classify_product_row_quality(data)


catalog_import_diagnostics_service = CatalogImportDiagnosticsService(
    catalog_log_dir=catalog_log_dir,
    logger=catalog_logger,
    sanitization_service=catalog_sanitization_service,
)

validator_crew = ValidatorCrewFacade(logger=logger)


def _sanitize_produto_extraido(prod: Dict[str, Any]) -> Dict[str, Any]:
    """Alias legado para testes existentes; implementacao real esta no servico."""
    return catalog_sanitization_service.sanitize_extracted_product(prod)


catalog_import_task_runner = CatalogImportTaskRunner(
    logger=logger,
    catalog_logger=catalog_logger,
    models=models,
    schemas=schemas,
    crud_produtos=crud_produtos,
    file_processing_service=file_processing_service,
    validator_crew=validator_crew,
    settings=settings,
    path_cls=Path,
    time_module=time,
    counter_cls=Counter,
    resolve_storage_path=catalog_import_diagnostics_service.resolve_storage_path,
    normalize_import_issue_item=catalog_sanitization_service.normalize_import_issue_item,
    extract_import_error_reason=catalog_sanitization_service.extract_import_error_reason,
    is_non_critical_import_reason=catalog_sanitization_service.is_non_critical_import_reason,
    normalizar_dados_validados=catalog_sanitization_service.normalize_validated_data,
    sanitize_produto_extraido=catalog_sanitization_service.sanitize_extracted_product,
    classificar_qualidade_linha_produto=catalog_quality_service.classify_product_row_quality,
    write_catalog_import_report=catalog_import_diagnostics_service.write_catalog_import_report,
    normalize_import_text=catalog_sanitization_service.normalize_import_text,
)

catalog_import_finalize_service = CatalogImportFinalizeService(
    oop_executor=catalog_import_task_runner.execute,
)
catalog_import_start_service = CatalogImportStartService(
    models=models,
    crud_fornecedores=crud_fornecedores,
    settings=settings,
    resolve_storage_path=catalog_import_diagnostics_service.resolve_storage_path,
    finalize_service=catalog_import_finalize_service,
)
catalog_import_status_service = CatalogImportStatusService(models=models)
catalog_import_workflow_service = CatalogImportWorkflowService(
    start_service=catalog_import_start_service,
    status_service=catalog_import_status_service,
)
catalog_import_file_service = CatalogImportFileService(
    models=models,
    file_processing_service=file_processing_service,
    catalog_import_start_service=catalog_import_start_service,
)
catalog_import_preview_service = CatalogImportPreviewService(
    models=models,
    settings=settings,
    file_processing_service=file_processing_service,
    resolve_storage_path=catalog_import_diagnostics_service.resolve_storage_path,
    logger=logger,
    pdfplumber_module=pdfplumber,
)
catalog_import_legacy_ingest_service = CatalogImportLegacyIngestService(
    schemas=schemas,
    models=models,
    crud_fornecedores=crud_fornecedores,
    crud_produtos=crud_produtos,
    crud_uso_ia=crud,
    crud_historico=crud_historico,
    file_processing_service=file_processing_service,
    normalize_import_issue_item=catalog_sanitization_service.normalize_import_issue_item,
    extract_import_error_reason=catalog_sanitization_service.extract_import_error_reason,
    is_non_critical_import_reason=catalog_sanitization_service.is_non_critical_import_reason,
    sanitize_produto_extraido=catalog_sanitization_service.sanitize_extracted_product,
    classificar_qualidade_linha_produto=catalog_quality_service.classify_product_row_quality,
    json_module=json,
)
product_management_service = ProductManagementService(
    models=models,
    schemas=schemas,
    crud_produtos=crud_produtos,
    crud_fornecedores=crud_fornecedores,
    crud_product_types=crud_product_types,
    crud_historico=crud_historico,
    crud_uso_ia=crud,
)
product_media_service = ProductMediaService(
    crud_produtos=crud_produtos,
    schemas=schemas,
)


class _ProdutosRouterRuntime:
    def create_produto(
        self,
        produto: schemas.ProdutoCreate,
        db: Session,
        current_user: models.User,
    ) -> models.Produto:
        return product_management_service.create_produto(
            db=db,
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
        return catalog_import_file_service.list_user_files(
            db=db,
            user_id=user_id,
            fornecedor_id=fornecedor_id,
            skip=skip,
            limit=limit,
        )

    def delete_catalog_import_file(self, db: Session, file_id: int, user_id: int):
        return catalog_import_file_service.delete_user_file(
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
        return await catalog_import_file_service.reprocess_catalog_file(
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
        return product_management_service.read_produto(
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
        return product_management_service.list_produtos(
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
        return product_management_service.update_produto(
            db=db,
            produto_id=produto_id,
            produto_update=produto_update,
            current_user=current_user,
        )

    def delete_produto(self, db: Session, produto_id: int, current_user: models.User):
        return product_management_service.delete_produto(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )

    def batch_delete_produtos(self, db: Session, produto_ids: List[int], current_user: models.User):
        return product_management_service.batch_delete_produtos(
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
        return await product_media_service.upload_produto_image(
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
        response_payload = await catalog_import_preview_service.importar_catalogo_preview(
            file=file,
            fornecedor_id=fornecedor_id,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
            db=db,
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
        return await catalog_import_legacy_ingest_service.importar_catalogo_fornecedor(
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
        return await catalog_import_workflow_service.importar_catalogo_finalizar(
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
        return catalog_import_workflow_service.importar_catalogo_status(
            file_id=file_id,
            db=db,
            user_id=user_id,
        )

    def importar_catalogo_status_simple(self, file_id: int, db: Session, user_id: int):
        return catalog_import_workflow_service.importar_catalogo_status_simple(
            file_id=file_id,
            db=db,
            user_id=user_id,
        )

    def importar_catalogo_result(self, file_id: int, db: Session, user_id: int):
        return catalog_import_workflow_service.importar_catalogo_result(
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
        return await catalog_import_workflow_service.importar_catalogo_finalizar_todas_paginas(
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
        return catalog_import_preview_service.selecionar_regiao(
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
        return await catalog_import_preview_service.extrair_pagina_unica(
            file_id=file_id,
            page_number=page_number,
            db=db,
            user_id=user_id,
        )


class _ProdutosRouterWorkflow:
    def __init__(self, runtime: Optional[object] = None) -> None:
        self._default_runtime = _ProdutosRouterRuntime()
        self._runtime = runtime or self._default_runtime

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


produtos_router_workflow = _ProdutosRouterWorkflow()


@router.post("/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED)
def create_produto(
    produto: schemas.ProdutoCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.create_produto(
        produto=produto,
        db=db,
        current_user=current_user,
    )


@router.get("/catalog-import-files/", response_model=schemas.CatalogImportFilePage)
def list_catalog_import_files(
    db: Session = Depends(database.get_db),
    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor"),
    skip: int = Query(0, ge=0, description="Numero de itens para pular"),
    limit: int = Query(10, ge=1, le=100, description="Numero maximo de itens por pagina"),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.list_catalog_import_files(
        db=db,
        user_id=current_user.id,
        fornecedor_id=fornecedor_id,
        skip=skip,
        limit=limit,
    )


@router.delete("/catalog-import-files/{file_id}/", response_model=schemas.CatalogImportFileResponse)
def delete_catalog_import_file(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.delete_catalog_import_file(
        db=db,
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.reprocess_catalog_import_file(
        background_tasks=background_tasks,
        db=db,
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.read_produto(
        db=db,
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
    db: Session = Depends(database.get_db),
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
):
    return produtos_router_workflow.list_produtos(
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


@router.put("/{produto_id}", response_model=schemas.ProdutoResponse)
def update_produto(
    produto_id: int,
    produto: schemas.ProdutoUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.update_produto(
        db=db,
        produto_id=produto_id,
        produto_update=produto,
        current_user=current_user,
    )


@router.delete("/{produto_id}", response_model=schemas.ProdutoResponse)
def delete_produto(
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.delete_produto(
        db=db,
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.batch_delete_produtos(
        db=db,
        produto_ids=produto_ids,
        current_user=current_user,
    )


@router.post("/upload-image/{produto_id}", response_model=schemas.ProdutoResponse)
async def upload_produto_image(
    produto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.upload_produto_image(
        db=db,
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.importar_catalogo_preview(
        file=file,
        fornecedor_id=fornecedor_id,
        start_page=start_page,
        page_count=page_count,
        dpi=dpi,
        db=db,
        user_id=current_user.id,
    )


@router.post("/importar-catalogo/{fornecedor_id}/", response_model=schemas.ImportCatalogoResponse)
async def importar_catalogo_fornecedor(
    fornecedor_id: int,
    file: UploadFile = File(...),
    mapeamento_colunas_usuario: Optional[str] = Form(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.importar_catalogo_fornecedor(
        fornecedor_id=fornecedor_id,
        file=file,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        db=db,
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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.importar_catalogo_finalizar(
        background_tasks=background_tasks,
        file_id=file_id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,
        db=db,
        user_id=current_user.id,
    )


@router.get("/importar-catalogo-status/{file_id}/", response_model=schemas.CatalogImportFileResponse)
def importar_catalogo_status(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.importar_catalogo_status(
        file_id=file_id,
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/importar-catalogo-status/{file_id}",
    response_model=schemas.CatalogImportStatus,
    include_in_schema=False,
)
def importar_catalogo_status_simple(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.importar_catalogo_status_simple(
        file_id=file_id,
        db=db,
        user_id=current_user.id,
    )


@router.get(
    "/importar-catalogo-result/{file_id}/",
    response_model=Union[schemas.CatalogImportResult, schemas.CatalogImportResultPending],
)
def importar_catalogo_result(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return produtos_router_workflow.importar_catalogo_result(
        file_id=file_id,
        db=db,
        user_id=current_user.id,
    )


@router.post("/importar-catalogo-finalizar/", response_model=schemas.CatalogImportResult)
async def importar_catalogo_finalizar_todas_paginas(
    file_id: int = Body(..., embed=True),
    start_page: int = Body(1, embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.importar_catalogo_finalizar_todas_paginas(
        file_id=file_id,
        start_page=start_page,
        mapping=mapping,
        db=db,
        user_id=current_user.id,
    )


@router.post("/selecionar-regiao/", response_model=schemas.RegionExtractionResponse)
async def selecionar_regiao(
    file_id: int = Body(..., embed=True),
    page: int = Body(..., embed=True),
    bbox: List[float] = Body(..., embed=True),
    bbox_norm: Optional[List[float]] = Body(None, embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.selecionar_regiao(
        file_id=file_id,
        page=page,
        bbox=bbox,
        bbox_norm=bbox_norm,
        db=db,
        user_id=current_user.id,
    )


@router.post("/extrair-pagina-unica/", response_model=schemas.SinglePageExtractionResponse)
async def extrair_pagina_unica(
    file_id: int = Body(..., embed=True),
    page_number: int = Body(..., embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await produtos_router_workflow.extrair_pagina_unica(
        file_id=file_id,
        page_number=page_number,
        db=db,
        user_id=current_user.id,
    )


class ProdutosRouterLegacyService:
    def create_produto(self, *args, **kwargs):
        return produtos_router_workflow.create_produto(*args, **kwargs)

    def list_catalog_import_files(self, *args, **kwargs):
        return produtos_router_workflow.list_catalog_import_files(*args, **kwargs)

    def delete_catalog_import_file(self, *args, **kwargs):
        return produtos_router_workflow.delete_catalog_import_file(*args, **kwargs)

    async def reprocess_catalog_import_file(self, *args, **kwargs):
        return await produtos_router_workflow.reprocess_catalog_import_file(*args, **kwargs)

    def read_produto(self, *args, **kwargs):
        return produtos_router_workflow.read_produto(*args, **kwargs)

    def list_produtos(self, *args, **kwargs):
        return produtos_router_workflow.list_produtos(*args, **kwargs)

    def update_produto(self, *args, **kwargs):
        return produtos_router_workflow.update_produto(*args, **kwargs)

    def delete_produto(self, *args, **kwargs):
        return produtos_router_workflow.delete_produto(*args, **kwargs)

    def batch_delete_produtos(self, *args, **kwargs):
        return produtos_router_workflow.batch_delete_produtos(*args, **kwargs)

    async def upload_produto_image(self, *args, **kwargs):
        return await produtos_router_workflow.upload_produto_image(*args, **kwargs)

    async def importar_catalogo_preview(self, *args, **kwargs):
        return await produtos_router_workflow.importar_catalogo_preview(*args, **kwargs)

    async def importar_catalogo_fornecedor(self, *args, **kwargs):
        return await produtos_router_workflow.importar_catalogo_fornecedor(*args, **kwargs)

    async def importar_catalogo_finalizar(self, *args, **kwargs):
        return await produtos_router_workflow.importar_catalogo_finalizar(*args, **kwargs)

    def importar_catalogo_status(self, *args, **kwargs):
        return produtos_router_workflow.importar_catalogo_status(*args, **kwargs)

    def importar_catalogo_status_simple(self, *args, **kwargs):
        return produtos_router_workflow.importar_catalogo_status_simple(*args, **kwargs)

    def importar_catalogo_result(self, *args, **kwargs):
        return produtos_router_workflow.importar_catalogo_result(*args, **kwargs)

    async def importar_catalogo_finalizar_todas_paginas(self, *args, **kwargs):
        return await produtos_router_workflow.importar_catalogo_finalizar_todas_paginas(*args, **kwargs)

    async def selecionar_regiao(self, *args, **kwargs):
        return await produtos_router_workflow.selecionar_regiao(*args, **kwargs)

    async def extrair_pagina_unica(self, *args, **kwargs):
        return await produtos_router_workflow.extrair_pagina_unica(*args, **kwargs)


