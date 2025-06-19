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
)
from sqlalchemy.orm import Session
import logging


from Backend import crud_fornecedores
from Backend import crud_produtos
from Backend import crud_fornecedor_import_jobs
from Backend import models
from Backend import schemas
from Backend import crud_historico
from Backend import database
from Backend.services import file_processing_service
from . import auth_utils  # Para obter o usuário

logger = logging.getLogger(__name__)

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
    db_fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)

    if db_fornecedor is None:
        raise HTTPException(
            status_code=404,
            detail="Fornecedor não encontrado ou não pertence ao usuário",
        )

    if not current_user.is_superuser and db_fornecedor.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a acessar este fornecedor."
        )
    return db_fornecedor


# Endpoint para atualizar um fornecedor
@router.put("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def update_fornecedor_endpoint(
    fornecedor_id: int,
    fornecedor_update: schemas.FornecedorUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)

    if db_fornecedor is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    if not current_user.is_superuser and db_fornecedor.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a modificar este fornecedor."
        )

    if fornecedor_update.nome and fornecedor_update.nome != db_fornecedor.nome:
        existing_fornecedor_check = (
            db.query(models.Fornecedor)
            .filter(
                models.Fornecedor.user_id == current_user.id,
                func.lower(models.Fornecedor.nome)
                == func.lower(fornecedor_update.nome),
                models.Fornecedor.id != fornecedor_id,
            )
            .first()
        )
        if existing_fornecedor_check:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Já existe um fornecedor com o nome '{fornecedor_update.nome}'.",
            )

    try:
        updated = crud_fornecedores.update_fornecedor(
            db=db, db_fornecedor=db_fornecedor, fornecedor_update=fornecedor_update
        )
        crud_historico.create_registro_historico(
            db,
            schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=models.TipoAcaoSistemaEnum.ATUALIZACAO,
                entity_id=updated.id,
            ),
        )
        return updated
    except HTTPException as e:
        raise e
    except Exception as e:
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
    fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    if not current_user.is_superuser and fornecedor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")
    return fornecedor.default_column_mapping


@router.put("/{fornecedor_id}/mapping", response_model=schemas.FornecedorResponse)
def update_mapping(
    fornecedor_id: int,
    mapping: Optional[dict] = None,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)
    if not fornecedor:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado")
    if not current_user.is_superuser and fornecedor.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado")
    fornecedor.default_column_mapping = mapping
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor


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

    df = file_processing_service.extract_data_from_pdf_region(
        file_path=file_path,
        page_number=preview_request.page_number,
        region=preview_request.region,
    )

    if df.empty:
        raise HTTPException(
            status_code=400,
            detail="Não foi possível extrair dados da região selecionada. Tente selecionar uma área diferente ou ajustar as configurações.",
        )

    columns = df.columns.astype(str).tolist()
    sample_data = df.head(10).to_dict(orient="records")

    return schemas.CatalogPreview(columns=columns, data=sample_data)


# Endpoint para deletar um fornecedor
@router.delete("/{fornecedor_id}", response_model=schemas.FornecedorResponse)
def delete_fornecedor_endpoint(
    fornecedor_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)

    if db_fornecedor is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")

    if not current_user.is_superuser and db_fornecedor.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a deletar este fornecedor."
        )

    try:
        deleted = crud_fornecedores.delete_fornecedor(
            db=db, db_fornecedor=db_fornecedor
        )
        crud_historico.create_registro_historico(
            db,
            schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted.id,
            ),
        )
        return deleted
    except HTTPException as e:  # Se o CRUD levantar HTTP 409 por produtos associados
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno ao deletar fornecedor.",
        )


async def _commit_import_job_task(db_session_factory, job_id: int, user_id: int):
    db = db_session_factory()
    try:
        job = crud_fornecedor_import_jobs.get_import_job(db, job_id)
        if not job:
            return
        summary = job.result_summary or []
        for prod_data in summary:
            try:
                produto_schema = schemas.ProdutoCreate(**prod_data)
            except Exception:
                continue
            crud_produtos.get_or_create_produto(db, produto_schema, user_id)
        crud_fornecedor_import_jobs.update_job_status(db, job, "COMPLETED")
    finally:
        db.close()


@router.get("/import/review/{job_id}", response_model=dict)
def review_import_job(
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    job = crud_fornecedor_import_jobs.get_import_job(db, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job não encontrado")
    return job.result_summary or {}


@router.post("/import/commit/{job_id}", status_code=status.HTTP_202_ACCEPTED)
def commit_import_job(
    background_tasks: BackgroundTasks,
    job_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    job = crud_fornecedor_import_jobs.get_import_job(db, job_id)
    if not job or job.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Job não encontrado")

    from sqlalchemy.orm import sessionmaker

    db_session_factory = sessionmaker(bind=db.get_bind())
    background_tasks.add_task(
        _commit_import_job_task,
        db_session_factory=db_session_factory,
        job_id=job_id,
        user_id=current_user.id,
    )
    return {"status": "PROCESSING", "job_id": job_id}
