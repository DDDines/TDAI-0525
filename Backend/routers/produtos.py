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
from fastapi.responses import JSONResponse
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
from Backend.application.contracts.pipeline_commands import CatalogImportFinalizeCommand
from Backend.application.orchestrators.catalog_import import (
    CatalogImportPipelineOrchestrator,
)
from Backend.application.services import (
    FileProcessingFacade,
    CatalogImportSanitizationService,
    CatalogImportQualityService,
    PipelineDispatcher,
    ValidatorCrewFacade,
)
from Backend.application.services.catalog_import_task_service import (
    CatalogImportTaskService,
)
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
_legacy_catalog_import_task_service: Optional[CatalogImportTaskService] = None
_oop_catalog_import_task_service: Optional[CatalogImportTaskService] = None
file_processing_service = FileProcessingFacade()


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


def _build_catalog_import_task_service(pipeline_variant: str) -> CatalogImportTaskService:
    return CatalogImportTaskService(
        logger=logger,
        catalog_logger=catalog_logger,
        models=models,
        schemas=schemas,
        crud_produtos=crud_produtos,
        file_processing_service=file_processing_service,
        validator_crew=validator_crew,
        settings=settings,
        Path=Path,
        time=time,
        Counter=Counter,
        resolve_storage_path=_resolve_storage_path,
        normalize_import_issue_item=_normalize_import_issue_item,
        extract_import_error_reason=_extract_import_error_reason,
        is_non_critical_import_reason=_is_non_critical_import_reason,
        normalizar_dados_validados=_normalizar_dados_validados,
        sanitize_produto_extraido=_sanitize_produto_extraido,
        classificar_qualidade_linha_produto=_classificar_qualidade_linha_produto,
        write_catalog_import_report=_write_catalog_import_report,
        normalize_import_text=_normalize_import_text,
        pipeline_variant=pipeline_variant,
    )


def _get_legacy_catalog_import_task_service() -> CatalogImportTaskService:
    global _legacy_catalog_import_task_service
    if _legacy_catalog_import_task_service is None:
        _legacy_catalog_import_task_service = _build_catalog_import_task_service(
            pipeline_variant="legacy"
        )
    return _legacy_catalog_import_task_service


def _get_oop_catalog_import_task_service() -> CatalogImportTaskService:
    global _oop_catalog_import_task_service
    if _oop_catalog_import_task_service is None:
        _oop_catalog_import_task_service = _build_catalog_import_task_service(
            pipeline_variant="oop"
        )
    return _oop_catalog_import_task_service

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

    await _get_legacy_catalog_import_task_service().execute(
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
    await _get_oop_catalog_import_task_service().execute(**task_kwargs)







@router.post(

    "/", response_model=schemas.ProdutoResponse, status_code=status.HTTP_201_CREATED

)  # CORRIGIDO AQUI

def create_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto: schemas.ProdutoCreate,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """

    Cria um novo produto para o usu?rio logado.

    """

    # Valida??o do fornecedor, se fornecido

    if produto.fornecedor_id:

        fornecedor = crud_fornecedores.get_fornecedor(

            db, fornecedor_id=produto.fornecedor_id

        )  # Assume que user_id n?o ? necess?rio aqui ou ? validado no get_fornecedor se n?o for admin

        if (

            not fornecedor

        ):  # Adicionar (or (not current_user.is_superuser and fornecedor.user_id != current_user.id)) se necess?rio

            raise HTTPException(

                status_code=404,

                detail=f"Fornecedor com ID {produto.fornecedor_id} n\u00e3o encontrado.",

            )



    # Valida??o do tipo de produto, se fornecido

    if produto.product_type_id:

        product_type = crud_product_types.get_product_type(

            db, product_type_id=produto.product_type_id

        )

        if (

            not product_type

        ):  # Adicionar valida??o de owner se tipos de produto forem espec?ficos do usu?rio

            raise HTTPException(

                status_code=404,

                detail=f"Tipo de Produto com ID {produto.product_type_id} n\u00e3o encontrado.",

            )



    # A fun??o crud_produtos.create_produto (ou create_user_produto) lida com a l?gica de cria??o

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

    skip: int = Query(0, ge=0, description="N?mero de itens para pular"),

    limit: int = Query(

        10, ge=1, le=100, description="N?mero m?ximo de itens por p?gina"

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

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



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

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")

    fornecedor_id_final = fornecedor_id or catalog_file.fornecedor_id
    if not fornecedor_id_final:
        raise HTTPException(
            status_code=400,
            detail="fornecedor_id \u00e9 obrigat\u00f3rio para reprocessar este arquivo.",
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



    orchestrator = CatalogImportPipelineOrchestrator(
        legacy_executor=_tarefa_processar_catalogo,
        oop_executor=_oop_tarefa_processar_catalogo,
    )
    command = CatalogImportFinalizeCommand(
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id_final,
        mapping=mapping,
        pages=pages,
        region=region,
    )
    selected_plan = orchestrator.select_finalize_plan(
        db_session_factory=db_session_factory,
        command=command,
    )
    if PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC"):
        await PipelineDispatcher.run_inline(selected_plan)
    else:
        _ = background_tasks  # Mantido por compatibilidade de assinatura da rota.
        PipelineDispatcher.dispatch_threaded(
            selected_plan,
            thread_name_prefix="catalog-import",
        )



    return {"status": "PROCESSING", "file_id": file_id}





@router.get("/{produto_id}", response_model=schemas.ProdutoResponse)  # CORRIGIDO AQUI

def read_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    """

    Obt?m os detalhes de um produto espec?fico.

    """

    db_produto = crud_produtos.get_produto(

        db, produto_id=produto_id

    )  # crud_produtos.get_produto n?o filtra por user_id por padr?o



    if db_produto is None:

        raise HTTPException(status_code=404, detail="Produto não encontrado")



    # Verifica a permiss?o para visualizar

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N?o autorizado a visualizar este produto"

        )

    return db_produto





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

    user_id_filter = None if current_user.is_superuser else current_user.id



    # Usando get_produtos_by_user do crud, que foi ajustado para receber user_id opcional ou is_admin

    produtos_db = crud_produtos.get_produtos_by_user(  # Nome da fun??o no CRUD

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

    total_items = crud_produtos.count_produtos_by_user(  # Nome da fun??o no CRUD

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

def update_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

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

            status_code=403, detail="N?o autorizado a modificar este produto"

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

        ):  # Adicionar (or (not current_user.is_superuser and fornecedor.user_id != current_user.id)) se necess?rio

            raise HTTPException(

                status_code=404,

                detail=f"Fornecedor com ID {produto.fornecedor_id} n\u00e3o encontrado.",

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

                detail=f"Tipo de Produto com ID {produto.product_type_id} n\u00e3o encontrado.",

            )



    # A fun??o crud_produtos.update_produto espera o objeto db_produto

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

def delete_produto(  # Nome da fun??o mantido como no arquivo do usu?rio

    produto_id: int,

    db: Session = Depends(database.get_db),

    current_user: models.User = Depends(auth_utils.get_current_active_user),

):

    db_produto = crud_produtos.get_produto(db, produto_id=produto_id)

    if db_produto is None:

        raise HTTPException(status_code=404, detail="Produto não encontrado")

    if not current_user.is_superuser and db_produto.user_id != current_user.id:

        raise HTTPException(

            status_code=403, detail="N?o autorizado a deletar este produto"

        )



    # A fun??o crud_produtos.delete_produto espera o objeto db_produto

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

    deleted_produtos = []

    not_found_ids = []

    not_authorized_ids = []



    for produto_id_val in produto_ids:  # Ajustado nome da vari?vel

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

        )  # Adiciona o objeto que foi deletado (j? ? um objeto do modelo)



    # Construindo a resposta

    # A convers?o para schemas.ProdutoResponse ? feita automaticamente pelo FastAPI

    # devido ao response_model=List[schemas.ProdutoResponse]



    if not_found_ids or not_authorized_ids:

        error_detail_parts = []

        if not_found_ids:

            error_detail_parts.append(f"Produtos n\u00e3o encontrados: IDs {not_found_ids}.")

        if not_authorized_ids:

            error_detail_parts.append(

                f"N?o autorizado a deletar produtos: IDs {not_authorized_ids}.",

            )



        # Se nenhum produto foi deletado com sucesso e houve erros, levanta uma exce??o.

        # Se alguns foram deletados, retorna os deletados e o cliente pode precisar ser informado das falhas.

        if not deleted_produtos:

            raise HTTPException(

                status_code=status.HTTP_400_BAD_REQUEST,

                detail=" ".join(error_detail_parts),

            )

        # Se alguns foram deletados, a resposta incluir? apenas eles.

        # O frontend pode precisar verificar a diferen?a entre a lista enviada e a recebida.



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

async def upload_produto_image(  # Nome da fun??o mantido como no arquivo do usu?rio

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

            status_code=403, detail="N?o autorizado a modificar este produto"

        )



    try:

        file_path_in_db = await crud_produtos.save_produto_image(db, produto_id, file)

    except ValueError as e:

        raise HTTPException(status_code=400, detail=str(e))

    except IOError as e:  # Captura erro de IO de save_produto_image

        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:

        raise HTTPException(

            status_code=500, detail=f"N?o foi poss?vel salvar a imagem: {str(e)}"

        )



    # Atualiza o campo imagem_principal_url no produto

    # O schema ProdutoUpdate pode n?o ter imagem_principal_url se n?o for edit?vel diretamente

    # mas o modelo tem. O CRUD pode ter uma l?gica para isso.

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

    """Gera preview de um cat?logo enviado e salva o arquivo para posterior processamento."""



    # L? o conte?do para gerar o preview

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

    """Importa um arquivo de cat?logo e cria produtos vinculados ao fornecedor."""

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
    quality_filter_enabled = ext == ".pdf"
    ignored_non_critical: List[Dict[str, Any]] = []
    quarantine_non_critical: List[Dict[str, Any]] = []

    def _append_import_issue(item: Dict[str, Any]) -> None:
        normalized_item = _normalize_import_issue_item(item)
        reason = _extract_import_error_reason(normalized_item)
        if _is_non_critical_import_reason(reason):
            ignored_non_critical.append(normalized_item)
            return
        erros.append(normalized_item)

    def _append_quarantine_issue(item: Dict[str, Any]) -> None:
        normalized_item = _normalize_import_issue_item(item)
        quarantine_non_critical.append(normalized_item)

    for prod in produtos_data:

        if isinstance(prod, dict) and (

            prod.get("motivo_descarte")

            or any(key.startswith("erro_processamento") for key in prod.keys())

        ):

            _append_import_issue(prod)

            continue

        cleaned_prod = _sanitize_produto_extraido(prod)
        quality_eval = (
            _classificar_qualidade_linha_produto(cleaned_prod)
            if quality_filter_enabled
            else {"decision": "accept", "score": 100, "reason": None}
        )
        if quality_eval.get("decision") == "discard":
            _append_import_issue(
                {
                    "motivo_descarte": quality_eval.get("reason"),
                    "linha_original": prod,
                    "linha_sanitizada": cleaned_prod,
                    "qualidade_score": quality_eval.get("score"),
                }
            )
            continue
        if quality_eval.get("decision") == "quarantine":
            _append_quarantine_issue(
                {
                    "motivo_descarte": quality_eval.get("reason"),
                    "linha_original": prod,
                    "linha_sanitizada": cleaned_prod,
                    "qualidade_score": quality_eval.get("score"),
                    "classificacao": "quarentena",
                }
            )
            continue

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

            _append_import_issue(

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

        for err in dup_errors:
            _append_import_issue(err)

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

    all_issues = erros + ignored_non_critical + quarantine_non_critical
    return {

        "produtos_criados": created,

        "produtos_atualizados": updated,

        "erros": all_issues,

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

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



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

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



    if mapping is None:

        fornecedor = crud_fornecedores.get_fornecedor(db, fornecedor_id)

        if fornecedor and fornecedor.default_column_mapping:

            mapping = fornecedor.default_column_mapping



    orchestrator = CatalogImportPipelineOrchestrator(
        legacy_executor=_tarefa_processar_catalogo,
        oop_executor=_oop_tarefa_processar_catalogo,
    )
    command = CatalogImportFinalizeCommand(
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=product_type_id,
        fornecedor_id=fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=region,
    )
    selected_plan = orchestrator.select_finalize_plan(
        db_session_factory=db_session_factory,
        command=command,
    )
    if PipelineDispatcher.should_run_inline_for_tests("CATALOG_IMPORT_TEST_SYNC"):
        await PipelineDispatcher.run_inline(selected_plan)
    else:
        _ = background_tasks  # Mantido por compatibilidade de assinatura da rota.
        PipelineDispatcher.dispatch_threaded(
            selected_plan,
            thread_name_prefix="catalog-import",
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

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")

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

    """Vers?o simplificada do status de importa??o."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")

    if record.status in {"IMPORTED", "DONE"}:
        status = "DONE"
    elif record.status == "PARTIAL":
        status = "PARTIAL"
    elif record.status == "FAILED":
        status = "FAILED"
    else:
        status = "PROCESSING"

    total_pages = record.total_pages or 0
    result_ready = bool(
        record.status in {"IMPORTED", "PARTIAL", "DONE", "FAILED"}
        and record.result_summary
    )
    return {
        "status": status,
        "total_pages": total_pages,
        "pages_total": total_pages,
        "pages_processed": record.pages_processed,
        "result_ready": result_ready,
    }





@router.get(

    "/importar-catalogo-result/{file_id}/",

    response_model=Union[schemas.CatalogImportResult, schemas.CatalogImportResultPending],

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

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")

    terminal_status = record.status in ["IMPORTED", "PARTIAL", "DONE", "FAILED"]
    if not terminal_status or not record.result_summary:
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "ready": False,
                "status": record.status or "PROCESSING",
                "detail": "Resultados ainda n\u00e3o dispon\u00edveis",
            },
        )

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

    """Processa todas as p?ginas de um cat?logo PDF a partir de ``start_page``."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    )

    if not file_path.exists():

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



    content = file_path.read_bytes()

    ext = file_path.suffix.lower()

    if ext != ".pdf":

        raise HTTPException(status_code=400, detail="Formato de arquivo não suportado")



    with pdfplumber.open(io.BytesIO(content)) as pdf:

        total_pages = len(pdf.pages)



    pages = list(range(start_page, total_pages + 1))



    if mapping is None and record.fornecedor_id:

        fornecedor = crud_fornecedores.get_fornecedor(db, record.fornecedor_id)

        if fornecedor and fornecedor.default_column_mapping:

            mapping = fornecedor.default_column_mapping



    from sqlalchemy.orm import sessionmaker



    db_session_factory = sessionmaker(bind=db.get_bind())



    orchestrator = CatalogImportPipelineOrchestrator(
        legacy_executor=_tarefa_processar_catalogo,
        oop_executor=_oop_tarefa_processar_catalogo,
    )
    command = CatalogImportFinalizeCommand(
        file_id=file_id,
        user_id=current_user.id,
        product_type_id=None,
        fornecedor_id=record.fornecedor_id,
        mapping=mapping,
        pages=pages,
        region=None,
    )
    selected_plan = orchestrator.select_finalize_plan(
        db_session_factory=db_session_factory,
        command=command,
    )
    await selected_plan.executor(**selected_plan.task_kwargs)



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
    """Extrai linhas tabulares de uma regi?o selecionada de um PDF para mapeamento."""
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

    def _parse_key_value_rows(raw_text: str) -> List[Dict[str, str]]:
        """Converte texto simples `chave: valor` em linhas estruturadas."""
        rows: List[Dict[str, str]] = []
        current: Dict[str, str] = {}
        aliases = {
            "nome": "nome",
            "nome base": "nome_base",
            "marca": "marca",
            "descricao": "descricao",
            "descrição": "descricao",
            "sku": "sku",
            "ean": "ean",
            "codigo": "sku",
            "código": "sku",
        }

        for line in (raw_text or "").splitlines():
            line = str(line).strip()
            if not line:
                continue
            match = re.match(r"^\s*([^:]{1,60})\s*:\s*(.?)\s*$", line)
            if not match:
                continue
            raw_key = match.group(1).strip().lower()
            value = match.group(2).strip()
            if not value:
                continue

            key = aliases.get(raw_key, raw_key.replace(" ", "_"))
            if key in current and current:
                rows.append(current)
                current = {}
            current[key] = value

        if current:
            rows.append(current)
        return rows

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
                non_empty_values = [str(v).strip() for v in row.values() if str(v).strip()]
                joined = " ".join(non_empty_values)
                # Evita transformar texto solto/ruido em "produto" no preview da regiao.
                if len(non_empty_values) == 1 and not re.search(r"\d", joined):
                    continue
                produto = file_processing_service._processar_linha_padronizada(row, None)
                if produto:
                    produtos.append(produto)

            log.append(
                f"Pagina {page}: extraidas {len(preview_rows)} linhas e {len(preview_headers)} colunas da regiao."
            )
        else:
            text_rows: List[Dict[str, str]] = []
            with pdfplumber.open(file_path) as pdf:
                target_page = pdf.pages[page - 1]
                cropped = target_page.crop(tuple(selected_bbox))
                raw_text = cropped.extract_text() or ""
                text_rows = _parse_key_value_rows(raw_text)

            if text_rows:
                header_order: List[str] = []
                for row in text_rows:
                    for key in row.keys():
                        if key not in header_order:
                            header_order.append(key)
                preview_headers = header_order
                preview_rows = text_rows
                for row in text_rows:
                    produto = file_processing_service._processar_linha_padronizada(row, None)
                    if produto:
                        produtos.append(produto)
                log.append(
                    f"Pagina {page}: extraidas {len(text_rows)} linhas por fallback de texto (chave:valor)."
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

    """Retorna imagem, texto e tabela de uma ?nica p?gina de um PDF."""

    record = (

        db.query(models.CatalogImportFile)

        .filter_by(id=file_id, user_id=current_user.id)

        .first()

    )

    if not record:

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



    file_path = _resolve_storage_path(
        Path(settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
    )

    if not file_path.exists():

        raise HTTPException(status_code=404, detail="Arquivo n\u00e3o encontrado")



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


