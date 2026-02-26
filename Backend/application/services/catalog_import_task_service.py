from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional
from sqlalchemy.orm import Session


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



        file_path = resolve_storage_path(
            Path(settings.UPLOAD_DIRECTORY) / "catalogs" / catalog_file.stored_filename
        )

        if not file_path.exists():

            catalog_file.status = "FAILED"
            catalog_file.result_summary = {
                "created": [],
                "updated": [],
                "errors": [
                    {
                        "erro_processamento": "Arquivo de catálogo não encontrado no armazenamento.",
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
        quality_filter_enabled = ext == ".pdf"
        ignored_non_critical: List[Dict[str, Any]] = []
        ignored_reason_counter: Counter = Counter()
        ignored_samples: List[Dict[str, Any]] = []
        quarantine_non_critical: List[Dict[str, Any]] = []
        quarantine_reason_counter: Counter = Counter()
        quarantine_samples: List[Dict[str, Any]] = []
        accepted_quality_scores: List[int] = []
        quarantine_quality_scores: List[int] = []

        def _append_import_issue(item: Dict[str, Any]) -> None:
            normalized_item = normalize_import_issue_item(item)
            reason = extract_import_error_reason(normalized_item)
            if is_non_critical_import_reason(reason):
                ignored_non_critical.append(normalized_item)
                ignored_reason_counter[reason] += 1
                if len(ignored_samples) < 30:
                    ignored_samples.append(normalized_item)
                return
            erros.append(normalized_item)

        def _append_quarantine_issue(item: Dict[str, Any]) -> None:
            normalized_item = normalize_import_issue_item(item)
            reason = extract_import_error_reason(normalized_item)
            quarantine_non_critical.append(normalized_item)
            quarantine_reason_counter[reason] += 1
            score_value = normalized_item.get("qualidade_score")
            if isinstance(score_value, (int, float)):
                quarantine_quality_scores.append(int(score_value))
            if len(quarantine_samples) < 30:
                quarantine_samples.append(normalized_item)

        produtos_create: List[schemas.ProdutoCreate] = []

        created: List[models.Produto] = []

        updated: List[models.Produto] = []

        def _registrar_auditoria_criacao(produtos_criados: List[models.Produto]) -> None:
            """Registra uso IA e historico sem commits por item."""
            for db_produto in produtos_criados:
                db.add(
                    models.RegistroUsoIA(
                        user_id=user_id,
                        produto_id=db_produto.id,
                        tipo_acao=models.TipoAcaoEnum.CRIACAO_PRODUTO,
                        creditos_consumidos=0,
                    )
                )
                db.add(
                    models.RegistroHistorico(
                        user_id=user_id,
                        entidade="Produto",
                        acao=models.TipoAcaoSistemaEnum.CRIACAO,
                        entity_id=db_produto.id,
                    )
                )

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

                        _append_import_issue(prod)

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
                        _append_import_issue(
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
                        _append_quarantine_issue(
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
                    accepted_quality_scores.append(int(quality_eval.get("score") or 0))



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

                        _append_import_issue(

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
                        _append_import_issue(err)



                    _registrar_auditoria_criacao(created_page)

                    produtos_create = []

                catalog_file.pages_processed += 1

                db.commit()
                catalog_logger.info(
                    "file_id=%s page=%s processed_rows=%s created=%s updated=%s errors_total=%s ignored_total=%s elapsed=%.2fs",
                    file_id,
                    page,
                    len(produtos_data) if "produtos_data" in locals() else 0,
                    len(created_page),
                    len(updated_page),
                    len(erros),
                    len(ignored_non_critical),
                    time.perf_counter() - page_start,
                )

        else:  # L?gica para outros tipos de arquivo (Excel, CSV)

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

                    _append_import_issue(prod)

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
                    _append_import_issue(
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
                    _append_quarantine_issue(
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
                accepted_quality_scores.append(int(quality_eval.get("score") or 0))

                

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

                    _append_import_issue(

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
                    _append_import_issue(err)



                _registrar_auditoria_criacao(created_page)

                catalog_file.pages_processed = catalog_file.total_pages

            db.commit()



        created_count = len(created)
        updated_count = len(updated)
        errors_count = len(erros)
        ignored_count = len(ignored_non_critical)
        quarantine_count = len(quarantine_non_critical)
        total_success = created_count + updated_count
        has_partial_success = total_success > 0 and errors_count > 0
        final_status = "IMPORTED"
        if total_success == 0 and (errors_count > 0 or ignored_count > 0 or quarantine_count > 0):
            final_status = "FAILED"
        elif has_partial_success:
            final_status = "PARTIAL"

        error_reasons = Counter(
            extract_import_error_reason(err) for err in erros if isinstance(err, dict)
        )
        top_reasons = error_reasons.most_common(10)
        top_ignored_reasons = ignored_reason_counter.most_common(10)
        top_quarantine_reasons = quarantine_reason_counter.most_common(10)
        accepted_quality_avg = (
            round(sum(accepted_quality_scores) / len(accepted_quality_scores), 2)
            if accepted_quality_scores
            else None
        )
        quarantine_quality_avg = (
            round(sum(quarantine_quality_scores) / len(quarantine_quality_scores), 2)
            if quarantine_quality_scores
            else None
        )

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
            "ignored_non_critical": ignored_non_critical,
            "quarantine_non_critical": quarantine_non_critical,
            "stats": {
                "produtos_criados": created_count,
                "produtos_atualizados": updated_count,
                "erros": errors_count,
                "critical_errors": errors_count,
                "descartes_nao_criticos": ignored_count,
                "quarentena_nao_critica": quarantine_count,
                "qualidade_score_medio_aceitas": accepted_quality_avg,
                "qualidade_score_medio_quarentena": quarantine_quality_avg,
                "partial_success": has_partial_success,
                "pages_processed": catalog_file.pages_processed or 0,
                "pages_total": catalog_file.total_pages or 0,
                "ext": ext,
            },
            "log": [
                f"Resumo final: status={final_status}",
                (
                    f"Criados={created_count}, Atualizados={updated_count}, "
                    f"Erros={errors_count}, Descartes n\u00e3o cr\u00edticos={ignored_count}, "
                    f"Quarentena n\u00e3o cr\u00edtica={quarantine_count}"
                ),
            ],
        }
        if top_reasons:
            top_reasons_log = "; ".join(
                [f"{normalize_import_text(reason)} ({count})" for reason, count in top_reasons]
            )
            result_summary["log"].append(f"Top motivos de erro: {top_reasons_log}")
        if top_ignored_reasons:
            top_ignored_log = "; ".join(
                [f"{normalize_import_text(reason)} ({count})" for reason, count in top_ignored_reasons]
            )
            result_summary["log"].append(f"Top descartes n\u00e3o cr\u00edticos: {top_ignored_log}")
        if top_quarantine_reasons:
            top_quarantine_log = "; ".join(
                [f"{normalize_import_text(reason)} ({count})" for reason, count in top_quarantine_reasons]
            )
            result_summary["log"].append(f"Top linhas em quarentena: {top_quarantine_log}")
        if accepted_quality_avg is not None:
            result_summary["log"].append(
                f"Score m\u00e9dio de qualidade (aceitas): {accepted_quality_avg}"
            )
        if quarantine_quality_avg is not None:
            result_summary["log"].append(
                f"Score m\u00e9dio de qualidade (quarentena): {quarantine_quality_avg}"
            )
        if has_partial_success:
            result_summary["log"].append(
                "Importa\u00e7\u00e3o conclu\u00edda com sucesso parcial: produtos foram gravados, mas houve erros cr\u00edticos."
            )

        report_path = write_catalog_import_report(
            file_id=file_id,
            status=final_status,
            created_count=created_count,
            updated_count=updated_count,
            errors=erros,
            ignored_count=ignored_count,
            ignored_reasons=top_ignored_reasons,
            ignored_samples=ignored_samples,
            quarantine_count=quarantine_count,
            quarantine_reasons=top_quarantine_reasons,
            quarantine_samples=quarantine_samples,
            accepted_quality_avg=accepted_quality_avg,
            quarantine_quality_avg=quarantine_quality_avg,
            pages_processed=catalog_file.pages_processed or 0,
            pages_total=catalog_file.total_pages or 0,
            ext=ext,
        )
        if report_path:
            result_summary["log"].append(f"Relat\u00f3rio detalhado: {report_path}")

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
            "fim file_id=%s status=%s created=%s updated=%s errors=%s ignored=%s quarantine=%s pages=%s/%s top_reasons=%s top_ignored=%s top_quarantine=%s quality_avg=%s quality_quarantine_avg=%s report=%s",
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

    except Exception as e:

        logger.exception("Erro ao processar importa\u00e7\u00e3o de cat\u00e1logo")
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
