from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session

from Backend.application.services.catalog_import_components import (
    CatalogImportAuditWriter,
    CatalogImportFileStateService,
    CatalogImportIssueTracker,
    CatalogImportOutcomeResolver,
    CatalogImportQualityAccumulator,
    CatalogImportResultBuilder,
)
from Backend.application.services.shadow_result_comparator import ShadowResultComparator


_shadow_result_comparator = ShadowResultComparator()


async def run_catalog_import_task(
    db_session_factory,
    file_id: int,
    user_id: int,
    product_type_id: Optional[int],
    fornecedor_id: int,
    mapping: Optional[Dict[str, str]] = None,
    pages: Optional[List[int]] = None,
    region: Optional[List[float]] = None,
    *,
    logger,
    catalog_logger,
    models,
    schemas,
    crud_produtos,
    file_processing_service,
    validator_crew,
    settings,
    Path,
    time,
    Counter,
    resolve_storage_path: Callable,
    normalize_import_issue_item: Callable,
    extract_import_error_reason: Callable,
    is_non_critical_import_reason: Callable,
    normalizar_dados_validados: Callable,
    sanitize_produto_extraido: Callable,
    classificar_qualidade_linha_produto: Callable,
    write_catalog_import_report: Callable,
    normalize_import_text: Callable,
    pipeline_variant: str = "unknown",
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
        catalog_logger.info(
            "inicio variant=%s file_id=%s user_id=%s fornecedor_id=%s product_type_id=%s pages=%s region=%s mapping_keys=%s",
            pipeline_variant,
            file_id,
            user_id,
            fornecedor_id,
            product_type_id,
            pages,
            region,
            list(mapping.keys()) if mapping else [],
        )

        file_state_service = CatalogImportFileStateService()
        file_state_service.mark_processing(
            db=db,
            catalog_file=catalog_file,
            fornecedor_id=fornecedor_id,
        )



        file_path = resolve_storage_path(
            Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

        if not file_path.exists():

            file_state_service.mark_file_missing(
                db=db,
                catalog_file=catalog_file,
                file_id=file_id,
                stored_filename=catalog_file.stored_filename,
            )

            return

        content = file_path.read_bytes()

        ext = file_path.suffix.lower()

        quality_filter_enabled = ext == ".pdf"
        issue_tracker = CatalogImportIssueTracker(
            normalize_import_issue_item=normalize_import_issue_item,
            extract_import_error_reason=extract_import_error_reason,
            is_non_critical_import_reason=is_non_critical_import_reason,
        )
        quality_scores = CatalogImportQualityAccumulator()
        outcome_resolver = CatalogImportOutcomeResolver()
        result_builder = CatalogImportResultBuilder(
            schemas=schemas,
            normalize_import_text=normalize_import_text,
            write_catalog_import_report=write_catalog_import_report,
            outcome_resolver=outcome_resolver,
        )
        audit_writer = CatalogImportAuditWriter(models=models)

        produtos_create: List[schemas.ProdutoCreate] = []

        created: List[models.Produto] = []

        updated: List[models.Produto] = []

        if ext == ".pdf":

            import pdfplumber, io



            with pdfplumber.open(io.BytesIO(content)) as pdf:

                total = len(pages) if pages else len(pdf.pages)

            file_state_service.initialize_pages(
                db=db,
                catalog_file=catalog_file,
                total_pages=total,
            )

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

                        issue_tracker.add_issue(prod)

                        continue

                    

                    # Executa validação IA com fallback resiliente.
                    validated_prod = normalizar_dados_validados(
                        validator_crew.run_validation_crew(prod),
                        prod,
                    )
                    cleaned_prod = sanitize_produto_extraido(validated_prod)
                    quality_eval = (
                        classificar_qualidade_linha_produto(cleaned_prod)
                        if quality_filter_enabled
                        else {"decision": "accept", "score": 100, "reason": None}
                    )
                    if quality_eval.get("decision") == "discard":
                        issue_tracker.add_issue(
                            {
                                "motivo_descarte": quality_eval.get("reason"),
                                "linha_original": prod,
                                "linha_validada": validated_prod,
                                "linha_sanitizada": cleaned_prod,
                                "qualidade_score": quality_eval.get("score"),
                            }
                        )
                        continue
                    if quality_eval.get("decision") == "quarantine":
                        quality_scores.add_quarantine(quality_eval.get("score"))
                        issue_tracker.add_quarantine_issue(
                            {
                                "motivo_descarte": quality_eval.get("reason"),
                                "linha_original": prod,
                                "linha_validada": validated_prod,
                                "linha_sanitizada": cleaned_prod,
                                "qualidade_score": quality_eval.get("score"),
                                "classificacao": "quarentena",
                            }
                        )
                        continue
                    quality_scores.add_accepted(quality_eval.get("score"))



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

                        issue_tracker.add_issue(

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

                    for err in dup_errors:
                        issue_tracker.add_issue(err)



                    audit_writer.register_creation(
                        db=db,
                        user_id=user_id,
                        produtos_criados=created_page,
                    )

                    produtos_create = []

                file_state_service.increment_page(db=db, catalog_file=catalog_file)
                catalog_logger.info(
                    "file_id=%s page=%s processed_rows=%s created=%s updated=%s errors_total=%s ignored_total=%s elapsed=%.2fs",
                    file_id,
                    page,
                    len(produtos_data) if "produtos_data" in locals() else 0,
                    len(created_page),
                    len(updated_page),
                    len(issue_tracker.errors),
                    len(issue_tracker.ignored_non_critical),
                    time.perf_counter() - page_start,
                )

        else:  # L?gica para outros tipos de arquivo (Excel, CSV)

            file_state_service.initialize_pages(
                db=db,
                catalog_file=catalog_file,
                total_pages=1,
            )

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

                file_state_service.mark_final(
                    db=db,
                    catalog_file=catalog_file,
                    final_status="FAILED",
                    result_summary={
                        "created": [],
                        "updated": [],
                        "errors": [
                            {
                                "erro_processamento": f"Formato de arquivo nao suportado: {ext}",
                                "file_id": file_id,
                            }
                        ],
                    },
                )

                return

            

            created_page: List[models.Produto] = []

            updated_page: List[models.Produto] = []



            for prod in produtos_data:

                if isinstance(prod, dict) and (

                    prod.get("motivo_descarte")

                    or any(key.startswith("erro_processamento") for key in prod.keys())

                ):

                    issue_tracker.add_issue(prod)

                    continue



                # Executa validação IA com fallback resiliente.
                validated_prod = normalizar_dados_validados(
                    validator_crew.run_validation_crew(prod),
                    prod,
                )
                cleaned_prod = sanitize_produto_extraido(validated_prod)
                quality_eval = (
                    classificar_qualidade_linha_produto(cleaned_prod)
                    if quality_filter_enabled
                    else {"decision": "accept", "score": 100, "reason": None}
                )
                if quality_eval.get("decision") == "discard":
                    issue_tracker.add_issue(
                        {
                            "motivo_descarte": quality_eval.get("reason"),
                            "linha_original": prod,
                            "linha_validada": validated_prod,
                            "linha_sanitizada": cleaned_prod,
                            "qualidade_score": quality_eval.get("score"),
                        }
                    )
                    continue
                if quality_eval.get("decision") == "quarantine":
                    quality_scores.add_quarantine(quality_eval.get("score"))
                    issue_tracker.add_quarantine_issue(
                        {
                            "motivo_descarte": quality_eval.get("reason"),
                            "linha_original": prod,
                            "linha_validada": validated_prod,
                            "linha_sanitizada": cleaned_prod,
                            "qualidade_score": quality_eval.get("score"),
                            "classificacao": "quarentena",
                        }
                    )
                    continue
                quality_scores.add_accepted(quality_eval.get("score"))

                

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

                    issue_tracker.add_issue(

                        {

                            "motivo_descarte": f"Erro ao converter linha pós-validação: {str(e)}",

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

                for err in dup_errors:
                    issue_tracker.add_issue(err)



                audit_writer.register_creation(
                    db=db,
                    user_id=user_id,
                    produtos_criados=created_page,
                )

                catalog_file.pages_processed = catalog_file.total_pages

            db.commit()



        result_payload = result_builder.build(
            file_id=file_id,
            created=created,
            updated=updated,
            issue_tracker=issue_tracker,
            quality_scores=quality_scores,
            pages_processed=catalog_file.pages_processed or 0,
            pages_total=catalog_file.total_pages or 0,
            ext=ext,
        )
        final_status = result_payload["final_status"]
        result_summary = result_payload["result_summary"]
        created_count = result_payload["created_count"]
        updated_count = result_payload["updated_count"]
        errors_count = result_payload["errors_count"]
        ignored_count = result_payload["ignored_count"]
        quarantine_count = result_payload["quarantine_count"]
        top_reasons = result_payload["top_reasons"]
        top_ignored_reasons = result_payload["top_ignored_reasons"]
        top_quarantine_reasons = result_payload["top_quarantine_reasons"]
        accepted_quality_avg = result_payload["accepted_quality_avg"]
        quarantine_quality_avg = result_payload["quarantine_quality_avg"]
        report_path = result_payload["report_path"]

        file_state_service.mark_final(
            db=db,
            catalog_file=catalog_file,
            final_status=final_status,
            result_summary=result_summary,
        )
        if final_status == "FAILED":
            first_error = issue_tracker.errors[0] if issue_tracker.errors else {}
            catalog_logger.warning(
                "falha file_id=%s pages=%s/%s first_error=%s",
                file_id,
                catalog_file.pages_processed,
                catalog_file.total_pages,
                str(first_error)[:1000],
            )
        catalog_logger.info(
            "fim variant=%s file_id=%s status=%s created=%s updated=%s errors=%s ignored=%s quarantine=%s pages=%s/%s top_reasons=%s top_ignored=%s top_quarantine=%s quality_avg=%s quality_quarantine_avg=%s report=%s",
            pipeline_variant,
            file_id,
            final_status,
            created_count,
            updated_count,
            errors_count,
            ignored_count,
            quarantine_count,
            catalog_file.pages_processed,
            catalog_file.total_pages,
            top_reasons,
            top_ignored_reasons,
            top_quarantine_reasons,
            accepted_quality_avg,
            quarantine_quality_avg,
            str(report_path) if report_path else "-",
        )
        _shadow_result_comparator.record_result(
            context="catalog_import.finalize",
            entity_id=file_id,
            variant=pipeline_variant,
            payload={
                "status": final_status,
                "created": created_count,
                "updated": updated_count,
                "errors": errors_count,
                "ignored_non_critical": ignored_count,
                "quarantine_non_critical": quarantine_count,
                "pages_processed": catalog_file.pages_processed or 0,
                "pages_total": catalog_file.total_pages or 0,
            },
        )

    except Exception as e:

        logger.exception("Erro ao processar importa\u00e7\u00e3o de cat\u00e1logo")
        catalog_logger.exception("falha file_id=%s erro=%s", file_id, e)

        if db:

            catalog_file = (

                db.query(models.CatalogImportFile).filter_by(id=file_id).first()

            )

            if catalog_file:

                CatalogImportFileStateService.mark_failure_with_exception(
                    db=db,
                    catalog_file=catalog_file,
                    file_id=file_id,
                    error=e,
                )

    finally:

        if db:

            db.close()


class CatalogImportTaskService:
    """Service OO para executar processamento de importacao de catalogo."""

    def __init__(
        self,
        *,
        logger,
        catalog_logger,
        models,
        schemas,
        crud_produtos,
        file_processing_service,
        validator_crew,
        settings,
        Path,
        time,
        Counter,
        resolve_storage_path: Callable,
        normalize_import_issue_item: Callable,
        extract_import_error_reason: Callable,
        is_non_critical_import_reason: Callable,
        normalizar_dados_validados: Callable,
        sanitize_produto_extraido: Callable,
        classificar_qualidade_linha_produto: Callable,
        write_catalog_import_report: Callable,
        normalize_import_text: Callable,
        pipeline_variant: str = "unknown",
    ):
        self._deps = {
            "logger": logger,
            "catalog_logger": catalog_logger,
            "models": models,
            "schemas": schemas,
            "crud_produtos": crud_produtos,
            "file_processing_service": file_processing_service,
            "validator_crew": validator_crew,
            "settings": settings,
            "Path": Path,
            "time": time,
            "Counter": Counter,
            "resolve_storage_path": resolve_storage_path,
            "normalize_import_issue_item": normalize_import_issue_item,
            "extract_import_error_reason": extract_import_error_reason,
            "is_non_critical_import_reason": is_non_critical_import_reason,
            "normalizar_dados_validados": normalizar_dados_validados,
            "sanitize_produto_extraido": sanitize_produto_extraido,
            "classificar_qualidade_linha_produto": classificar_qualidade_linha_produto,
            "write_catalog_import_report": write_catalog_import_report,
            "normalize_import_text": normalize_import_text,
            "pipeline_variant": pipeline_variant,
        }

    async def execute(
        self,
        *,
        db_session_factory,
        file_id: int,
        user_id: int,
        product_type_id: Optional[int],
        fornecedor_id: int,
        mapping: Optional[Dict[str, str]] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ):
        await run_catalog_import_task(
            db_session_factory=db_session_factory,
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
            **self._deps,
        )

