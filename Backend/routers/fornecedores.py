# Backend/routers/fornecedores.py
from typing import List, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func
from sqlalchemy.orm import Session

from Backend import crud_fornecedor_import_jobs
from Backend import crud_fornecedores
from Backend import crud_historico
from Backend import crud_produtos
from Backend import database
from Backend import models
from Backend import schemas
from Backend.application.services.fornecedor_catalog_process_service import (
    FornecedorCatalogProcessService,
)
from Backend.application.services.fornecedor_import_job_service import (
    FornecedorImportJobService,
)
from Backend.application.services.fornecedor_import_tracking_service import (
    FornecedorImportTrackingService,
)
from Backend.application.services.fornecedor_management_service import (
    FornecedorManagementService,
)
from Backend.application.services.fornecedor_preview_service import (
    FornecedorPreviewService,
)
from Backend.application.services.service_container import service_container
from Backend.core.logging_config import get_logger
from Backend.tasks import process_pdf_extraction_task

from . import auth_utils
from Backend.routers.produtos import catalog_import_start_service

logger = get_logger(__name__)

file_processing_service = service_container.file_processing
web_data_extractor_service = service_container.web_data_extractor
fornecedor_catalog_process_service = FornecedorCatalogProcessService(
    models=models,
    crud_fornecedores=crud_fornecedores,
    catalog_import_start_service=catalog_import_start_service,
)
fornecedor_import_job_service = FornecedorImportJobService(
    crud_fornecedor_import_jobs=crud_fornecedor_import_jobs,
    crud_produtos=crud_produtos,
    produto_create_schema=schemas.ProdutoCreate,
)
fornecedor_import_tracking_service = FornecedorImportTrackingService(
    models=models,
    process_pdf_extraction_task=process_pdf_extraction_task,
)
fornecedor_management_service = FornecedorManagementService(
    models=models,
    schemas=schemas,
    crud_fornecedores=crud_fornecedores,
    crud_historico=crud_historico,
    sqlalchemy_func=func,
)
fornecedor_preview_service = FornecedorPreviewService(
    file_processing_service=file_processing_service,
    web_data_extractor_service=web_data_extractor_service,
)

router = APIRouter(
    prefix="/fornecedores",
    tags=["fornecedores"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)


class _FornecedoresRouterWorkflow:
    def create_fornecedor(
        self,
        fornecedor: schemas.FornecedorCreate,
        db: Session,
        current_user: models.User,
    ) -> models.Fornecedor:
        logger.info("Requisicao para criar fornecedor recebida.")
        return fornecedor_management_service.create_fornecedor(
            db=db,
            fornecedor=fornecedor,
            current_user=current_user,
        )

    def list_fornecedores_page(
        self,
        db: Session,
        current_user: models.User,
        skip: int,
        limit: int,
        termo_busca: Optional[str],
    ) -> schemas.FornecedorPage:
        return fornecedor_management_service.list_fornecedores_page(
            db=db,
            current_user=current_user,
            skip=skip,
            limit=limit,
            termo_busca=termo_busca,
        )

    def read_fornecedor(
        self,
        fornecedor_id: int,
        db: Session,
        current_user: models.User,
    ) -> models.Fornecedor:
        return fornecedor_management_service.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado ou nao pertence ao usuario",
            forbidden_detail="Nao autorizado a acessar este fornecedor.",
        )

    def update_fornecedor(
        self,
        fornecedor_id: int,
        fornecedor_update: schemas.FornecedorUpdate,
        db: Session,
        current_user: models.User,
    ) -> models.Fornecedor:
        return fornecedor_management_service.update_fornecedor(
            db=db,
            fornecedor_id=fornecedor_id,
            fornecedor_update=fornecedor_update,
            current_user=current_user,
        )

    def get_mapping(
        self,
        fornecedor_id: int,
        db: Session,
        current_user: models.User,
    ) -> Optional[dict]:
        return fornecedor_management_service.get_mapping(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )

    def update_mapping(
        self,
        fornecedor_id: int,
        mapping: Optional[dict],
        db: Session,
        current_user: models.User,
    ) -> models.Fornecedor:
        return fornecedor_management_service.update_mapping(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            mapping=mapping,
        )

    async def preview_pages(self, file: UploadFile):
        return await fornecedor_preview_service.preview_pages(file=file)

    async def preview_pdf(
        self,
        fornecedor_id: int,
        file: UploadFile,
        db: Session,
        current_user: models.User,
        offset: int,
        limit: int,
    ) -> schemas.PdfPreviewResponse:
        _ = fornecedor_management_service.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado",
            forbidden_detail="Nao autorizado a acessar este fornecedor.",
        )

        return fornecedor_preview_service.preview_pdf(
            db=db,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )

    def preview_catalog_from_region(
        self,
        preview_request: schemas.CatalogRegionPreviewRequest,
        db: Session,
    ) -> schemas.CatalogPreview:
        return fornecedor_preview_service.preview_catalog_from_region(
            db=db,
            file_id=preview_request.file_id,
            page_number=preview_request.page_number,
            region=preview_request.region,
        )

    def extract_data_from_pdf_bulk(
        self,
        background_tasks: BackgroundTasks,
        request: schemas.PdfRegionBulkRequest,
        db: Session,
    ):
        return fornecedor_preview_service.extract_data_from_pdf_bulk(
            background_tasks=background_tasks,
            db=db,
            file_id=request.file_id,
            region=request.region,
            pages=request.pages,
            all_pages=request.all_pages,
        )

    def get_import_progress(
        self,
        job_id: int,
        db: Session,
        current_user: models.User,
    ) -> dict:
        record = fornecedor_import_tracking_service.get_catalog_record_or_404(
            db=db,
            file_id=job_id,
            user_id=current_user.id,
            not_found_detail="Importacao nao encontrada",
        )
        return fornecedor_import_tracking_service.build_progress_payload(record=record)

    async def process_full_catalog(
        self,
        background_tasks: BackgroundTasks,
        file_id: int,
        fornecedor_id: int,
        tipo_produto_id: int,
        start_page: int,
        region: Optional[List[float]],
        mapping: Optional[dict],
        db: Session,
        current_user: models.User,
    ):
        return await fornecedor_catalog_process_service.start_full_processing(
            background_tasks=background_tasks,
            db=db,
            current_user=current_user,
            file_id=file_id,
            fornecedor_id=fornecedor_id,
            tipo_produto_id=tipo_produto_id,
            start_page=start_page,
            region=region,
            mapping=mapping,
        )

    def extract_page_data(
        self,
        background_tasks: BackgroundTasks,
        file_id: int,
        page_number: int,
        db: Session,
        current_user: models.User,
    ) -> dict:
        record = fornecedor_import_tracking_service.get_catalog_record_or_404(
            db=db,
            file_id=file_id,
            user_id=current_user.id,
            not_found_detail="Arquivo nao encontrado",
        )
        fornecedor_import_tracking_service.schedule_page_extraction(
            background_tasks=background_tasks,
            import_job_id=record.id,
            page_number=page_number,
            db_url=str(database.engine.url),
        )
        return {"job_id": record.id, "status": "PROCESSING"}

    def delete_fornecedor(
        self,
        fornecedor_id: int,
        db: Session,
        current_user: models.User,
    ) -> models.Fornecedor:
        return fornecedor_management_service.delete_fornecedor(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )

    def review_import_job(
        self,
        job_id: int,
        db: Session,
        current_user: models.User,
    ) -> dict:
        job = fornecedor_import_job_service.get_job_for_user_or_404(
            db=db,
            job_id=job_id,
            user_id=current_user.id,
        )
        return fornecedor_import_job_service.build_review_payload(job=job)

    def commit_import_job(
        self,
        background_tasks: BackgroundTasks,
        job_id: int,
        db: Session,
        current_user: models.User,
    ) -> dict:
        _ = fornecedor_import_job_service.get_job_for_user_or_404(
            db=db,
            job_id=job_id,
            user_id=current_user.id,
        )
        fornecedor_import_job_service.schedule_commit(
            background_tasks=background_tasks,
            db=db,
            job_id=job_id,
            user_id=current_user.id,
        )
        return {"status": "PROCESSING", "job_id": job_id}

    def get_import_job_status(
        self,
        job_id: int,
        db: Session,
        current_user: models.User,
    ) -> dict:
        record = fornecedor_import_tracking_service.get_catalog_record_or_404(
            db=db,
            file_id=job_id,
            user_id=current_user.id,
            not_found_detail="Job nao encontrado",
        )
        return fornecedor_import_tracking_service.build_import_job_status_payload(record=record)


fornecedores_router_workflow = _FornecedoresRouterWorkflow()


@router.post("/", response_model=schemas.FornecedorResponse, status_code=status.HTTP_201_CREATED)
def create_user_fornecedor(
    fornecedor: schemas.FornecedorCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        return fornecedores_router_workflow.create_fornecedor(
            fornecedor=fornecedor,
            db=db,
            current_user=current_user,
        )
    except HTTPException as exc:
        logger.warning("HTTPException ao criar fornecedor: %s", exc.detail)
        raise
    except Exception:
        logger.exception("Erro interno inesperado ao criar fornecedor")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar fornecedor. Tente novamente mais tarde.",
        )


@router.get("/", response_model=schemas.FornecedorPage)
def read_user_fornecedores(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0, description="Numero de itens para pular"),
    limit: int = Query(10, ge=1, le=100, description="Numero maximo de itens por pagina"),
    termo_busca: Optional[str] = Query(None, description="Termo para buscar no nome do fornecedor"),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.list_fornecedores_page(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
        termo_busca=termo_busca,
    )


@router.get("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def read_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.read_fornecedor(
        fornecedor_id=fornecedor_id,
        db=db,
        current_user=current_user,
    )


@router.put("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def update_fornecedor_endpoint(
    fornecedor_id: int,
    fornecedor_update: schemas.FornecedorUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        return fornecedores_router_workflow.update_fornecedor(
            fornecedor_id=fornecedor_id,
            fornecedor_update=fornecedor_update,
            db=db,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao atualizar fornecedor.",
        )


@router.get("/{fornecedor_id}/mapping", response_model=Optional[dict])
def get_mapping(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.get_mapping(
        fornecedor_id=fornecedor_id,
        db=db,
        current_user=current_user,
    )


@router.put("/{fornecedor_id}/mapping", response_model=schemas.FornecedorResponse)
def update_mapping(
    fornecedor_id: int,
    mapping: Optional[dict] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.update_mapping(
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        db=db,
        current_user=current_user,
    )


@router.post("/import/preview-pages")
async def preview_pages(file: UploadFile = File(...)):
    return await fornecedores_router_workflow.preview_pages(file=file)


@router.post("/{fornecedor_id}/preview-pdf", response_model=schemas.PdfPreviewResponse)
async def preview_pdf(
    fornecedor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    offset: int = Query(0, description="Pagina inicial para pre-visualizacao (base 0)."),
    limit: int = Query(20, description="Numero maximo de paginas para pre-visualizacao."),
):
    return await fornecedores_router_workflow.preview_pdf(
        fornecedor_id=fornecedor_id,
        file=file,
        db=db,
        current_user=current_user,
        offset=offset,
        limit=limit,
    )


@router.post("/preview-catalog-region", response_model=schemas.CatalogPreview)
def preview_catalog_from_region(
    preview_request: schemas.CatalogRegionPreviewRequest,
    db: Session = Depends(database.get_db),
):
    return fornecedores_router_workflow.preview_catalog_from_region(
        preview_request=preview_request,
        db=db,
    )


@router.post("/extract_data_from_pdf_bulk", status_code=status.HTTP_202_ACCEPTED)
def extract_data_from_pdf_bulk(
    background_tasks: BackgroundTasks,
    request: schemas.PdfRegionBulkRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    _ = current_user
    return fornecedores_router_workflow.extract_data_from_pdf_bulk(
        background_tasks=background_tasks,
        request=request,
        db=db,
    )


@router.get("/import/progress/{job_id}")
def get_import_progress(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.get_import_progress(
        job_id=job_id,
        db=db,
        current_user=current_user,
    )


@router.post("/import/process-full-catalog", status_code=status.HTTP_202_ACCEPTED)
async def process_full_catalog(
    background_tasks: BackgroundTasks,
    file_id: int = Body(..., embed=True),
    fornecedor_id: int = Body(..., embed=True),
    tipo_produto_id: int = Body(..., embed=True),
    start_page: int = Body(1, embed=True),
    region: Optional[List[float]] = Body(None, embed=True),
    mapping: Optional[dict] = Body(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await fornecedores_router_workflow.process_full_catalog(
        background_tasks=background_tasks,
        file_id=file_id,
        fornecedor_id=fornecedor_id,
        tipo_produto_id=tipo_produto_id,
        start_page=start_page,
        region=region,
        mapping=mapping,
        db=db,
        current_user=current_user,
    )


@router.get("/import/extract-page-data", status_code=status.HTTP_202_ACCEPTED)
def extract_page_data(
    background_tasks: BackgroundTasks,
    file_id: int = Query(..., description="ID do arquivo importado"),
    page_number: int = Query(..., ge=1, description="Numero da pagina a extrair"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.extract_page_data(
        background_tasks=background_tasks,
        file_id=file_id,
        page_number=page_number,
        db=db,
        current_user=current_user,
    )


@router.delete("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def delete_fornecedor_endpoint(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        return fornecedores_router_workflow.delete_fornecedor(
            fornecedor_id=fornecedor_id,
            db=db,
            current_user=current_user,
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao deletar fornecedor.",
        )


@router.get("/import/review/{job_id}", response_model=dict)
def review_import_job(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.review_import_job(
        job_id=job_id,
        db=db,
        current_user=current_user,
    )


@router.post("/import/commit/{job_id}", status_code=status.HTTP_202_ACCEPTED)
def commit_import_job(
    background_tasks: BackgroundTasks,
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.commit_import_job(
        background_tasks=background_tasks,
        job_id=job_id,
        db=db,
        current_user=current_user,
    )


@router.get("/import_job/{job_id}/status")
def get_import_job_status(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedores_router_workflow.get_import_job_status(
        job_id=job_id,
        db=db,
        current_user=current_user,
    )


class FornecedoresRouterLegacyService:
    def create_fornecedor(self, *args, **kwargs):
        return fornecedores_router_workflow.create_fornecedor(*args, **kwargs)

    def list_fornecedores_page(self, *args, **kwargs):
        return fornecedores_router_workflow.list_fornecedores_page(*args, **kwargs)

    def read_fornecedor(self, *args, **kwargs):
        return fornecedores_router_workflow.read_fornecedor(*args, **kwargs)

    def update_fornecedor(self, *args, **kwargs):
        return fornecedores_router_workflow.update_fornecedor(*args, **kwargs)

    def get_mapping(self, *args, **kwargs):
        return fornecedores_router_workflow.get_mapping(*args, **kwargs)

    def update_mapping(self, *args, **kwargs):
        return fornecedores_router_workflow.update_mapping(*args, **kwargs)

    async def preview_pages(self, *args, **kwargs):
        return await fornecedores_router_workflow.preview_pages(*args, **kwargs)

    async def preview_pdf(self, *args, **kwargs):
        return await fornecedores_router_workflow.preview_pdf(*args, **kwargs)

    def preview_catalog_from_region(self, *args, **kwargs):
        return fornecedores_router_workflow.preview_catalog_from_region(*args, **kwargs)

    def extract_data_from_pdf_bulk(self, *args, **kwargs):
        return fornecedores_router_workflow.extract_data_from_pdf_bulk(*args, **kwargs)

    def get_import_progress(self, *args, **kwargs):
        return fornecedores_router_workflow.get_import_progress(*args, **kwargs)

    async def process_full_catalog(self, *args, **kwargs):
        return await fornecedores_router_workflow.process_full_catalog(*args, **kwargs)

    def extract_page_data(self, *args, **kwargs):
        return fornecedores_router_workflow.extract_page_data(*args, **kwargs)

    def delete_fornecedor(self, *args, **kwargs):
        return fornecedores_router_workflow.delete_fornecedor(*args, **kwargs)

    def review_import_job(self, *args, **kwargs):
        return fornecedores_router_workflow.review_import_job(*args, **kwargs)

    def commit_import_job(self, *args, **kwargs):
        return fornecedores_router_workflow.commit_import_job(*args, **kwargs)

    def get_import_job_status(self, *args, **kwargs):
        return fornecedores_router_workflow.get_import_job_status(*args, **kwargs)


fornecedores_router_legacy_service = FornecedoresRouterLegacyService()
