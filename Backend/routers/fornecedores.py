# Caminho: Backend/routers/fornecedores.py

from typing import List, Optional
from sqlalchemy import func
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
    UploadFile,
    File,
    BackgroundTasks,
    Body,
)
from sqlalchemy.orm import Session
from pathlib import Path
import logging
import uuid
import os


from Backend import crud_fornecedores
from Backend import crud_produtos
from Backend import crud_fornecedor_import_jobs
from Backend import models
from Backend import schemas
from Backend import crud_historico
from Backend import database
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
from Backend.application.services.service_container import service_container
from Backend.tasks import process_pdf_extraction_task
from . import auth_utils  # Para obter o usuário
from Backend.routers.produtos import catalog_import_start_service

logger = logging.getLogger(__name__)
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

router = APIRouter(
    prefix="/fornecedores",
    tags=["fornecedores"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)


# Endpoint para criar fornecedor
@router.post(
    "/", response_model=schemas.FornecedorResponse, status_code=status.HTTP_201_CREATED
)
def create_user_fornecedor(
    fornecedor: schemas.FornecedorCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    logger.info(f"Requisição para criar fornecedor recebida.")
    logger.info(
        f"current_user (email): {current_user.email if current_user else 'N/A'}"
    )
    logger.info(f"current_user.id: {current_user.id if current_user else 'N/A'}")

    if current_user is None or current_user.id is None:
        logger.error(
            "ERRO: Usuário autenticado ou seu ID é nulo ao tentar criar fornecedor. Isso pode indicar um problema de autenticação ou de sessão."
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não foi possível identificar o usuário logado para criar o fornecedor. Por favor, tente fazer login novamente.",
        )

    try:
        db_forn = crud_fornecedores.create_fornecedor(
            db=db, fornecedor=fornecedor, user_id=current_user.id
        )
        crud_historico.create_registro_historico(
            db,
            schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=db_forn.id,
            ),
        )
        return db_forn
    except HTTPException as e:  # Repassa HTTPExceptions do CRUD (ex: nome duplicado)
        logger.warning(f"HTTPException ao criar fornecedor: {e.detail}")
        raise e
    except Exception as e:  # Captura outros erros inesperados
        logger.exception(
            "Erro interno inesperado ao criar fornecedor:"
        )  # Usa exception para incluir o traceback completo
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao criar fornecedor. Por favor, tente novamente mais tarde.",
        )


# Endpoint para listar fornecedores do usuário logado (ou todos para admin)
@router.get("/", response_model=schemas.FornecedorPage)
def read_user_fornecedores(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0, description="Número de itens para pular"),
    limit: int = Query(
        10, ge=1, le=100, description="Número máximo de itens por página"
    ),
    termo_busca: Optional[str] = Query(
        None, description="Termo para buscar no nome do fornecedor"
    ),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    if current_user.is_superuser:
        fornecedores = db.query(models.Fornecedor)
        if termo_busca:
            fornecedores = fornecedores.filter(
                models.Fornecedor.nome.ilike(f"%{termo_busca}%")
            )
        total_items = fornecedores.count()
        items_paginados = (
            fornecedores.order_by(models.Fornecedor.nome)
            .offset(skip)
            .limit(limit)
            .all()
        )
    else:
        items_paginados = crud_fornecedores.get_fornecedores_by_user(
            db, user_id=current_user.id, skip=skip, limit=limit, search=termo_busca
        )
        total_items = crud_fornecedores.count_fornecedores_by_user(
            db=db, user_id=current_user.id, search=termo_busca
        )

    page_number = skip // limit + 1
    return {
        "items": items_paginados,
        "total_items": total_items,
        "page": page_number,
        "limit": limit,
    }


# Endpoint para obter um fornecedor específico
@router.get("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def read_fornecedor(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedor_management_service.resolve_fornecedor_for_user(
        db=db,
        fornecedor_id=fornecedor_id,
        current_user=current_user,
        not_found_detail="Fornecedor nao encontrado ou nao pertence ao usuario",
        forbidden_detail="Nao autorizado a acessar este fornecedor.",
    )

# Endpoint para atualizar um fornecedor
@router.put("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def update_fornecedor_endpoint(
    fornecedor_id: int,
    fornecedor_update: schemas.FornecedorUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        return fornecedor_management_service.update_fornecedor(
            db=db,
            fornecedor_id=fornecedor_id,
            fornecedor_update=fornecedor_update,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e
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
    return fornecedor_management_service.get_mapping(
        db=db,
        fornecedor_id=fornecedor_id,
        current_user=current_user,
    )


@router.put("/{fornecedor_id}/mapping", response_model=schemas.FornecedorResponse)
def update_mapping(
    fornecedor_id: int,
    mapping: Optional[dict] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return fornecedor_management_service.update_mapping(
        db=db,
        fornecedor_id=fornecedor_id,
        current_user=current_user,
        mapping=mapping,
    )


@router.post("/import/preview-pages")
async def preview_pages(file: UploadFile = File(...)):
    """Gera imagens de todas as páginas de um PDF enviado."""

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos PDF são permitidos.")

    file_id = uuid.uuid4().hex
    tmp_dir = Path(os.getenv("TMPDIR", "/tmp"))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = tmp_dir / f"{file_id}.pdf"

    contents = await file.read()
    with open(pdf_path, "wb") as out_file:
        out_file.write(contents)

    page_image_urls = file_processing_service.generate_pdf_page_images(
        str(pdf_path), file_id
    )

    return {"file_id": file_id, "page_image_urls": page_image_urls}


@router.post("/{fornecedor_id}/preview-pdf", response_model=schemas.PdfPreviewResponse)
async def preview_pdf(
    fornecedor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),  # <- CORRIGIDO AQUI
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    offset: int = Query(
        0, description="Página inicial para começar a pré-visualização (base 0)."
    ),
    limit: int = Query(20, description="Número máximo de páginas para pré-visualizar."),
):
    db_fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if not db_fornecedor or db_fornecedor.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Tipo de ficheiro inválido. Apenas PDFs são permitidos.",
        )

    result = file_processing_service.pdf_pages_to_images(
        db=db,
        file=file,
        fornecedor_id=fornecedor_id,
        user_id=current_user.id,
        offset=offset,
        limit=limit,
    )
    return result


# Novo endpoint para pré-visualizar uma região específica de um catálogo PDF
@router.post("/preview-catalog-region", response_model=schemas.CatalogPreview)
def preview_catalog_from_region(
    preview_request: schemas.CatalogRegionPreviewRequest,
    db: Session = Depends(database.get_db),
):
    """Gera uma pré-visualização dos dados de uma região específica de um PDF."""
    file_path = file_processing_service.get_file_path_by_id(
        db, file_id=preview_request.file_id
    )
    if not file_path:
        raise HTTPException(
            status_code=404, detail="Arquivo de catálogo não encontrado"
        )

    image_bytes = file_processing_service.extract_pdf_region_image(
        file_path=file_path,
        page_number=preview_request.page_number,
        region=preview_request.region,
    )
    annotation = web_data_extractor_service.extract_text_from_image_region(image_bytes)
    df = file_processing_service.parse_annotation_to_dataframe(annotation)

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível extrair dados da região selecionada. Tente selecionar uma área diferente ou ajustar as configurações.",
        )

    columns = df.columns.astype(str).tolist()
    sample_data = df.head(10).to_dict(orient="records")

    return schemas.CatalogPreview(columns=columns, data=sample_data)


@router.post("/extract_data_from_pdf_bulk", status_code=status.HTTP_202_ACCEPTED)
def extract_data_from_pdf_bulk(
    background_tasks: BackgroundTasks,
    request: schemas.PdfRegionBulkRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Inicia a extração de uma região do PDF em várias páginas."""
    file_path = file_processing_service.get_file_path_by_id(db, file_id=request.file_id)
    if not file_path:
        raise HTTPException(status_code=404, detail="Arquivo de catálogo não encontrado")

    import pdfplumber
    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)

    pages = request.pages
    if request.all_pages or not pages:
        pages = list(range(1, total_pages + 1))

    for pg in pages:
        if 1 <= pg <= total_pages:
            background_tasks.add_task(
                file_processing_service.extract_data_from_pdf_region,
                file_path=file_path,
                page_number=pg,
                region=request.region,
            )

    return {"detail": "Batch processing started", "total_pages": total_pages}


# Endpoint para consultar progresso de importação de catálogo
@router.get("/import/progress/{job_id}")
def get_import_progress(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Retorna o status e o progresso da importacao de catalogo."""
    record = fornecedor_import_tracking_service.get_catalog_record_or_404(
        db=db,
        file_id=job_id,
        user_id=current_user.id,
        not_found_detail="Importacao nao encontrada",
    )
    return fornecedor_import_tracking_service.build_progress_payload(record=record)

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
    """Processa todas as paginas de um catalogo em background."""
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

@router.get("/import/extract-page-data", status_code=status.HTTP_202_ACCEPTED)
def extract_page_data(
    background_tasks: BackgroundTasks,
    file_id: int = Query(..., description="ID do arquivo importado"),
    page_number: int = Query(..., ge=1, description="Numero da pagina a extrair"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Agenda a extracao de dados de uma pagina de um catalogo PDF."""
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

# Endpoint para deletar um fornecedor
@router.delete("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def delete_fornecedor_endpoint(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    try:
        return fornecedor_management_service.delete_fornecedor(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
        )
    except HTTPException as e:
        raise e
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
    job = fornecedor_import_job_service.get_job_for_user_or_404(
        db=db,
        job_id=job_id,
        user_id=current_user.id,
    )
    return fornecedor_import_job_service.build_review_payload(job=job)


@router.post("/import/commit/{job_id}", status_code=status.HTTP_202_ACCEPTED)
def commit_import_job(
    background_tasks: BackgroundTasks,
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
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


@router.get("/import_job/{job_id}/status")
def get_import_job_status(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Retorna o status de processamento de um job de importacao."""
    record = fornecedor_import_tracking_service.get_catalog_record_or_404(
        db=db,
        file_id=job_id,
        user_id=current_user.id,
        not_found_detail="Job nao encontrado",
    )
    return fornecedor_import_tracking_service.build_import_job_status_payload(
        record=record
    )

