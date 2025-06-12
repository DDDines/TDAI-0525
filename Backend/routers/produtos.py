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
    page_count: int = Query(1, ge=1, description="Número de páginas de preview do PDF"),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Salva o arquivo enviado, gera preview e registra no banco."""
    saved = await file_processing_service.save_uploaded_catalog(file, fornecedor_id)
    saved.user_id = current_user.id
    db.add(saved)
    db.commit()
    db.refresh(saved)

    ext = Path(saved.stored_filename).suffix.lower()
    file_path = Path(settings.UPLOAD_DIRECTORY) / "catalogs" / saved.stored_filename
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent.parent / file_path
    content = file_path.read_bytes()

    try:
        preview = await file_processing_service.gerar_preview(content, ext)
    except ValueError:
        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")

    if ext == ".pdf":
        preview_images = await file_processing_service.pdf_pages_to_images(
            content, max_pages=page_count
        )
        preview["preview_images"] = preview_images

    preview["file_id"] = saved.id
    return preview


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
        created = crud_produtos.create_produtos_bulk(
            db, produtos_create, user_id=current_user.id
        )
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
    response_model=schemas.ImportCatalogoResponse,
)
async def importar_catalogo_finalizar(
    file_id: int,
    product_type_id: int = Body(..., embed=True),
    fornecedor_id: int = Body(..., embed=True),
    mapping: Optional[Dict[str, str]] = Body(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """Processa o arquivo salvo e cria produtos definitivos."""
    catalog_file = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not catalog_file:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # persiste o fornecedor definido nesta etapa
    catalog_file.fornecedor_id = fornecedor_id

    file_path = (
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
    )
    if not file_path.is_absolute():
        file_path = Path(__file__).resolve().parent.parent / file_path
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado no disco")

    # Sempre reprocessa o arquivo completo para evitar importar apenas as linhas de preview
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
        )
    else:
        raise HTTPException(
            status_code=400, detail="Formato de arquivo não suportado"
        )

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
            erros.append(
                {
                    "motivo_descarte": f"Erro ao converter linha: {str(e)}",
                    "linha_original": prod,
                }
            )

    created: List[models.Produto] = []
    if produtos_create:
        created = crud_produtos.create_produtos_bulk(
            db, produtos_create, user_id=current_user.id
        )
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

    catalog_file.status = "IMPORTED"
    db.add(catalog_file)
    db.commit()

    return {"produtos_criados": created, "erros": erros}


