# Backend/routers/produtos.py

from typing import Any, Dict, List, Optional, Union
from collections import Counter

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
import json
import logging
import time
from logging import FileHandler, Formatter
from pathlib import Path

import pdfplumber
from sqlalchemy import func, or_
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
    CatalogImportLegacyIngestService,
    CatalogImportFinalizeService,
    CatalogImportPreviewService,
    CatalogImportStartService,
    CatalogImportStatusService,
    CatalogImportWorkflowService,
    CatalogImportTaskRunner,
    CatalogImportSanitizationService,
    CatalogImportQualityService,
    ProductManagementService,
    ProductMediaService,
    ValidatorCrewFacade,
)
from Backend.application.services.service_container import service_container
from Backend.core import config
from Backend.core.config import settings
from Backend.database import SessionLocal

from . import auth_utils

router = APIRouter(
    prefix="/produtos",
    tags=["produtos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = logging.getLogger(__name__)

# Logger dedicado para diagnostico da importacao de catalogo.
catalog_log_dir = Path(__file__).resolve().parent.parent / "logs"
catalog_log_dir.mkdir(parents=True, exist_ok=True)
catalog_logger = logging.getLogger("catalogo")
if not catalog_logger.handlers:
    fh = FileHandler(catalog_log_dir / "catalogo.log", encoding="utf-8")
    fh.setFormatter(Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    catalog_logger.addHandler(fh)
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
    legacy_executor=catalog_import_task_runner.execute_legacy,
    oop_executor=catalog_import_task_runner.execute_oop,
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







@router.post(

    "/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED

)  # CORRIGIDO AQUI

def create_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto: schemas.ProdutoCreate,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):
    return product_management_service.create_produto(
        db=db,
        produto=produto,
        current_user=current_user,
    )





@router.get("/catalog-import-files/", response_model=schemas.CatalogImportFilePage)

def list_catalog_import_files(

    db: Session = Depends(database.get_db),

    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor"),

    skip: int = Query(0, ge=0, description="N?mero de itens para pular"),

    limit: int = Query(

        10, ge=1, le=100, description="N?mero m?ximo de itens por p?gina"

    ),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):
    return catalog_import_file_service.list_user_files(
        db=db,
        user_id=current_user.id,
        fornecedor_id=fornecedor_id,
        skip=skip,
        limit=limit,
    )





@router.delete(

    "/catalog-import-files/{file_id}/",

    response_model=schemas.CatalogImportFileResponse,

)

def delete_catalog_import_file(

    file_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):
    return catalog_import_file_service.delete_user_file(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )





@router.post(

    "/catalog-import-files/{file_id}/reprocess/",

    status_code=status.HTTP_202_ACCEPTED,

)

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
    return await catalog_import_file_service.reprocess_catalog_file(
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





@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI

def read_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):
    return product_management_service.read_produto(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )

# Tamb?m exp?e a rota com barra ao final para evitar redirecionamentos que podem

# levar ? perda do cabe?alho Authorization em alguns clientes HTTP.

router.add_api_route(

    "/{produto_id}/",

    read_produto,

    methods=["GET"],

    response_model=schemas.ProdutoResponse,

    include_in_schema=False,

)





@router.get("/", response_model=schemas.ProdutoPage)  # Este j? estava correto

def read_produtos(  # Nome da fun??o mantido como no arquivo do usu?rio

    db: Session = Depends(database.get_db),

    skip: int = Query(0, ge=0, description="N?mero de itens para pular"),

    limit: int = Query(

        10, ge=1, le=200, description="N?mero m?ximo de itens por p?gina"

    ),

    sort_by: Optional[str] = Query(

        None, description="Campo para ordena??o (ex: nome_base, preco_venda)"

    ),  # Ajustado para nome_base

    sort_order: Optional[str] = Query(

        "asc", description="Ordem da ordena??o (asc ou desc)"

    ),

    search: Optional[str] = Query(

        None, description="Termo de busca para nome, descri??o, SKU, EAN"

    ),

    fornecedor_id: Optional[int] = Query(

        None, description="ID do fornecedor para filtrar produtos"

    ),

    categoria: Optional[str] = Query(

        None,

        description="Categoria para filtrar produtos (usa campo categoria_original)",

    ),

    status_enriquecimento_web: Optional[models.StatusEnriquecimentoEnum] = Query(

        None, description="Filtrar por status de enriquecimento web"

    ),

    status_titulo_ia: Optional[models.StatusGeracaoIAEnum] = Query(

        None, description="Filtrar por status de gera??o de t?tulo por IA"

    ),

    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = Query(

        None, description="Filtrar por status de gera??o de descri??o por IA"

    ),

    product_type_id: Optional[int] = Query(

        None, description="ID do Tipo de Produto para filtrar produtos"

    ),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

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

@router.put("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI

def update_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    produto: schemas.ProdutoUpdate,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    return product_management_service.update_produto(
        db=db,
        produto_id=produto_id,
        produto_update=produto,
        current_user=current_user,
    )

@router.delete(

    "/{produto_id}", response_model=schemas.ProdutoResponse

)  # CORRIGIDO AQUI

def delete_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    return product_management_service.delete_produto(
        db=db,
        produto_id=produto_id,
        current_user=current_user,
    )

# Expondo rotas com barra final para opera??es de atualiza??o e dele??o.

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





@router.post(

    "/batch-delete/", response_model=List[schemas.ProdutoResponse]

)  # Este j? estava correto

def batch_delete_produtos(

    produto_ids: List[int] = Body(

        ...

    ),  # Accept list of IDs directly from the request body

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    return product_management_service.batch_delete_produtos(
        db=db,
        produto_ids=produto_ids,
        current_user=current_user,
    )

@router.post(

    "/upload-image/{produto_id}", response_model=schemas.ProdutoResponse

)  # CORRIGIDO AQUI

async def upload_produto_image(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    file: UploadFile = File(...),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    return await product_media_service.upload_produto_image(
        db=db,
        produto_id=produto_id,
        file=file,
        current_user=current_user,
    )

@router.post(

    "/importar-catalogo-preview/", response_model=schemas.ImportPreviewResponse

)

async def importar_catalogo_preview(

    file: UploadFile = File(...),

    fornecedor_id: Optional[int] = Form(None),

    start_page: int = Form(1),

    page_count: int = Form(0),

    dpi: int = Form(72),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Gera preview de um cat?logo enviado e salva o arquivo para posterior processamento."""
    response_payload = await catalog_import_preview_service.importar_catalogo_preview(
        file=file,
        fornecedor_id=fornecedor_id,
        start_page=start_page,
        page_count=page_count,
        dpi=dpi,
        db=db,
        user_id=current_user.id,
    )
    return schemas.ImportPreviewResponse(**response_payload)





@router.post(

    "/importar-catalogo/{fornecedor_id}/",

    response_model=schemas.ImportCatalogoResponse,

)

async def importar_catalogo_fornecedor(

    fornecedor_id: int,

    file: UploadFile = File(...),

    mapeamento_colunas_usuario: Optional[str] = Form(None),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Importa um arquivo de catalogo e cria produtos vinculados ao fornecedor."""
    return await catalog_import_legacy_ingest_service.importar_catalogo_fornecedor(
        fornecedor_id=fornecedor_id,
        file=file,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        db=db,
        current_user=current_user,
    )





@router.post(

    "/importar-catalogo-finalizar/{file_id}/",

    status_code=status.HTTP_202_ACCEPTED,

)

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

    """Agenda o processamento do arquivo salvo e retorna imediatamente."""
    return await catalog_import_workflow_service.importar_catalogo_finalizar(
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





@router.get(

    "/importar-catalogo-status/{file_id}/",

    response_model=schemas.CatalogImportFileResponse,

)

def importar_catalogo_status(

    file_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Retorna o status atual do processamento do cat?logo."""
    return catalog_import_workflow_service.importar_catalogo_status(
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

    """Vers?o simplificada do status de importa??o."""
    return catalog_import_workflow_service.importar_catalogo_status_simple(
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
    return catalog_import_workflow_service.importar_catalogo_result(
        file_id=file_id,
        db=db,
        user_id=current_user.id,
    )





@router.post(

    "/importar-catalogo-finalizar/", response_model=schemas.CatalogImportResult

)

async def importar_catalogo_finalizar_todas_paginas(

    file_id: int = Body(..., embed=True),

    start_page: int = Body(1, embed=True),

    mapping: Optional[Dict[str, str]] = Body(None),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Processa todas as p?ginas de um cat?logo PDF a partir de ``start_page``."""
    return await catalog_import_workflow_service.importar_catalogo_finalizar_todas_paginas(
        file_id=file_id,
        start_page=start_page,
        mapping=mapping,
        db=db,
        user_id=current_user.id,
    )





@router.post(

    "/selecionar-regiao/",

    response_model=schemas.RegionExtractionResponse,

)

async def selecionar_regiao(
    file_id: int = Body(..., embed=True),
    page: int = Body(..., embed=True),
    bbox: List[float] = Body(..., embed=True),
    bbox_norm: Optional[List[float]] = Body(None, embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Extrai linhas tabulares de uma regiao selecionada de um PDF para mapeamento."""
    return catalog_import_preview_service.selecionar_regiao(
        file_id=file_id,
        page=page,
        bbox=bbox,
        bbox_norm=bbox_norm,
        db=db,
        user_id=current_user.id,
    )
@router.post(

    "/extrair-pagina-unica/",

    response_model=schemas.SinglePageExtractionResponse,

)

async def extrair_pagina_unica(

    file_id: int = Body(..., embed=True),

    page_number: int = Body(..., embed=True),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Retorna imagem, texto e tabela de uma unica pagina de um PDF."""
    return await catalog_import_preview_service.extrair_pagina_unica(
        file_id=file_id,
        page_number=page_number,
        db=db,
        user_id=current_user.id,
    )



