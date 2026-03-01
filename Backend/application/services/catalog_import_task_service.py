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
from Backend.application.services.repository_runtime_support import (
    bind_repository,
    call_repository_method,
)


class _CatalogImportTaskRuntime:
    RUNTIME_FIELDS = (
        "logger",
        "catalog_logger",
        "models",
        "schemas",
        "product_repository",
        "catalog_file_repository",
        "file_processing_service",
        "validator_crew",
        "settings",
        "Path",
        "time",
        "Counter",
        "resolve_storage_path",
        "normalize_import_issue_item",
        "extract_import_error_reason",
        "is_non_critical_import_reason",
        "normalizar_dados_validados",
        "sanitize_produto_extraido",
        "classificar_qualidade_linha_produto",
        "write_catalog_import_report",
        "normalize_import_text",
    )

    def __init__(
        self,
        *,
        logger,
        catalog_logger,
        models,
        schemas,
        product_repository,
        catalog_file_repository,
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
    ) -> None:
        self.logger = logger
        self.catalog_logger = catalog_logger
        self.models = models
        self.schemas = schemas
        self.product_repository = product_repository
        self.catalog_file_repository = catalog_file_repository
        self.file_processing_service = file_processing_service
        self.validator_crew = validator_crew
        self.settings = settings
        self.Path = Path
        self.time = time
        self.Counter = Counter
        self.resolve_storage_path = resolve_storage_path
        self.normalize_import_issue_item = normalize_import_issue_item
        self.extract_import_error_reason = extract_import_error_reason
        self.is_non_critical_import_reason = is_non_critical_import_reason
        self.normalizar_dados_validados = normalizar_dados_validados
        self.sanitize_produto_extraido = sanitize_produto_extraido
        self.classificar_qualidade_linha_produto = classificar_qualidade_linha_produto
        self.write_catalog_import_report = write_catalog_import_report
        self.normalize_import_text = normalize_import_text

    def apply_overrides(self, runtime: Any) -> "_CatalogImportTaskRuntime":
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self


class _CatalogImportTaskWorkflow:
    """Orquestra importacao de catalogo com pipeline em etapas OO."""

    def __init__(
        self,
        *,
        logger,
        catalog_logger,
        models,
        schemas,
        product_repository=None,
        catalog_file_repository=None,
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
        runtime: Optional[Any] = None,
    ) -> None:
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        runtime_obj = _CatalogImportTaskRuntime(
            logger=logger,
            catalog_logger=catalog_logger,
            models=models,
            schemas=schemas,
            product_repository=product_repository,
            catalog_file_repository=catalog_file_repository,
            file_processing_service=file_processing_service,
            validator_crew=validator_crew,
            settings=settings,
            Path=Path,
            time=time,
            Counter=Counter,
            resolve_storage_path=resolve_storage_path,
            normalize_import_issue_item=normalize_import_issue_item,
            extract_import_error_reason=extract_import_error_reason,
            is_non_critical_import_reason=is_non_critical_import_reason,
            normalizar_dados_validados=normalizar_dados_validados,
            sanitize_produto_extraido=sanitize_produto_extraido,
            classificar_qualidade_linha_produto=classificar_qualidade_linha_produto,
            write_catalog_import_report=write_catalog_import_report,
            normalize_import_text=normalize_import_text,
        )
        if runtime is not None:
            runtime_obj.apply_overrides(runtime)

        self._runtime = runtime_obj
        self.logger = runtime_obj.logger
        self.catalog_logger = runtime_obj.catalog_logger
        self.models = runtime_obj.models
        self.schemas = runtime_obj.schemas
        self.product_repository = runtime_obj.product_repository
        self.catalog_file_repository = runtime_obj.catalog_file_repository
        self.file_processing_service = runtime_obj.file_processing_service
        self.validator_crew = runtime_obj.validator_crew
        self.settings = runtime_obj.settings
        self.Path = runtime_obj.Path
        self.time = runtime_obj.time
        self.Counter = runtime_obj.Counter

        self.resolve_storage_path = runtime_obj.resolve_storage_path
        self.normalizar_dados_validados = runtime_obj.normalizar_dados_validados
        self.sanitize_produto_extraido = runtime_obj.sanitize_produto_extraido
        self.classificar_qualidade_linha_produto = runtime_obj.classificar_qualidade_linha_produto

        self.file_state_service = CatalogImportFileStateService()
        self.issue_tracker = CatalogImportIssueTracker(
            normalize_import_issue_item=runtime_obj.normalize_import_issue_item,
            extract_import_error_reason=runtime_obj.extract_import_error_reason,
            is_non_critical_import_reason=runtime_obj.is_non_critical_import_reason,
        )
        self.quality_scores = CatalogImportQualityAccumulator()
        self.outcome_resolver = CatalogImportOutcomeResolver()
        self.result_builder = CatalogImportResultBuilder(
            schemas=runtime_obj.schemas,
            normalize_import_text=runtime_obj.normalize_import_text,
            write_catalog_import_report=runtime_obj.write_catalog_import_report,
            outcome_resolver=self.outcome_resolver,
        )
        self.audit_writer = CatalogImportAuditWriter(models=runtime_obj.models)

        self.db: Optional[Session] = None
        self.catalog_file = None
        self.file_id = 0
        self.user_id = 0
        self.product_type_id: Optional[int] = None
        self.fornecedor_id = 0
        self.mapping: Optional[Dict[str, str]] = None
        self.pages: Optional[List[int]] = None
        self.region: Optional[List[float]] = None

        self.created: List[Any] = []
        self.updated: List[Any] = []
        self.ext = ""
        self.quality_filter_enabled = False
        self.catalog_file_repo_runtime: Any | None = None

    def _load_catalog_file(self) -> bool:
        self.catalog_file = call_repository_method(
            self.catalog_file_repo_runtime,
            "get_catalog_file_for_user",
            session=self.db,
            file_id=self.file_id,
            user_id=self.user_id,
        )
        if not self.catalog_file:
            self.logger.error("Catalog file %s not found", self.file_id)
            return False

        self.catalog_logger.info(
            "inicio variant=oop file_id=%s user_id=%s fornecedor_id=%s product_type_id=%s pages=%s region=%s mapping_keys=%s",
            self.file_id,
            self.user_id,
            self.fornecedor_id,
            self.product_type_id,
            self.pages,
            self.region,
            list(self.mapping.keys()) if self.mapping else [],
        )

        self.file_state_service.mark_processing(
            catalog_file_repo=self.catalog_file_repo_runtime,
            catalog_file=self.catalog_file,
            fornecedor_id=self.fornecedor_id,
        )
        return True

    def _resolve_file(self):
        file_path = self.resolve_storage_path(
            self.Path(self.settings.UPLOAD_DIRECTORY)
            / "catalogs"
            / self.catalog_file.stored_filename
        )
        if not file_path.exists():
            self.file_state_service.mark_file_missing(
                catalog_file_repo=self.catalog_file_repo_runtime,
                catalog_file=self.catalog_file,
                file_id=self.file_id,
                stored_filename=self.catalog_file.stored_filename,
            )
            return None, None, None

        content = file_path.read_bytes()
        ext = file_path.suffix.lower()
        self.ext = ext
        self.quality_filter_enabled = ext == ".pdf"
        return file_path, content, ext

    def _build_produto_schema(self, cleaned_prod: Dict[str, Any]):
        return self.schemas.ProdutoCreate(
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
            fornecedor_id=self.catalog_file.fornecedor_id,
            product_type_id=self.product_type_id,
        )

    def _process_quality_and_schema(
        self,
        *,
        prod: Dict[str, Any],
        conversion_error_prefix: str,
        produtos_create: List[Any],
    ) -> None:
        if isinstance(prod, dict) and (
            prod.get("motivo_descarte")
            or any(key.startswith("erro_processamento") for key in prod.keys())
        ):
            self.issue_tracker.add_issue(prod)
            return

        validated_prod = self.normalizar_dados_validados(
            self.validator_crew.run_validation_crew(prod),
            prod,
        )
        cleaned_prod = self.sanitize_produto_extraido(validated_prod)
        quality_eval = (
            self.classificar_qualidade_linha_produto(cleaned_prod)
            if self.quality_filter_enabled
            else {"decision": "accept", "score": 100, "reason": None}
        )

        if quality_eval.get("decision") == "discard":
            self.issue_tracker.add_issue(
                {
                    "motivo_descarte": quality_eval.get("reason"),
                    "linha_original": prod,
                    "linha_validada": validated_prod,
                    "linha_sanitizada": cleaned_prod,
                    "qualidade_score": quality_eval.get("score"),
                }
            )
            return

        if quality_eval.get("decision") == "quarantine":
            self.quality_scores.add_quarantine(quality_eval.get("score"))
            self.issue_tracker.add_quarantine_issue(
                {
                    "motivo_descarte": quality_eval.get("reason"),
                    "linha_original": prod,
                    "linha_validada": validated_prod,
                    "linha_sanitizada": cleaned_prod,
                    "qualidade_score": quality_eval.get("score"),
                    "classificacao": "quarentena",
                }
            )
            return

        self.quality_scores.add_accepted(quality_eval.get("score"))

        try:
            produtos_create.append(self._build_produto_schema(cleaned_prod))
        except Exception as e:
            self.issue_tracker.add_issue(
                {
                    "motivo_descarte": f"{conversion_error_prefix}: {str(e)}",
                    "linha_original": prod,
                    "linha_validada": validated_prod,
                    "linha_sanitizada": cleaned_prod,
                }
            )

    def _flush_produtos(self, *, produtos_create: List[Any]) -> tuple[List[Any], List[Any]]:
        created_page: List[Any] = []
        updated_page: List[Any] = []
        if not produtos_create:
            return created_page, updated_page

        created_page, updated_page, dup_errors = call_repository_method(
            self.product_repository,
            "create_produtos_bulk",
            session=self.db,
            produtos=produtos_create,
            arg_aliases={"produtos": ("produtos_data",)},
            user_id=self.user_id,
        )
        self.created.extend(created_page)
        self.updated.extend(updated_page)
        for err in dup_errors:
            self.issue_tracker.add_issue(err)

        self.audit_writer.register_creation(
            session=self.db,
            user_id=self.user_id,
            produtos_criados=created_page,
        )
        return created_page, updated_page

    async def _process_pdf(self, *, content: bytes) -> None:
        import io
        import pdfplumber

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            total = len(self.pages) if self.pages else len(pdf.pages)

        self.file_state_service.initialize_pages(
            catalog_file_repo=self.catalog_file_repo_runtime,
            catalog_file=self.catalog_file,
            total_pages=total,
        )

        page_list = self.pages or list(range(1, total + 1))
        for page in page_list:
            page_start = self.time.perf_counter()
            produtos_data = await self.file_processing_service.processar_arquivo_pdf(
                content,
                mapeamento_colunas_usuario=self.mapping,
                usar_llm=False,
                product_type_id=self.product_type_id,
                pages=[page],
                region=self.region,
            )

            produtos_create: List[Any] = []
            for prod in produtos_data:
                self._process_quality_and_schema(
                    prod=prod,
                    conversion_error_prefix="Erro ao converter linha",
                    produtos_create=produtos_create,
                )

            created_page, updated_page = self._flush_produtos(produtos_create=produtos_create)
            self.file_state_service.increment_page(
                catalog_file_repo=self.catalog_file_repo_runtime,
                catalog_file=self.catalog_file,
            )
            self.catalog_logger.info(
                "file_id=%s page=%s processed_rows=%s created=%s updated=%s errors_total=%s ignored_total=%s elapsed=%.2fs",
                self.file_id,
                page,
                len(produtos_data),
                len(created_page),
                len(updated_page),
                len(self.issue_tracker.errors),
                len(self.issue_tracker.ignored_non_critical),
                self.time.perf_counter() - page_start,
            )

    async def _process_tabular(self, *, ext: str, content: bytes) -> bool:
        self.file_state_service.initialize_pages(
            catalog_file_repo=self.catalog_file_repo_runtime,
            catalog_file=self.catalog_file,
            total_pages=1,
        )

        if ext in [".xlsx", ".xls"]:
            produtos_data = await self.file_processing_service.processar_arquivo_excel(
                content,
                mapeamento_colunas_usuario=self.mapping,
                product_type_id=self.product_type_id,
            )
        elif ext == ".csv":
            produtos_data = await self.file_processing_service.processar_arquivo_csv(
                content,
                mapeamento_colunas_usuario=self.mapping,
                product_type_id=self.product_type_id,
            )
        else:
            self.file_state_service.mark_final(
                catalog_file_repo=self.catalog_file_repo_runtime,
                catalog_file=self.catalog_file,
                final_status="FAILED",
                result_summary={
                    "created": [],
                    "updated": [],
                    "errors": [
                        {
                            "erro_processamento": f"Formato de arquivo nao suportado: {ext}",
                            "file_id": self.file_id,
                        }
                    ],
                },
            )
            return False

        produtos_create: List[Any] = []
        for prod in produtos_data:
            self._process_quality_and_schema(
                prod=prod,
                conversion_error_prefix="Erro ao converter linha pos-validacao",
                produtos_create=produtos_create,
            )

        self._flush_produtos(produtos_create=produtos_create)
        self.catalog_file.pages_processed = self.catalog_file.total_pages
        self.db.commit()
        return True

    def _finalize_success(self) -> None:
        result_payload = self.result_builder.build(
            file_id=self.file_id,
            created=self.created,
            updated=self.updated,
            issue_tracker=self.issue_tracker,
            quality_scores=self.quality_scores,
            pages_processed=self.catalog_file.pages_processed or 0,
            pages_total=self.catalog_file.total_pages or 0,
            ext=self.ext,
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

        self.file_state_service.mark_final(
            catalog_file_repo=self.catalog_file_repo_runtime,
            catalog_file=self.catalog_file,
            final_status=final_status,
            result_summary=result_summary,
        )
        if final_status == "FAILED":
            first_error = self.issue_tracker.errors[0] if self.issue_tracker.errors else {}
            self.catalog_logger.warning(
                "falha file_id=%s pages=%s/%s first_error=%s",
                self.file_id,
                self.catalog_file.pages_processed,
                self.catalog_file.total_pages,
                str(first_error)[:1000],
            )

        self.catalog_logger.info(
            "fim variant=oop file_id=%s status=%s created=%s updated=%s errors=%s ignored=%s quarantine=%s pages=%s/%s top_reasons=%s top_ignored=%s top_quarantine=%s quality_avg=%s quality_quarantine_avg=%s report=%s",
            self.file_id,
            final_status,
            created_count,
            updated_count,
            errors_count,
            ignored_count,
            quarantine_count,
            self.catalog_file.pages_processed,
            self.catalog_file.total_pages,
            top_reasons,
            top_ignored_reasons,
            top_quarantine_reasons,
            accepted_quality_avg,
            quarantine_quality_avg,
            str(report_path) if report_path else "-",
        )

    def _handle_failure(self, error: Exception) -> None:
        self.logger.exception("Erro ao processar importacao de catalogo")
        self.catalog_logger.exception("falha file_id=%s erro=%s", self.file_id, error)
        if not self.db:
            return
        catalog_file = call_repository_method(
            self.catalog_file_repo_runtime,
            "get_catalog_file",
            session=self.db,
            file_id=self.file_id,
        )
        if catalog_file:
            CatalogImportFileStateService.mark_failure_with_exception(
                catalog_file_repo=self.catalog_file_repo_runtime,
                catalog_file=catalog_file,
                file_id=self.file_id,
                error=error,
            )

    async def run(
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
    ) -> None:
        self.db = db_session_factory()
        self.catalog_file_repo_runtime = bind_repository(
            self.catalog_file_repository,
            session=self.db,
        )
        self.file_id = file_id
        self.user_id = user_id
        self.product_type_id = product_type_id
        self.fornecedor_id = fornecedor_id
        self.mapping = mapping
        self.pages = pages
        self.region = region

        try:
            if not self._load_catalog_file():
                return

            _, content, ext = self._resolve_file()
            if content is None:
                return

            if ext == ".pdf":
                await self._process_pdf(content=content)
            else:
                ok = await self._process_tabular(ext=ext, content=content)
                if not ok:
                    return

            self._finalize_success()
        except Exception as e:
            self._handle_failure(e)
        finally:
            if self.db:
                self.db.close()


CatalogImportTaskWorkflow = _CatalogImportTaskWorkflow


class CatalogImportTaskService:
    """Service OO para executar processamento de importacao de catalogo."""

    def __init__(
        self,
        *,
        logger,
        catalog_logger,
        models,
        schemas,
        product_repository,
        catalog_file_repository=None,
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
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._deps = {
            "logger": logger,
            "catalog_logger": catalog_logger,
            "models": models,
            "schemas": schemas,
            "product_repository": product_repository,
            "catalog_file_repository": catalog_file_repository,
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
        workflow = _CatalogImportTaskWorkflow(**self._deps)
        await workflow.run(
            db_session_factory=db_session_factory,
            file_id=file_id,
            user_id=user_id,
            product_type_id=product_type_id,
            fornecedor_id=fornecedor_id,
            mapping=mapping,
            pages=pages,
            region=region,
        )
