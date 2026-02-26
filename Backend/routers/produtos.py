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
from Backend.application.services import (
    CatalogImportFileService,
    CatalogImportLegacyIngestService,
    CatalogImportFinalizeService,
    CatalogImportPreviewService,
    CatalogImportStartService,
    CatalogImportStatusService,
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


def _normalize_import_text(value: str) -> str:
    return catalog_sanitization_service.normalize_import_text(value)


def _normalize_import_issue_item(item: Dict[str, Any]) -> Dict[str, Any]:
    return catalog_sanitization_service.normalize_import_issue_item(item)


def _extract_import_error_reason(error_item: Dict[str, Any]) -> str:
    return catalog_sanitization_service.extract_import_error_reason(error_item)


def _is_non_critical_import_reason(reason: str) -> bool:
    return catalog_sanitization_service.is_non_critical_import_reason(reason)


def _alnum_len(value: Any) -> int:
    return catalog_quality_service.alnum_len(value)


def _texto_tem_contexto(value: Any) -> bool:
    return catalog_quality_service.text_has_context(value)



def _fold_ascii_text(value: Any) -> str:
    return catalog_quality_service.fold_ascii_text(value)


def _texto_parece_nome_peca(value: Any) -> bool:
    return catalog_quality_service.text_looks_like_part_name(value)


def _texto_parece_aplicacao_veicular(value: Any) -> bool:
    return catalog_quality_service.text_looks_like_vehicle_application(value)


def _texto_parece_codigo_peca(value: Any) -> bool:
    return catalog_quality_service.text_looks_like_part_code(value)


def _nome_parece_cabecalho_anotacao(value: Any) -> bool:
    return catalog_quality_service.name_looks_like_annotation_header(value)


def _nome_parece_ruido_ocr(value: Any) -> bool:
    return catalog_quality_service.name_looks_like_ocr_noise(value)


def _avaliar_qualidade_linha_produto(data: Dict[str, Any]) -> Optional[str]:
    return catalog_quality_service.evaluate_product_row_quality(data)


def _score_qualidade_linha_produto(data: Dict[str, Any]) -> int:
    return catalog_quality_service.score_product_row_quality(data)


def _classificar_qualidade_linha_produto(data: Dict[str, Any]) -> Dict[str, Any]:
    return catalog_quality_service.classify_product_row_quality(data)


def _write_catalog_import_report(
    *,
    file_id: int,
    status: str,
    created_count: int,
    updated_count: int,
    errors: List[Dict[str, Any]],
    ignored_count: int = 0,
    ignored_reasons: Optional[List[tuple[str, int]]] = None,
    ignored_samples: Optional[List[Dict[str, Any]]] = None,
    quarantine_count: int = 0,
    quarantine_reasons: Optional[List[tuple[str, int]]] = None,
    quarantine_samples: Optional[List[Dict[str, Any]]] = None,
    accepted_quality_avg: Optional[float] = None,
    quarantine_quality_avg: Optional[float] = None,
    pages_processed: int,
    pages_total: int,
    ext: str,
) -> Optional[Path]:
    """Persist reports for each import to simplify post-mortem diagnostics."""
    try:
        report_dir = catalog_log_dir / "import_jobs"
        report_dir.mkdir(parents=True, exist_ok=True)
        reasons = Counter(_extract_import_error_reason(err) for err in errors if isinstance(err, dict))
        payload = {
            "file_id": file_id,
            "status": status,
            "stats": {
                "created": created_count,
                "updated": updated_count,
                "errors": len(errors),
                "ignored_non_critical": ignored_count,
                "quarantine_non_critical": quarantine_count,
                "quality_score_avg_accepted": accepted_quality_avg,
                "quality_score_avg_quarantine": quarantine_quality_avg,
                "pages_processed": pages_processed,
                "pages_total": pages_total,
                "ext": ext,
            },
            "error_reasons_top": reasons.most_common(30),
            "ignored_reasons_top": ignored_reasons or [],
            "ignored_samples": ignored_samples or [],
            "quarantine_reasons_top": quarantine_reasons or [],
            "quarantine_samples": quarantine_samples or [],
            "errors": errors,
        }
        report_path = report_dir / f"import_{file_id}.json"
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return report_path
    except Exception as report_err:
        catalog_logger.warning(
            "falha ao salvar relatorio detalhado file_id=%s erro=%s",
            file_id,
            report_err,
        )
        return None


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


validator_crew = ValidatorCrewFacade(logger=logger)


def _normalizar_dados_validados(candidate: Any, fallback: Dict[str, Any]) -> Dict[str, Any]:
    return catalog_sanitization_service.normalize_validated_data(candidate, fallback)


def _sanitize_produto_extraido(prod: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza campos antes de instanciar ProdutoCreate para evitar descartes por validacao."""
    return catalog_sanitization_service.sanitize_extracted_product(prod)

    # Legacy fallback mantido apenas para rollback/comparacao historica.
    data = dict(prod) if isinstance(prod, dict) else {}

    # Une dados_brutos_adicionais + dados_brutos_web para nao perder contexto util.
    extras: Dict[str, Any] = {}
    for raw_key in ("dados_brutos_adicionais", "dados_brutos_web"):
        raw_payload = data.get(raw_key)
        if isinstance(raw_payload, dict):
            for key, value in raw_payload.items():
                if key in extras and extras.get(key) != value:
                    extras[f"{raw_key}_{key}"] = value
                else:
                    extras[key] = value
        elif raw_payload not in (None, "", [], {}):
            extras[f"{raw_key}_raw"] = str(raw_payload)

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
        if sku_original.lower() in {"none", "null", "nan", "na", "n/a", "-", "--"}:
            extras["sku_original_descartado"] = sku_original
            sku_original = ""
        if len(sku_original) > 100:
            extras["sku_original_truncado_de"] = sku_original
            sku_original = sku_original[:100]
        data["sku_original"] = sku_original or None

    marca = data.get("marca")
    if marca is not None:
        marca = str(marca).strip()
        if len(marca) > 100:
            extras["marca_truncada_de"] = marca
            marca = marca[:100]
        data["marca"] = marca or None

    modelo = data.get("modelo")
    if modelo is not None:
        modelo = str(modelo).strip()
        if len(modelo) > 100:
            extras["modelo_truncado_de"] = modelo
            modelo = modelo[:100]
        data["modelo"] = modelo or None

    categoria_original = data.get("categoria_original")
    if categoria_original is not None:
        categoria_original = str(categoria_original).strip()
        if len(categoria_original) > 150:
            extras["categoria_original_truncada_de"] = categoria_original
            categoria_original = categoria_original[:150]
        data["categoria_original"] = categoria_original or None

    descricao_original = data.get("descricao_original")
    if descricao_original is not None:
        descricao_original = str(descricao_original).strip()
        if len(descricao_original) > 5000:
            extras["descricao_original_truncada_de"] = descricao_original
            descricao_original = descricao_original[:5000]
        data["descricao_original"] = descricao_original or None

    ean_original = data.get("ean_original")
    if ean_original is not None:
        ean_text = str(ean_original).strip()
        if ean_text:
            # Aceita apenas EAN informado como numero + separadores.
            # Evita transformar textos livres ("Actros 2651 - 2016") em falso EAN.
            if not re.fullmatch(r"[\d\s\-_/.]+", ean_text):
                extras["ean_original_descartado"] = ean_text
                data["ean_original"] = None
            else:
                normalized = re.sub(r"[\s\-_/.]", "", ean_text)
                if 1 <= len(normalized) <= 13:
                    data["ean_original"] = normalized
                else:
                    extras["ean_original_descartado"] = ean_text
                    data["ean_original"] = None
        else:
            data["ean_original"] = None

    # Recupera nome quando OCR traz somente codigo no nome_base.
    nome_base = str(data.get("nome_base") or "").strip()
    sku_original = str(data.get("sku_original") or "").strip()
    descricao_original = str(data.get("descricao_original") or "").strip()
    categoria_original = str(data.get("categoria_original") or "").strip()
    nome_compacto = re.sub(r"[^0-9A-Za-z]", "", nome_base).lower()
    sku_compacto = re.sub(r"[^0-9A-Za-z]", "", sku_original).lower()
    nome_numerico = bool(nome_compacto) and nome_compacto.isdigit()
    nome_codigo_peca = _texto_parece_codigo_peca(nome_base)
    nome_igual_sku = bool(nome_compacto and sku_compacto and nome_compacto == sku_compacto)
    nome_ruido_ocr = _nome_parece_ruido_ocr(nome_base)
    descricao_util = _texto_tem_contexto(descricao_original)
    descricao_parece_peca = _texto_parece_nome_peca(descricao_original)
    descricao_parece_aplicacao = _texto_parece_aplicacao_veicular(descricao_original)

    if nome_base and _nome_parece_cabecalho_anotacao(nome_base):
        extras["nome_base_descartado"] = nome_base
        nome_base = ""
        data["nome_base"] = None

    # Quando categoria parece conter nome de peca e descricao esta vazia,
    # aproveita categoria como descricao para nao perder contexto util.
    if not descricao_util and categoria_original and _texto_parece_nome_peca(categoria_original):
        data["descricao_original"] = categoria_original[:5000]
        descricao_original = data["descricao_original"]
        descricao_util = _texto_tem_contexto(descricao_original)
        descricao_parece_peca = _texto_parece_nome_peca(descricao_original)
        descricao_parece_aplicacao = _texto_parece_aplicacao_veicular(descricao_original)
        extras["descricao_substituida_por_categoria"] = True

    # Se descricao atual e apenas aplicacao e categoria contem nome de peca,
    # prioriza categoria como descricao principal.
    if (
        descricao_util
        and descricao_parece_aplicacao
        and categoria_original
        and _texto_parece_nome_peca(categoria_original)
    ):
        data["descricao_original"] = categoria_original[:5000]
        descricao_original = data["descricao_original"]
        descricao_util = _texto_tem_contexto(descricao_original)
        descricao_parece_peca = _texto_parece_nome_peca(descricao_original)
        descricao_parece_aplicacao = _texto_parece_aplicacao_veicular(descricao_original)
        extras["descricao_aplicacao_substituida_por_categoria"] = True

    nome_fraco = (
        not nome_base
        or nome_numerico
        or nome_codigo_peca
        or nome_igual_sku
        or nome_ruido_ocr
        or _nome_parece_cabecalho_anotacao(nome_base)
    )

    # Tenta recuperar descricao util a partir de dados brutos (colunas nao mapeadas).
    # Também corrige casos em que a descricao atual é apenas aplicacao veicular.
    should_try_raw_part = (
        not descricao_util
        or (descricao_parece_aplicacao and nome_fraco)
        or (nome_fraco and not descricao_parece_peca)
    )
    if should_try_raw_part and isinstance(extras, dict):
        for raw_key, raw_value in extras.items():
            candidate = str(raw_value or "").strip()
            if not candidate:
                continue
            if _texto_parece_nome_peca(candidate):
                if data.get("descricao_original") != candidate:
                    data["descricao_original"] = candidate[:5000]
                descricao_original = data["descricao_original"]
                descricao_util = _texto_tem_contexto(descricao_original)
                descricao_parece_peca = _texto_parece_nome_peca(descricao_original)
                descricao_parece_aplicacao = _texto_parece_aplicacao_veicular(descricao_original)
                extras["descricao_substituida_por_dados_brutos"] = str(raw_key)
                break

    # Se nome e' apenas codigo/sku, tenta promover descricao util para nome_base.
    if descricao_util and (
        not nome_base
        or nome_numerico
        or nome_codigo_peca
        or nome_igual_sku
        or nome_ruido_ocr
        or _nome_parece_cabecalho_anotacao(nome_base)
    ):
        if descricao_parece_peca or nome_numerico or (not nome_base and not descricao_parece_aplicacao):
            data["nome_base"] = descricao_original[:255]
            extras["nome_base_substituido_por_descricao"] = True

    if extras:
        data["dados_brutos_adicionais"] = extras

    return data


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
    resolve_storage_path=_resolve_storage_path,
    normalize_import_issue_item=_normalize_import_issue_item,
    extract_import_error_reason=_extract_import_error_reason,
    is_non_critical_import_reason=_is_non_critical_import_reason,
    normalizar_dados_validados=_normalizar_dados_validados,
    sanitize_produto_extraido=_sanitize_produto_extraido,
    classificar_qualidade_linha_produto=_classificar_qualidade_linha_produto,
    write_catalog_import_report=_write_catalog_import_report,
    normalize_import_text=_normalize_import_text,
)

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

    await catalog_import_task_runner.execute_legacy(
        db_session_factory=db_session_factory,
        file_id=file_id,
        user_id=user_id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,
    )


async def _oop_tarefa_processar_catalogo(**task_kwargs):
    """Executor OOP dedicado (modo oop), separado do legado para comparacao futura."""
    await catalog_import_task_runner.execute_oop(**task_kwargs)

catalog_import_finalize_service = CatalogImportFinalizeService(
    legacy_executor=_tarefa_processar_catalogo,
    oop_executor=_oop_tarefa_processar_catalogo,
)
catalog_import_start_service = CatalogImportStartService(
    models=models,
    crud_fornecedores=crud_fornecedores,
    settings=settings,
    resolve_storage_path=_resolve_storage_path,
    finalize_service=catalog_import_finalize_service,
)
catalog_import_status_service = CatalogImportStatusService(models=models)
catalog_import_file_service = CatalogImportFileService(
    models=models,
    file_processing_service=file_processing_service,
    catalog_import_start_service=catalog_import_start_service,
)
catalog_import_preview_service = CatalogImportPreviewService(
    models=models,
    settings=settings,
    file_processing_service=file_processing_service,
    resolve_storage_path=_resolve_storage_path,
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
    normalize_import_issue_item=_normalize_import_issue_item,
    extract_import_error_reason=_extract_import_error_reason,
    is_non_critical_import_reason=_is_non_critical_import_reason,
    sanitize_produto_extraido=_sanitize_produto_extraido,
    classificar_qualidade_linha_produto=_classificar_qualidade_linha_produto,
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
    catalog_file = catalog_import_start_service.get_catalog_file_or_404(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    catalog_import_start_service.mark_processing(
        db=db,
        catalog_file=catalog_file,
        fornecedor_id=fornecedor_id,
        reset_pages=False,
    )
    # Sempre reprocessa o arquivo completo para evitar importar apenas as linhas de preview.
    catalog_import_start_service.ensure_catalog_binary_exists(catalog_file=catalog_file)
    mapping = catalog_import_start_service.resolve_mapping(
        db=db,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
    )
    command = catalog_import_start_service.build_finalize_command(
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,
    )
    await catalog_import_start_service.dispatch_finalize(
        background_tasks=background_tasks,
        db=db,
        command=command,
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

    """Retorna o status atual do processamento do cat?logo."""
    return catalog_import_status_service.get_record_or_404(
        db=db,
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

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """Vers?o simplificada do status de importa??o."""
    record = catalog_import_status_service.get_record_or_404(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    return catalog_import_status_service.build_simple_status(record=record)





@router.get(

    "/importar-catalogo-result/{file_id}/",

    response_model=Union[schemas.CatalogImportResult, schemas.CatalogImportResultPending],

)

def importar_catalogo_result(

    file_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):
    record = catalog_import_status_service.get_record_or_404(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    return catalog_import_status_service.build_result_response(record=record)





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
    record = catalog_import_start_service.get_catalog_file_or_404(
        db=db,
        file_id=file_id,
        user_id=current_user.id,
    )
    fornecedor_id_final = catalog_import_start_service.resolve_fornecedor_id(
        catalog_file=record,
        fornecedor_id=record.fornecedor_id,
        required_message="fornecedor_id e obrigatorio para processar este arquivo.",
    )

    pages = catalog_import_start_service.resolve_pdf_pages(
        catalog_file=record,
        start_page=start_page,
    )



    mapping = catalog_import_start_service.resolve_mapping(
        db=db,
        fornecedor_id=fornecedor_id_final,
        mapping=mapping,
    )
    command = catalog_import_start_service.build_finalize_command(
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=None,
        fornecedor_id=fornecedor_id_final,
        mapping=mapping,
        pages=pages,
        region=None,
    )
    await catalog_import_start_service.run_finalize_direct(
        db=db,
        command=command,
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



