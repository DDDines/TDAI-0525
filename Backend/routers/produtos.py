# Backend/routers/produtos.py

from typing import Any, Dict, List, Optional, Union

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
import io
import json
import logging
import re
import time
from logging import FileHandler, Formatter
from pathlib import Path
from uuid import uuid4

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
from Backend.core import config
from Backend.core.config import settings
from Backend.database import SessionLocal
from Backend.services import file_processing_service

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


def _resolve_storage_path(path_value: Union[str, Path]) -> Path:
    """Resolve caminhos relativos de storage sem duplicar prefixo Backend."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    backend_root = Path(__file__).resolve().parent.parent
    project_root = backend_root.parent
    if p.parts and p.parts[0].lower() == "backend":
        return project_root / p
    return backend_root / p


try:
    from Backend.services import validator_crew  # type: ignore
except Exception as validator_import_error:  # pragma: no cover - depends on optional deps
    logger.warning(
        "Validador IA indisponivel no startup (%s). Importacao seguira em modo fallback.",
        validator_import_error,
    )

    class _ValidatorCrewFallback:
        @staticmethod
        def run_validation_crew(raw_data):
            return raw_data

    validator_crew = _ValidatorCrewFallback()  # type: ignore


def _normalizar_dados_validados(candidate: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    """Garante dict para o pipeline mesmo quando o validador retorna texto/JSON string."""
    if isinstance(candidate, dict):
        return candidate
    if isinstance(candidate, str):
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return fallback if isinstance(fallback, dict) else {}


def _sanitize_produto_extraido(prod: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos antes de instanciar ProdutoCreate para evitar descartes por validacao."""
    data = dict(prod) if isinstance(prod, dict) else {}

    extras = data.get("dados_brutos_adicionais") or data.get("dados_brutos_web") or {}
    if not isinstance(extras, dict):
        extras = {"dados_brutos_raw": str(extras)}

    nome_base = data.get("nome_base")
    if nome_base is not None:
        nome_base = str(nome_base).strip()
        if len(nome_base) > 255:
            extras["nome_base_truncado_de"] = nome_base
            nome_base = nome_base[:255]
        data["nome_base"] = nome_base or None

    sku_original = data.get("sku_original")
    if sku_original is not None:
        sku_original = str(sku_original).strip()
        if len(sku_original) > 100:
            extras["sku_original_truncado_de"] = sku_original
            sku_original = sku_original[:100]
        data["sku_original"] = sku_original or None

    ean_original = data.get("ean_original")
    if ean_original is not None:
        ean_text = str(ean_original).strip()
        if ean_text:
            normalized = re.sub(r"[\s\-_/.]", "", ean_text).upper()
            normalized = normalized.replace("O", "0").replace("I", "1").replace("L", "1")
            if re.search(r"[^0-9]", normalized) or len(normalized) not in {8, 12, 13}:
                extras["ean_original_descartado"] = ean_text
                data["ean_original"] = None
            else:
                data["ean_original"] = normalized
        else:
            data["ean_original"] = None

    if extras:
        data["dados_brutos_adicionais"] = extras

    return data

async def _tarefa_processar_catalogo(

    db_session_factory,

    file_id: int,

    user_id: int,

    product_type_id: Optional[int],

    fornecedor_id: int,

    mapping: Optional[Dict[str, str]] = None,

    pages: Optional[List[int]] = None,

    region: Optional[List[float]] = None,

):

    """Processa o arquivo salvo em background e cria os produtos."""

    db: Optional[Session] = None

    try:

        db = db_session_factory()

        catalog_file = (

            db.query(models.CatalogImportFile)

            .filter_by(id=file_id, user_id=user_id)

            .first()

        )

        if not catalog_file:

            logger.error("Catalog file %s not found", file_id)

            return
        catalog_logger.info("inicio file_id=%s user_id=%s fornecedor_id=%s product_type_id=%s pages=%s region=%s mapping_keys=%s", file_id, user_id, fornecedor_id, product_type_id, pages, region, list(mapping.keys()) if mapping else [])

        catalog_file.status = "PROCESSING"

        catalog_file.fornecedor_id = fornecedor_id

        db.commit()



        file_path = _resolve_storage_path(
            Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

        if not file_path.exists():

            catalog_file.status = "FAILED"
            catalog_file.result_summary = {
                "created": [],
                "updated": [],
                "errors": [
                    {
                        "erro_processamento": "Arquivo de catÃ¡logo nÃ£o encontrado no armazenamento.",
                        "file_id": file_id,
                        "stored_filename": catalog_file.stored_filename,
                    }
                ],
            }

            db.commit()

            return

        content = file_path.read_bytes()

        ext = file_path.suffix.lower()

        erros: List[Dict[str, Any]] = []

        produtos_create: List[schemas.ProdutoCreate] = []

        created: List[models.Produto] = []

        updated: List[models.Produto] = []

        if ext == ".pdf":

            import pdfplumber, io



            with pdfplumber.open(io.BytesIO(content)) as pdf:

                total = len(pages) if pages else len(pdf.pages)

            catalog_file.total_pages = total

            catalog_file.pages_processed = 0

            db.commit()

            page_list = pages or list(range(1, total + 1))

            for page in page_list:
                page_start = time.perf_counter()

                created_page: List[models.Produto] = []

                updated_page: List[models.Produto] = []

                produtos_data = await file_processing_service.processar_arquivo_pdf(

                    content,

                    mapeamento_colunas_usuario=mapping,
                    usar_llm=False,

                    product_type_id=product_type_id,

                    pages=[page],

                    region=region,

                )



                for prod in produtos_data:

                    if isinstance(prod, dict) and (

                        prod.get("motivo_descarte")

                        or any(

                            key.startswith("erro_processamento") for key in prod.keys()

                        )

                    ):

                        erros.append(prod)

                        continue

                    

                    # Executa validaÃ§Ã£o IA com fallback resiliente.
                    validated_prod = _normalizar_dados_validados(
                        validator_crew.run_validation_crew(prod),
                        prod,
                    )
                    cleaned_prod = _sanitize_produto_extraido(validated_prod)



                    try:

                        produto_schema = schemas.ProdutoCreate(

                            nome_base=cleaned_prod.get("nome_base")

                            or cleaned_prod.get("sku_original")

                            or "Produto Importado",

                            sku=cleaned_prod.get("sku_original"),

                            ean=cleaned_prod.get("ean_original"),

                            descricao_original=cleaned_prod.get("descricao_original"),

                            marca=cleaned_prod.get("marca"),

                            categoria_original=cleaned_prod.get("categoria_original"),
                            dados_brutos_web=cleaned_prod.get("dados_brutos_adicionais")
                            or cleaned_prod.get("dados_brutos_web"),
                            dynamic_attributes=cleaned_prod.get("dynamic_attributes"),

                            fornecedor_id=catalog_file.fornecedor_id,

                            product_type_id=product_type_id,

                        )

                        produtos_create.append(produto_schema)

                    except Exception as e:

                        erros.append(

                            {

                                "motivo_descarte": f"Erro ao converter linha: {str(e)}",

                                "linha_original": prod,

                                "linha_validada": validated_prod,
                                "linha_sanitizada": cleaned_prod,

                            }

                        )



                if produtos_create:

                    (

                        created_page,

                        updated_page,

                        dup_errors,

                    ) = crud_produtos.create_produtos_bulk(

                        db, produtos_create, user_id=user_id

                    )

                    created.extend(created_page)

                    updated.extend(updated_page)

                    erros.extend(dup_errors) # Simplificado



                    for db_produto in created_page:

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

                    produtos_create = []

                catalog_file.pages_processed += 1

                db.commit()
                catalog_logger.info(
                    "file_id=%s page=%s processed_rows=%s created=%s updated=%s errors_total=%s elapsed=%.2fs",
                    file_id,
                    page,
                    len(produtos_data) if "produtos_data" in locals() else 0,
                    len(created_page),
                    len(updated_page),
                    len(erros),
                    time.perf_counter() - page_start,
                )

        else: # L+Ã‚Â¦gica para outros tipos de arquivo (Excel, CSV)

            catalog_file.total_pages = 1

            catalog_file.pages_processed = 0

            db.commit()

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

            else:

                catalog_file.status = "FAILED"

                db.commit()

                return

            

            created_page: List[models.Produto] = []

            updated_page: List[models.Produto] = []



            for prod in produtos_data:

                if isinstance(prod, dict) and (

                    prod.get("motivo_descarte")

                    or any(key.startswith("erro_processamento") for key in prod.keys())

                ):

                    erros.append(prod)

                    continue



                # Executa validaÃ§Ã£o IA com fallback resiliente.
                validated_prod = _normalizar_dados_validados(
                    validator_crew.run_validation_crew(prod),
                    prod,
                )
                cleaned_prod = _sanitize_produto_extraido(validated_prod)

                

                try:

                    produto_schema = schemas.ProdutoCreate(

                        nome_base=cleaned_prod.get("nome_base")

                        or cleaned_prod.get("sku_original")

                        or "Produto Importado",

                        sku=cleaned_prod.get("sku_original"),

                        ean=cleaned_prod.get("ean_original"),

                        descricao_original=cleaned_prod.get("descricao_original"),

                        marca=cleaned_prod.get("marca"),

                        categoria_original=cleaned_prod.get("categoria_original"),
                        dados_brutos_web=cleaned_prod.get("dados_brutos_adicionais")
                        or cleaned_prod.get("dados_brutos_web"),
                        dynamic_attributes=cleaned_prod.get("dynamic_attributes"),

                        fornecedor_id=catalog_file.fornecedor_id,

                        product_type_id=product_type_id,

                    )

                    produtos_create.append(produto_schema)

                except Exception as e:

                    erros.append(

                        {

                            "motivo_descarte": f"Erro ao converter linha p+Ã‚Â¦s-valida+Ã‚Âº+ÃƒÂºo: {str(e)}",

                            "linha_original": prod,

                            "linha_validada": validated_prod,
                            "linha_sanitizada": cleaned_prod

                        }

                    )

            if produtos_create:

                (

                    created_page,

                    updated_page,

                    dup_errors,

                ) = crud_produtos.create_produtos_bulk(

                    db, produtos_create, user_id=user_id

                )

                created.extend(created_page)

                updated.extend(updated_page)

                erros.extend(dup_errors)



                for db_produto in created_page:

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

                catalog_file.pages_processed = catalog_file.total_pages

            db.commit()



        created_count = len(created)
        updated_count = len(updated)
        errors_count = len(erros)
        final_status = "IMPORTED"
        if created_count + updated_count == 0 and errors_count > 0:
            final_status = "FAILED"

        result_summary = {
            "created": [
                schemas.ProdutoResponse.model_validate(p).model_dump(mode="json")
                for p in created
            ],
            "updated": [
                schemas.ProdutoResponse.model_validate(p).model_dump(mode="json")
                for p in updated
            ],
            "errors": erros,
            "stats": {
                "produtos_criados": created_count,
                "produtos_atualizados": updated_count,
                "erros": errors_count,
                "pages_processed": catalog_file.pages_processed or 0,
                "pages_total": catalog_file.total_pages or 0,
                "ext": ext,
            },
            "log": [
                f"Resumo final: status={final_status}",
                f"Criados={created_count}, Atualizados={updated_count}, Erros={errors_count}",
            ],
        }

        catalog_file.status = final_status
        catalog_file.result_summary = result_summary

        db.add(catalog_file)

        db.commit()
        if final_status == "FAILED":
            first_error = erros[0] if erros else {}
            catalog_logger.warning(
                "falha file_id=%s pages=%s/%s first_error=%s",
                file_id,
                catalog_file.pages_processed,
                catalog_file.total_pages,
                str(first_error)[:1000],
            )
        catalog_logger.info(
            "fim file_id=%s status=%s created=%s updated=%s errors=%s pages=%s/%s",
            file_id,
            final_status,
            created_count,
            updated_count,
            errors_count,
            catalog_file.pages_processed,
            catalog_file.total_pages,
        )

    except Exception as e:

        logger.exception("Erro ao processar importacao de catalogo")
        catalog_logger.exception("falha file_id=%s erro=%s", file_id, e)

        if db:

            catalog_file = (

                db.query(models.CatalogImportFile).filter_by(id=file_id).first()

            )

            if catalog_file:

                catalog_file.status = "FAILED"
                catalog_file.result_summary = {
                    "created": [],
                    "updated": [],
                    "errors": [
                        {
                            "erro_processamento": str(e),
                            "file_id": file_id,
                        }
                    ],
                }

                db.commit()

    finally:

        if db:

            db.close()







@router.post(

    "/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED

)  # CORRIGIDO AQUI

def create_produto(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    produto: schemas.ProdutoCreate,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """

    Cria um novo produto para o usu+ÃƒÂ­rio logado.

    """

    # Valida+Ã‚Âº+ÃƒÂºo do fornecedor, se fornecido

    if produto.fornecedor_id:

        fornecedor = crud_fornecedores.get_fornecedor(

            db, fornecedor_id=produto.fornecedor_id

        )  # Assume que user_id n+ÃƒÂºo +Ã‚Â¬ necess+ÃƒÂ­rio aqui ou +Ã‚Â¬ validado no get_fornecedor se n+ÃƒÂºo for admin

        if (

            not fornecedor

        ):  # Adicionar ( or (not current_user.is_superuser and fornecedor.user_id != current_user.id) ) se necess+ÃƒÂ­rio

            raise HTTPException(

                status_code=404,

                detail=f"Fornecedor com ID {produto.fornecedor_id} n+ÃƒÂºo encontrado.",

            )



    # Valida+Ã‚Âº+ÃƒÂºo do tipo de produto, se fornecido

    if produto.product_type_id:

        product_type = crud_product_types.get_product_type(

            db, product_type_id=produto.product_type_id

        )

        if (

            not product_type

        ):  # Adicionar valida+Ã‚Âº+ÃƒÂºo de owner se tipos de produto forem espec+Ã‚Â¡ficos do usu+ÃƒÂ­rio

            raise HTTPException(

                status_code=404,

                detail=f"Tipo de Produto com ID {produto.product_type_id} n+ÃƒÂºo encontrado.",

            )



    # A fun+Ã‚Âº+ÃƒÂºo crud_produtos.create_produto (ou create_user_produto) lida com a l+Ã‚Â¦gica de cria+Ã‚Âº+ÃƒÂºo

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

    skip: int = Query(0, ge=0, description="N+Ã‚Â¦mero de itens para pular"),

    limit: int = Query(

        10, ge=1, le=100, description="N+Ã‚Â¦mero m+ÃƒÂ­ximo de itens por p+ÃƒÂ­gina"

    ),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    query = db.query(models.CatalogImportFile).filter(

        models.CatalogImportFile.user_id == current_user.id

    )

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

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



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

    product_type_id: Optional[int] = Body(None, embed=True),

    fornecedor_id: Optional[int] = Body(None, embed=True),

    mapping: Optional[Dict[str, str]] = Body(None),
    pages: Optional[List[int]] = Body(None),
    region: Optional[List[float]] = Body(None),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    catalog_file = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not catalog_file:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")

    fornecedor_id_final = fornecedor_id or catalog_file.fornecedor_id
    if not fornecedor_id_final:
        raise HTTPException(
            status_code=400,
            detail="fornecedor_id Ã© obrigatÃ³rio para reprocessar este arquivo.",
        )


    catalog_file.status = "PROCESSING"

    catalog_file.fornecedor_id = fornecedor_id_final

    catalog_file.pages_processed = 0

    catalog_file.total_pages = 0

    db.commit()



    if mapping is None:

        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id_final)

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

        fornecedor_id=fornecedor_id_final,

        mapping=mapping,

        pages=pages,
        region=region,

    )



    return {"status": "PROCESSING", "file_id": file_id}





@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI

def read_produto(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """

    Obt+Ã‚Â¬m os detalhes de um produto espec+Ã‚Â¡fico.

    """

    db_produto = crud_produtos.get_produto(

        db, produto_id=produto_id

    )  # crud_produtos.get_produto n+ÃƒÂºo filtra por user_id por padr+ÃƒÂºo



    if db_produto is None:

        raise HTTPException(status_code=404, detail="Produto n+ÃƒÂºo encontrado")



    # Verifica a permiss+ÃƒÂºo para visualizar

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N+ÃƒÂºo autorizado a visualizar este produto"

        )

    return db_produto





# Tamb+Ã‚Â¬m exp+Ã‚Â¦e a rota com barra ao final para evitar redirecionamentos que podem

# levar +ÃƒÂ¡ perda do cabe+Ã‚Âºalho Authorization em alguns clientes HTTP.

router.add_api_route(

    "/{produto_id}/",

    read_produto,

    methods=["GET"],

    response_model=schemas.ProdutoResponse,

    include_in_schema=False,

)





@router.get("/", response_model=schemas.ProdutoPage)  # Este j+ÃƒÂ­ estava correto

def read_produtos(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    db: Session = Depends(database.get_db),

    skip: int = Query(0, ge=0, description="N+Ã‚Â¦mero de itens para pular"),

    limit: int = Query(

        10, ge=1, le=200, description="N+Ã‚Â¦mero m+ÃƒÂ­ximo de itens por p+ÃƒÂ­gina"

    ),

    sort_by: Optional[str] = Query(

        None, description="Campo para ordena+Ã‚Âº+ÃƒÂºo (ex: nome_base, preco_venda)"

    ),  # Ajustado para nome_base

    sort_order: Optional[str] = Query(

        "asc", description="Ordem da ordena+Ã‚Âº+ÃƒÂºo (asc ou desc)"

    ),

    search: Optional[str] = Query(

        None, description="Termo de busca para nome, descri+Ã‚Âº+ÃƒÂºo, SKU, EAN"

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

        None, description="Filtrar por status de gera+Ã‚Âº+ÃƒÂºo de t+Ã‚Â¡tulo por IA"

    ),

    status_descricao_ia: Optional[models.StatusGeracaoIAEnum] = Query(

        None, description="Filtrar por status de gera+Ã‚Âº+ÃƒÂºo de descri+Ã‚Âº+ÃƒÂºo por IA"

    ),

    product_type_id: Optional[int] = Query(

        None, description="ID do Tipo de Produto para filtrar produtos"

    ),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    user_id_filter = None if current_user.is_superuser else current_user.id



    # Usando get_produtos_by_user do crud, que foi ajustado para receber user_id opcional ou is_admin

    produtos_db = crud_produtos.get_produtos_by_user(  # Nome da fun+Ã‚Âº+ÃƒÂºo no CRUD

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

    total_items = crud_produtos.count_produtos_by_user(  # Nome da fun+Ã‚Âº+ÃƒÂºo no CRUD

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

def update_produto(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    produto_id: int,

    produto: schemas.ProdutoUpdate,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)

    if db_produto is None:

        raise HTTPException(status_code=404, detail="Produto n+ÃƒÂºo encontrado")

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N+ÃƒÂºo autorizado a modificar este produto"

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

        ):  # Adicionar ( or (not current_user.is_superuser and fornecedor.user_id != current_user.id) ) se necess+ÃƒÂ­rio

            raise HTTPException(

                status_code=404,

                detail=f"Fornecedor com ID {produto.fornecedor_id} n+ÃƒÂºo encontrado.",

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

                detail=f"Tipo de Produto com ID {produto.product_type_id} n+ÃƒÂºo encontrado.",

            )



    # A fun+Ã‚Âº+ÃƒÂºo crud_produtos.update_produto espera o objeto db_produto

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

def delete_produto(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)

    if db_produto is None:

        raise HTTPException(status_code=404, detail="Produto n+ÃƒÂºo encontrado")

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N+ÃƒÂºo autorizado a deletar este produto"

        )



    # A fun+Ã‚Âº+ÃƒÂºo crud_produtos.delete_produto espera o objeto db_produto

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





# Expondo rotas com barra final para opera+Ã‚Âº+Ã‚Â¦es de atualiza+Ã‚Âº+ÃƒÂºo e dele+Ã‚Âº+ÃƒÂºo.

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

)  # Este j+ÃƒÂ­ estava correto

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



    for produto_id_val in produto_ids:  # Ajustado nome da vari+ÃƒÂ­vel

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

        )  # Adiciona o objeto que foi deletado (j+ÃƒÂ­ +Ã‚Â¬ um objeto do modelo)



    # Construindo a resposta

    # A convers+ÃƒÂºo para schemas.ProdutoResponse +Ã‚Â¬ feita automaticamente pelo FastAPI

    # devido ao response_model=List[schemas.ProdutoResponse]



    if not_found_ids or not_authorized_ids:

        error_detail_parts = []

        if not_found_ids:

            error_detail_parts.append(f"Produtos n+ÃƒÂºo encontrados: IDs {not_found_ids}.")

        if not_authorized_ids:

            error_detail_parts.append(

                f"N+ÃƒÂºo autorizado a deletar produtos: IDs {not_authorized_ids}."

            )



        # Se nenhum produto foi deletado com sucesso E houve erros, levanta uma exce+Ã‚Âº+ÃƒÂºo.

        # Se alguns foram deletados, retorna os deletados e o cliente pode precisar ser informado das falhas.

        if not deleted_produtos:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail=" ".join(error_detail_parts),

            )

        # Se alguns foram deletados, a resposta incluir+ÃƒÂ­ apenas eles.

        # O frontend pode precisar verificar a diferen+Ã‚Âºa entre a lista enviada e a recebida.



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

async def upload_produto_image(  # Nome da fun+Ã‚Âº+ÃƒÂºo mantido como no arquivo do usu+ÃƒÂ­rio

    produto_id: int,

    file: UploadFile = File(...),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)

    if not db_produto:

        raise HTTPException(status_code=404, detail="Produto n+ÃƒÂºo encontrado")

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N+ÃƒÂºo autorizado a modificar este produto"

        )



    try:

        file_path_in_db = await crud_produtos.save_produto_image(db, produto_id, file)

    except ValueError as e:

        raise HTTPException(status_code=400, detail=str(e))

    except IOError as e:  # Captura erro de IO de save_produto_image

        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:

        raise HTTPException(

            status_code=500, detail=f"N+ÃƒÂºo foi poss+Ã‚Â¡vel salvar a imagem: {str(e)}"

        )



    # Atualiza o campo imagem_principal_url no produto

    # O schema ProdutoUpdate pode n+ÃƒÂºo ter imagem_principal_url se n+ÃƒÂºo for edit+ÃƒÂ­vel diretamente

    # mas o modelo tem. O CRUD pode ter uma l+Ã‚Â¦gica para isso.

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

    dpi: int = Form(72),

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Gera preview de um cat+ÃƒÂ­logo enviado e salva o arquivo para posterior processamento."""



    # L+Ã‚Â¬ o conte+Ã‚Â¦do para gerar o preview

    content = await file.read()

    start = time.perf_counter()

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

                content, ext, start_page, page_count, dpi

            )

        else:

            preview_tabular = await file_processing_service.gerar_preview(content, ext)
            if preview_tabular.get("error"):
                return schemas.ImportPreviewResponse(
                    file_id=catalog_record.id,
                    num_pages=0,
                    table_pages=[],
                    sample_rows=[],
                    preview_images=[],
                    headers=[],
                    error=preview_tabular.get("error"),
                )
            preview = {
                "num_pages": 1,
                "table_pages": [1],
                "sample_rows": preview_tabular.get("sample_rows", []),
                "preview_images": [],
                "headers": preview_tabular.get("headers", []),
            }

        duration = time.perf_counter() - start

        logger.info(

            "Preview generation for catalog file %s took %.4f seconds",

            catalog_record.id,

            duration,

        )

        return schemas.ImportPreviewResponse(

            **preview, error=None, file_id=catalog_record.id

        )

    except Exception as e:

        return schemas.ImportPreviewResponse(

            file_id=catalog_record.id,

            num_pages=0,

            table_pages=[],

            sample_rows={},

            preview_images=[],

            error=f"Falha ao gerar preview de PDF: {e}",

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

    """Importa um arquivo de cat+ÃƒÂ­logo e cria produtos vinculados ao fornecedor."""

    content = await file.read()

    ext = Path(file.filename).suffix.lower()

    mapping_dict = None

    if mapeamento_colunas_usuario:

        try:

            mapping_dict = json.loads(mapeamento_colunas_usuario)

        except Exception:

            raise HTTPException(

                status_code=400, detail="mapeamento_colunas_usuario inv+ÃƒÂ­lido"

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

        raise HTTPException(status_code=400, detail="Formato de arquivo n+ÃƒÂºo suportado")



    produtos_create = []

    erros: List[Dict[str, Any]] = []

    for prod in produtos_data:

        if isinstance(prod, dict) and (

            prod.get("motivo_descarte")

            or any(key.startswith("erro_processamento") for key in prod.keys())

        ):

            erros.append(prod)

            continue

        cleaned_prod = _sanitize_produto_extraido(prod)

        try:

            produto_schema = schemas.ProdutoCreate(

                nome_base=cleaned_prod.get("nome_base")

                or cleaned_prod.get("sku_original")

                or "Produto Importado",

                sku=cleaned_prod.get("sku_original"),

                ean=cleaned_prod.get("ean_original"),

                descricao_original=cleaned_prod.get("descricao_original"),

                marca=cleaned_prod.get("marca"),

                categoria_original=cleaned_prod.get("categoria_original"),
                dados_brutos_web=cleaned_prod.get("dados_brutos_adicionais")
                or cleaned_prod.get("dados_brutos_web"),
                dynamic_attributes=cleaned_prod.get("dynamic_attributes"),

                fornecedor_id=fornecedor_id,

            )

            produtos_create.append(produto_schema)

        except Exception as e:

            erros.append(

                {

                    "motivo_descarte": f"Erro ao converter linha: {str(e)}",

                    "linha_original": prod,
                    "linha_sanitizada": cleaned_prod,

                }

            )



    created: List[models.Produto] = []

    updated: List[models.Produto] = []

    if produtos_create:

        created, updated, dup_errors = crud_produtos.create_produtos_bulk(

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

    return {

        "produtos_criados": created,

        "produtos_atualizados": updated,

        "erros": erros,

    }





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

    catalog_file = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not catalog_file:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    catalog_file.status = "PROCESSING"

    catalog_file.fornecedor_id = fornecedor_id

    db.commit()



    from sqlalchemy.orm import sessionmaker



    db_session_factory = sessionmaker(bind=db.get_bind())

    # Sempre reprocessa o arquivo completo para evitar importar apenas as linhas de preview

    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
    )

    if not file_path.exists():

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    if mapping is None:

        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id)

        if fornecedor and fornecedor.default_column_mapping:

            mapping = fornecedor.default_column_mapping



    background_tasks.add_task(

        _tarefa_processar_catalogo,

        db_session_factory=db_session_factory,

        file_id=file_id,

        user_id=current_user.id,

        product_type_id=product_type_id,

        fornecedor_id=fornecedor_id,

        mapping=mapping,

        pages=pages,
        region=region,

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

    """Retorna o status atual do processamento do cat+ÃƒÂ­logo."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")

    return record





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

    """Vers+ÃƒÂºo simplificada do status de importa+Ã‚Âº+ÃƒÂºo."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")

    if record.status == "IMPORTED":
        status = "DONE"
    elif record.status == "FAILED":
        status = "FAILED"
    else:
        status = "PROCESSING"

    return {

        "status": status,

        "pages_total": record.total_pages or 0,

        "pages_processed": record.pages_processed,

    }





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

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")

    if record.status not in ["IMPORTED", "FAILED"] or not record.result_summary:

        raise HTTPException(status_code=400, detail="Resultados ainda nao disponiveis")

    return record.result_summary





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

    """Processa todas as p+ÃƒÂ­ginas de um cat+ÃƒÂ­logo PDF a partir de ``start_page``."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    )

    if not file_path.exists():

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    content = file_path.read_bytes()

    ext = file_path.suffix.lower()

    if ext != ".pdf":

        raise HTTPException(status_code=400, detail="Formato de arquivo n+ÃƒÂºo suportado")



    with pdfplumber.open(io.BytesIO(content)) as pdf:

        total_pages = len(pdf.pages)



    pages = list(range(start_page, total_pages + 1))



    if mapping is None and record.fornecedor_id:

        fornecedor = crud_fornecedores.get_fornecedor(db, record.fornecedor_id)

        if fornecedor and fornecedor.default_column_mapping:

            mapping = fornecedor.default_column_mapping



    from sqlalchemy.orm import sessionmaker



    db_session_factory = sessionmaker(bind=db.get_bind())



    await _tarefa_processar_catalogo(

        db_session_factory=db_session_factory,

        file_id=file_id,

        user_id=current_user.id,

        product_type_id=None,

        fornecedor_id=record.fornecedor_id,

        mapping=mapping,

        pages=pages,

    )



    db.refresh(record)

    return record.result_summary





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
    record = (
        db.query(models.CatalogImportFile)
        .filter_by(id=file_id, user_id=current_user.id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    )
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

    produtos: List[Dict[str, Any]] = []
    log: List[str] = []
    preview_headers: List[str] = []
    preview_rows: List[Dict[str, Any]] = []

    try:
        with pdfplumber.open(file_path) as pdf:
            if not (1 <= page <= len(pdf.pages)):
                raise HTTPException(
                    status_code=400,
                    detail=f"Numero de pagina invalido: {page}. PDF tem {len(pdf.pages)} paginas.",
                )
            target_page = pdf.pages[page - 1]

            selected_bbox = bbox
            if bbox_norm and len(bbox_norm) == 4:
                selected_bbox = [
                    float(bbox_norm[0]) * target_page.width,
                    float(bbox_norm[1]) * target_page.height,
                    float(bbox_norm[2]) * target_page.width,
                    float(bbox_norm[3]) * target_page.height,
                ]

            x0, y0, x1, y1 = map(float, selected_bbox)
            x0 = max(0.0, min(x0, float(target_page.width)))
            y0 = max(0.0, min(y0, float(target_page.height)))
            x1 = max(0.0, min(x1, float(target_page.width)))
            y1 = max(0.0, min(y1, float(target_page.height)))
            if x1 <= x0 or y1 <= y0:
                raise HTTPException(status_code=400, detail="BBox invalido para a pagina selecionada.")
            selected_bbox = [x0, y0, x1, y1]

        df_region = file_processing_service.extract_data_from_pdf_region(
            str(file_path),
            page,
            selected_bbox,
        )

        if not df_region.empty:
            preview_headers = [str(c) for c in df_region.columns.tolist()]
            preview_rows = [
                {
                    str(k): (
                        None if (v is None or (isinstance(v, float) and str(v) == "nan")) else v
                    )
                    for k, v in row.items()
                }
                for row in df_region.to_dict(orient="records")
            ]

            for row in preview_rows:
                produto = file_processing_service._processar_linha_padronizada(row, None)
                if produto:
                    produtos.append(produto)

            log.append(
                f"Pagina {page}: extraidas {len(preview_rows)} linhas e {len(preview_headers)} colunas da regiao."
            )
        else:
            log.append(f"Pagina {page}: nenhuma linha extraida da regiao selecionada.")

        logger.info(
            "selecionar_regiao: file_id=%s, page=%s, bbox=%s, bbox_norm=%s, produtos_extraidos=%s",
            file_id,
            page,
            selected_bbox,
            bbox_norm,
            len(produtos),
        )
        logger.info("selecionar_regiao: preview_headers=%s", preview_headers[:30])
        logger.info("selecionar_regiao: preview_rows_sample=%s", preview_rows[:3])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return {
        "produtos": produtos,
        "log": log,
        "preview_headers": preview_headers,
        "preview_rows": preview_rows[:100],
    }
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

    """Retorna imagem, texto e tabela de uma +Ã‚Â¦nica p+ÃƒÂ­gina de um PDF."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    )

    if not file_path.exists():

        raise HTTPException(status_code=404, detail="Arquivo n+ÃƒÂºo encontrado")



    content = file_path.read_bytes()

    try:

        page_data = await file_processing_service.extrair_pagina_pdf(

            content, page_number

        )

    except ValueError as e:

        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:

        raise HTTPException(status_code=500, detail=str(e))



    return page_data

