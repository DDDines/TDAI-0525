# Backend/routers/produtos.py

from typing import List, Optional, Union, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    BackgroundTasks,
    status,
    UploadFile,
    File,
    Form,
    Body,
)
import json
import io
import pdfplumber
from sqlalchemy.orm import Session
from pathlib import Path
from sqlalchemy import func, or_

from Backend import crud_produtos
from Backend import crud_fornecedores
from Backend import crud_product_types
from Backend import crud
from Backend import crud_historico
from Backend import models
from Backend import schemas  # schemas é importado
from Backend import database
from Backend.database import SessionLocal
import logging
from Backend.services import file_processing_service
from . import auth_utils  # Para obter o usuário logado
from Backend.core import (
    config,
)  # Pode ser necessário para settings, se usado diretamente
from Backend.core.config import settings

router = APIRouter(
    prefix="/produtos",
    tags=["produtos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = logging.getLogger(__name__)


async def _tarefa_processar_catalogo(
    db_session_factory,
    file_id: int,
    user_id: int,
    product_type_id: int,
    fornecedor_id: int,
    mapping: Optional[Dict[str, str]] = None,
    pages: Optional[List[int]] = None,
):
    """Processa o arquivo salvo em background e cria os produtos."""
    db: Optional[Session] = None
    try:
        db = db_session_factory()
        catalog_file = db.query(models.CatalogImportFile).filter_by(id=file_id, user_id=user_id).first()
        if not catalog_file:
            logger.error("Catalog file %s not found", file_id)
            return
        catalog_file.status = "PROCESSING"
        catalog_file.fornecedor_id = fornecedor_id
        db.commit()

        file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        if not file_path.is_absolute():
            file_path = Path(__file__).resolve().parent.parent / file_path
        if not file_path.exists():
            catalog_file.status = "FAILED"
            db.commit()
            return
        content = file_path.read_bytes()
        ext = file_path.suffix.lower()
        if ext in [".xlsx", ".xls"]:
            produtos_data = await file_processing_service.processar_arquivo_excel(
                content,
                mapeamento_colunas_usuario=mapping,
                product_type_id=product_type_id,
            )
        elif ext == ".csv":
            produtos_data = await file_processing_service.processar_arquivo_csv(
                content,
                mapeamento_colunas_usuario=mapping,
                product_type_id=product_type_id,
            )
        elif ext == ".pdf":
            produtos_data = await file_processing_service.processar_arquivo_pdf(
                content,
                mapeamento_colunas_usuario=mapping,
                product_type_id=product_type_id,
                pages=pages,
            )
        else:
            catalog_file.status = "FAILED"
            db.commit()
            return

        produtos_create: List[schemas.ProdutoCreate] = []
        erros: List[Dict[str, Any]] = []
        for prod in produtos_data:
            if isinstance(prod, dict) and (
                prod.get("motivo_descarte")
                or any(key.startswith("erro_processamento") for key in prod.keys())
            ):
                erros.append(prod)
                continue
            try:
                produto_schema = schemas.ProdutoCreate(
                    nome_base=prod.get("nome_base")
                    or prod.get("sku_original")
                    or "Produto Importado",
                    sku=prod.get("sku_original"),
                    ean=prod.get("ean_original"),
                    descricao_original=prod.get("descricao_original"),
                    marca=prod.get("marca"),
                    categoria_original=prod.get("categoria_original"),
                    fornecedor_id=catalog_file.fornecedor_id,
                    product_type_id=product_type_id,
                )
                produtos_create.append(produto_schema)
            except Exception as e:
                erros.append({"motivo_descarte": f"Erro ao converter linha: {str(e)}", "linha_original": prod})

        if produtos_create:
            created, dup_errors = crud_produtos.create_produtos_bulk(db, produtos_create, user_id=user_id)
            erros.extend(dup_errors)
            for db_produto in created:
                crud.create_registro_uso_ia(
                    db,
                    schemas.RegistroUsoIACreate(
                        user_id=user_id,
                        produto_id=db_produto.id,
                        tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO,
                        creditos_consumidos=0,
                    ),
                )
                crud_historico.create_registro_historico(
                    db,
                    schemas.RegistroHistoricoCreate(
                        user_id=user_id,
                        entidade="Produto",
                        acao=models.TipoAcaoSistemaEnum.CRIACAO,
                        entity_id=db_produto.id,
                    ),
                )

        result_summary = {
            "created": [
                schemas.ProdutoResponse.model_validate(p).model_dump()
                for p in created
            ],
            "updated": [],
            "errors": erros,
        }

        catalog_file.status = "IMPORTED"
        catalog_file.result_summary = result_summary
        db.add(catalog_file)
        db.commit()
    except Exception:
        logger.exception("Erro ao processar importacao de catalogo")
        if db:
            catalog_file = db.query(models.CatalogImportFile).filter_by(id=file_id).first()
            if catalog_file:
                catalog_file.status = "FAILED"
                db.commit()
    finally:
        if db:
            db.close()


@router.post(
    "/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED
)  # CORRIGIDO AQUI
def create_produto(  # Nome da função mantido como no arquivo do usuário
    produto: schemas.ProdutoCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """
    Cria um novo produto para o usuário logado.
    """
    # Validação do fornecedor, se fornecido
    if produto.fornecedor_id:
        fornecedor = crud_fornecedores.get_fornecedor(
            db, fornecedor_id=produto.fornecedor_id
        )  # Assume que user_id não é necessário aqui ou é validado no get_fornecedor se não for admin
        if (
            not fornecedor
        ):  # Adicionar ( or (not current_user.is_superuser and fornecedor.user_id != current_user.id) ) se necessário
            raise HTTPException(
                status_code=404,
                detail=f"Fornecedor com ID {produto.fornecedor_id} não encontrado.",
            )

    # Validação do tipo de produto, se fornecido
    if produto.product_type_id:
        product_type = crud_product_types.get_product_type(
            db, product_type_id=produto.product_type_id
        )
        if (
            not product_type
        ):  # Adicionar validação de owner se tipos de produto forem específicos do usuário
            raise HTTPException(
                status_code=404,
                detail=f"Tipo de Produto com ID {produto.product_type_id} não encontrado.",
            )

    # A função crud_produtos.create_produto (ou create_user_produto) lida com a lógica de criação
    # usando nome_base e nome_chat_api como definido nos schemas.
    db_produto = crud_produtos.create_produto(
        db=db, produto=produto, user_id=current_user.id
    )
    crud.create_registro_uso_ia(
        db,
        schemas.RegistroUsoIACreate(
            user_id=current_user.id,
            produto_id=db_produto.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO,
            creditos_consumidos=0,
        ),
    )
    crud_historico.create_registro_historico(
        db,
        schemas.RegistroHistoricoCreate(
            user_id=current_user.id,
            entidade="Produto",
            acao=models.TipoAcaoSistemaEnum.CRIACAO,
            entity_id=db_produto.id,
        ),
    )
    return db_produto


@router.get("/catalog-import-files/", response_model=schemas.CatalogImportFilePage)
def list_catalog_import_files(
    db: Session = Depends(database.get_db),
    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor"),
    skip: int = Query(0, ge=0, description="Número de itens para pular"),
    limit: int = Query(10, ge=1, le=100, description="Número máximo de itens por página"),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    query = db.query(models.CatalogImportFile).filter(models.CatalogImportFile.user_id == current_user.id)
    if fornecedor_id is not None:
        query = query.filter(models.CatalogImportFile.fornecedor_id == fornecedor_id)
    total_items = query.count()
    items = (
        query.order_by(models.CatalogImportFile.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    page = skip // limit + 1
    return {"items": items, "total_items": total_items, "page": page, "limit": limit}


@router.delete(
    "/catalog-import-files/{file_id}/",
    response_model=schemas.CatalogImportFileResponse,
)
def delete_catalog_import_file(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    record = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    file_processing_service.delete_catalog_file(record.stored_filename)
    db.delete(record)
    db.commit()
    return record


@router.post(
    "/catalog-import-files/{file_id}/reprocess/",
    status_code=status.HTTP_202_ACCEPTED,
)
async def reprocess_catalog_import_file(
    background_tasks: BackgroundTasks,
    file_id: int,
    product_type_id: int = Body(..., embed=True),
    fornecedor_id: int = Body(..., embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    catalog_file = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not catalog_file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    catalog_file.status = "PROCESSING"
    catalog_file.fornecedor_id = fornecedor_id
    db.commit()

    if mapping is None:
        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id)
        if fornecedor and fornecedor.default_column_mapping:
            mapping = fornecedor.default_column_mapping

    from sqlalchemy.orm import sessionmaker

    db_session_factory = sessionmaker(bind=db.get_bind())

    background_tasks.add_task(
        _tarefa_processar_catalogo,
        db_session_factory=db_session_factory,
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
    )

    return {"status": "PROCESSING", "file_id": file_id}




@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI
def read_produto(  # Nome da função mantido como no arquivo do usuário
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """
    Obtém os detalhes de um produto específico.
    """
    db_produto = crud_produtos.get_produto(
        db, produto_id=produto_id
    )  # crud_produtos.get_produto não filtra por user_id por padrão

    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    # Verifica a permissão para visualizar
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a visualizar este produto"
        )
    return db_produto


# Também expõe a rota com barra ao final para evitar redirecionamentos que podem
# levar à perda do cabeçalho Authorization em alguns clientes HTTP.
router.add_api_route(
    "/{produto_id}/",
    read_produto,
    methods=["GET"],
    response_model=schemas.ProdutoResponse,
    include_in_schema=False,
)


@router.get("/", response_model=schemas.ProdutoPage)  # Este já estava correto
def read_produtos(  # Nome da função mantido como no arquivo do usuário
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0, description="Número de itens para pular"),
    limit: int = Query(
        10, ge=1, le=200, description="Número máximo de itens por página"
    ),
    sort_by: Optional[str] = Query(
        None, description="Campo para ordenação (ex: nome_base, preco_venda)"
    ),  # Ajustado para nome_base
    sort_order: Optional[str] = Query(
        "asc", description="Ordem da ordenação (asc ou desc)"
    ),
    search: Optional[str] = Query(
        None, description="Termo de busca para nome, descrição, SKU, EAN"
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
        None, description="Filtrar por status de geração de título por IA"
    ),
    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = Query(
        None, description="Filtrar por status de geração de descrição por IA"
    ),
    product_type_id: Optional[int] = Query(
        None, description="ID do Tipo de Produto para filtrar produtos"
    ),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    user_id_filter = None if current_user.is_superuser else current_user.id

    # Usando get_produtos_by_user do crud, que foi ajustado para receber user_id opcional ou is_admin
    produtos_db = crud_produtos.get_produtos_by_user(  # Nome da função no CRUD
        db,
        user_id=user_id_filter,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        fornecedor_id=fornecedor_id,
        categoria=categoria,  # Passando categoria para o CRUD
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
        product_type_id=product_type_id,
        is_admin=current_user.is_superuser,  # Passando is_admin para o CRUD
    )
    total_items = crud_produtos.count_produtos_by_user(  # Nome da função no CRUD
        db,
        user_id=user_id_filter,
        search=search,
        fornecedor_id=fornecedor_id,
        categoria=categoria,  # Passando categoria para o CRUD
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
        product_type_id=product_type_id,
        is_admin=current_user.is_superuser,  # Passando is_admin para o CRUD
    )
    page = skip // limit + 1
    return {
        "items": produtos_db,
        "total_items": total_items,
        "page": page,
        "limit": limit,
    }


@router.put("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI
def update_produto(  # Nome da função mantido como no arquivo do usuário
    produto_id: int,
    produto: schemas.ProdutoUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a modificar este produto"
        )

    if (
        produto.fornecedor_id is not None
        and produto.fornecedor_id != db_produto.fornecedor_id
    ):
        fornecedor = crud_fornecedores.get_fornecedor(
            db, fornecedor_id=produto.fornecedor_id
        )
        if (
            not fornecedor
        ):  # Adicionar ( or (not current_user.is_superuser and fornecedor.user_id != current_user.id) ) se necessário
            raise HTTPException(
                status_code=404,
                detail=f"Fornecedor com ID {produto.fornecedor_id} não encontrado.",
            )

    if (
        produto.product_type_id is not None
        and produto.product_type_id != db_produto.product_type_id
    ):
        product_type = crud_product_types.get_product_type(
            db, product_type_id=produto.product_type_id
        )
        if not product_type:
            raise HTTPException(
                status_code=404,
                detail=f"Tipo de Produto com ID {produto.product_type_id} não encontrado.",
            )

    # A função crud_produtos.update_produto espera o objeto db_produto
    updated = crud_produtos.update_produto(
        db=db, db_produto=db_produto, produto_update=produto
    )
    crud_historico.create_registro_historico(
        db,
        schemas.RegistroHistoricoCreate(
            user_id=current_user.id,
            entidade="Produto",
            acao=models.TipoAcaoSistemaEnum.ATUALIZACAO,
            entity_id=updated.id,
        ),
    )
    return updated


@router.delete(
    "/{produto_id}", response_model=schemas.ProdutoResponse
)  # CORRIGIDO AQUI
def delete_produto(  # Nome da função mantido como no arquivo do usuário
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a deletar este produto"
        )

    # A função crud_produtos.delete_produto espera o objeto db_produto
    deleted = crud_produtos.delete_produto(db=db, db_produto=db_produto)
    crud_historico.create_registro_historico(
        db,
        schemas.RegistroHistoricoCreate(
            user_id=current_user.id,
            entidade="Produto",
            acao=models.TipoAcaoSistemaEnum.DELECAO,
            entity_id=deleted.id,
        ),
    )
    return deleted


# Expondo rotas com barra final para operações de atualização e deleção.
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
)  # Este já estava correto
def batch_delete_produtos(
    produto_ids: List[int] = Body(
        ...
    ),  # Accept list of IDs directly from the request body
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    deleted_produtos = []
    not_found_ids = []
    not_authorized_ids = []

    for produto_id_val in produto_ids:  # Ajustado nome da variável
        db_produto = crud_produtos.get_produto(db, produto_id=produto_id_val)
        if db_produto is None:
            not_found_ids.append(produto_id_val)
            continue

        if not current_user.is_superuser and db_produto.user_id != current_user.id:
            not_authorized_ids.append(produto_id_val)
            continue

        crud_produtos.delete_produto(db=db, db_produto=db_produto)  # Passa o objeto
        crud_historico.create_registro_historico(
            db,
            schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Produto",
                acao=models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=db_produto.id,
            ),
        )
        deleted_produtos.append(
            db_produto
        )  # Adiciona o objeto que foi deletado (já é um objeto do modelo)

    # Construindo a resposta
    # A conversão para schemas.ProdutoResponse é feita automaticamente pelo FastAPI
    # devido ao response_model=List[schemas.ProdutoResponse]

    if not_found_ids or not_authorized_ids:
        error_detail_parts = []
        if not_found_ids:
            error_detail_parts.append(f"Produtos não encontrados: IDs {not_found_ids}.")
        if not_authorized_ids:
            error_detail_parts.append(
                f"Não autorizado a deletar produtos: IDs {not_authorized_ids}."
            )

        # Se nenhum produto foi deletado com sucesso E houve erros, levanta uma exceção.
        # Se alguns foram deletados, retorna os deletados e o cliente pode precisar ser informado das falhas.
        if not deleted_produtos:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=" ".join(error_detail_parts),
            )
        # Se alguns foram deletados, a resposta incluirá apenas eles.
        # O frontend pode precisar verificar a diferença entre a lista enviada e a recebida.

    if not deleted_produtos and not (
        not_found_ids or not_authorized_ids
    ):  # Se a lista de entrada estava vazia
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum ID de produto fornecido ou lista de IDs vazia.",
        )

    return deleted_produtos


@router.post(
    "/upload-image/{produto_id}", response_model=schemas.ProdutoResponse
)  # CORRIGIDO AQUI
async def upload_produto_image(  # Nome da função mantido como no arquivo do usuário
    produto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(
            status_code=403, detail="Não autorizado a modificar este produto"
        )

    try:
        file_path_in_db = await crud_produtos.save_produto_image(db, produto_id, file)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except IOError as e:  # Captura erro de IO de save_produto_image
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Não foi possível salvar a imagem: {str(e)}"
        )

    # Atualiza o campo imagem_principal_url no produto
    # O schema ProdutoUpdate pode não ter imagem_principal_url se não for editável diretamente
    # mas o modelo tem. O CRUD pode ter uma lógica para isso.
    # Assumindo que crud_produtos.update_produto pode receber um dict com o campo a ser atualizado

    produto_update_schema = schemas.ProdutoUpdate(imagem_principal_url=file_path_in_db)
    updated_produto = crud_produtos.update_produto(
        db=db, db_produto=db_produto, produto_update=produto_update_schema
    )

    return updated_produto


@router.post(
    "/importar-catalogo-preview/", response_model=schemas.ImportPreviewResponse
)
async def importar_catalogo_preview(
    file: UploadFile = File(...),
    fornecedor_id: Optional[int] = Form(None),
    start_page: int = Form(1),
    page_count: int = Form(0),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Gera preview de um catálogo enviado e salva o arquivo para posterior processamento."""

    # Lê o conteúdo para gerar o preview
    content = await file.read()
    await file.seek(0)

    # Salva o arquivo e registra no banco
    catalog_record = await file_processing_service.save_uploaded_catalog(
        file, fornecedor_id
    )
    catalog_record.user_id = current_user.id
    db.add(catalog_record)
    db.commit()
    db.refresh(catalog_record)

    ext = Path(catalog_record.original_filename).suffix.lower()
    try:
        if ext == ".pdf":
            preview = await file_processing_service.preview_arquivo_pdf(
                content, ext, start_page, page_count
            )
        else:
            preview = await file_processing_service.gerar_preview(content, ext)
        return schemas.ImportPreviewResponse(
            **preview, error=None, file_id=catalog_record.id
        )
        return schemas.ImportPreviewResponse(**preview)
    except Exception as e:
        return schemas.ImportPreviewResponse(
            num_pages=0,
            table_pages=[],
            sample_rows={},
            preview_images=[],
            error=f"Falha ao gerar preview de PDF: {e}",
            file_id=catalog_record.id,
        )


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
    """Importa um arquivo de catálogo e cria produtos vinculados ao fornecedor."""
    content = await file.read()
    ext = Path(file.filename).suffix.lower()
    mapping_dict = None
    if mapeamento_colunas_usuario:
        try:
            mapping_dict = json.loads(mapeamento_colunas_usuario)
        except Exception:
            raise HTTPException(
                status_code=400, detail="mapeamento_colunas_usuario inválido"
            )
    else:
        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id)
        if fornecedor and fornecedor.default_column_mapping:
            mapping_dict = fornecedor.default_column_mapping
    if ext in [".xlsx", ".xls"]:
        produtos_data = await file_processing_service.processar_arquivo_excel(
            content, mapping_dict
        )
    elif ext == ".csv":
        produtos_data = await file_processing_service.processar_arquivo_csv(
            content, mapping_dict
        )
    elif ext == ".pdf":
        produtos_data = await file_processing_service.processar_arquivo_pdf(
            content, mapping_dict
        )
    else:
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

    produtos_create = []
    erros: List[Dict[str, Any]] = []
    for prod in produtos_data:
        if isinstance(prod, dict) and (
            prod.get("motivo_descarte")
            or any(key.startswith("erro_processamento") for key in prod.keys())
        ):
            erros.append(prod)
            continue
        try:
            produto_schema = schemas.ProdutoCreate(
                nome_base=prod.get("nome_base")
                or prod.get("sku_original")
                or "Produto Importado",
                sku=prod.get("sku_original"),
                ean=prod.get("ean_original"),
                descricao_original=prod.get("descricao_original"),
                marca=prod.get("marca"),
                categoria_original=prod.get("categoria_original"),
                fornecedor_id=fornecedor_id,
            )
            produtos_create.append(produto_schema)
        except Exception as e:
            erros.append(
                {
                    "motivo_descarte": f"Erro ao converter linha: {str(e)}",
                    "linha_original": prod,
                }
            )

    created: List[models.Produto] = []
    if produtos_create:
        created, dup_errors = crud_produtos.create_produtos_bulk(
            db, produtos_create, user_id=current_user.id
        )
        erros.extend(dup_errors)
        for db_produto in created:
            crud.create_registro_uso_ia(
                db,
                schemas.RegistroUsoIACreate(
                    user_id=current_user.id,
                    produto_id=db_produto.id,
                    tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO,
                    creditos_consumidos=0,
                ),
            )
            crud_historico.create_registro_historico(
                db,
                schemas.RegistroHistoricoCreate(
                    user_id=current_user.id,
                    entidade="Produto",
                    acao=models.TipoAcaoSistemaEnum.CRIACAO,
                    entity_id=db_produto.id,
                ),
            )
    return {"produtos_criados": created, "erros": erros}


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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Agenda o processamento do arquivo salvo e retorna imediatamente."""
    catalog_file = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not catalog_file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    catalog_file.status = "PROCESSING"
    catalog_file.fornecedor_id = fornecedor_id
    db.commit()

    from sqlalchemy.orm import sessionmaker

    db_session_factory = sessionmaker(bind=db.get_bind())
    # Sempre reprocessa o arquivo completo para evitar importar apenas as linhas de preview
    file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent.parent / file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    content = file_path.read_bytes()
    ext = file_path.suffix.lower()
    if mapping is None:
        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id)
        if fornecedor and fornecedor.default_column_mapping:
            mapping = fornecedor.default_column_mapping
    if ext in [".xlsx", ".xls"]:
        produtos_data = await file_processing_service.processar_arquivo_excel(
            content,
            mapeamento_colunas_usuario=mapping,
            product_type_id=product_type_id,
        )
    elif ext == ".csv":
        produtos_data = await file_processing_service.processar_arquivo_csv(
            content,
            mapeamento_colunas_usuario=mapping,
            product_type_id=product_type_id,
        )
    elif ext == ".pdf":
        produtos_data = await file_processing_service.processar_arquivo_pdf(
            content,
            mapeamento_colunas_usuario=mapping,
            product_type_id=product_type_id,
            pages=pages,
        )
    else:
        raise HTTPException(
            status_code=400, detail="Formato de arquivo não suportado"
        )

    background_tasks.add_task(
        _tarefa_processar_catalogo,
        db_session_factory=db_session_factory,
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
    )

    return {"status": "PROCESSING", "file_id": file_id}


@router.get(
    "/importar-catalogo-status/{file_id}/",
    response_model=schemas.CatalogImportFileResponse,
)
def importar_catalogo_status(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Retorna o status atual do processamento do catálogo."""
    record = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    return record


@router.get(
    "/importar-catalogo-result/{file_id}/",
    response_model=schemas.CatalogImportResult,
)
def importar_catalogo_result(
    file_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    record = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")
    if record.status != "IMPORTED" or not record.result_summary:
        raise HTTPException(status_code=400, detail="Resultados ainda nao disponiveis")
    return record.result_summary




@router.post(
    "/selecionar-regiao/",
    response_model=schemas.RegionExtractionResponse,
)
async def selecionar_regiao(
    file_id: int = Body(..., embed=True),
    page: int = Body(..., embed=True),
    bbox: List[float] = Body(..., embed=True),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Extrai produtos de uma região selecionada de um PDF."""
    record = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent.parent / file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    content = file_path.read_bytes()
    produtos: List[Dict[str, Any]] = []
    log: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for idx, pg in enumerate(pdf.pages):
                if idx + 1 < page:
                    continue
                region = pg.crop(bbox)
                text = region.extract_text(x_tolerance=2, y_tolerance=2)
                if not text:
                    continue
                log.append(f"Pagina {idx+1} processada")
                lines = [l.strip() for l in text.splitlines() if l.strip()]
                data_dict: Dict[str, Any] = {}
                for line in lines:
                    if ":" in line:
                        k, v = line.split(":", 1)
                        data_dict[k.strip()] = v.strip()
                if not data_dict:
                    data_dict = {f"col_{i}": v for i, v in enumerate(lines)}
                produto = file_processing_service._processar_linha_padronizada(
                    data_dict, None
                )
                if produto:
                    produtos.append(produto)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {"produtos": produtos, "log": log}
