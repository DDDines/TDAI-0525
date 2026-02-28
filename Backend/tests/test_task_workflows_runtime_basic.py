from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from Backend.application.services.catalog_import_task_service import (
    CatalogImportTaskWorkflow,
)
from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskWorkflow,
)


def test_catalog_import_task_workflow_aplica_runtime_override():
    def normalize_issue(item):
        return item

    workflow = CatalogImportTaskWorkflow(
        logger="default_logger",
        catalog_logger="default_catalog_logger",
        models=SimpleNamespace(CatalogImportFile=object),
        schemas=SimpleNamespace(),
        crud_produtos=SimpleNamespace(),
        file_processing_service=SimpleNamespace(),
        validator_crew=SimpleNamespace(),
        settings=SimpleNamespace(UPLOAD_DIRECTORY="uploads"),
        Path=Path,
        time=SimpleNamespace(perf_counter=lambda: 0.0),
        Counter=dict,
        resolve_storage_path=lambda p: p,
        normalize_import_issue_item=normalize_issue,
        extract_import_error_reason=lambda item: "erro",
        is_non_critical_import_reason=lambda reason: False,
        normalizar_dados_validados=lambda validated, original: validated,
        sanitize_produto_extraido=lambda prod: prod,
        classificar_qualidade_linha_produto=lambda prod: {"decision": "accept", "score": 100},
        write_catalog_import_report=lambda **kwargs: None,
        normalize_import_text=lambda text: text,
        runtime=SimpleNamespace(
            logger="runtime_logger",
            resolve_storage_path=lambda p: Path("runtime") / Path(p).name,
        ),
    )

    assert workflow.logger == "runtime_logger"
    assert workflow.resolve_storage_path(Path("abc.txt")) == Path("runtime/abc.txt")


def test_web_enrichment_task_workflow_aplica_runtime_override():
    workflow = WebEnrichmentTaskWorkflow(
        logger="default_logger",
        SQLAlchemyError=Exception,
        crud_users=SimpleNamespace(),
        crud_produtos=SimpleNamespace(),
        crud=SimpleNamespace(),
        models=SimpleNamespace(),
        schemas=SimpleNamespace(),
        web_extractor=SimpleNamespace(),
        settings=SimpleNamespace(),
        json=SimpleNamespace(dumps=lambda *args, **kwargs: "{}"),
        normalize_human_text=lambda text: text,
        build_payload_enriquecimento_visivel=lambda data: data,
        extrair_dominio_fornecedor=lambda site: site,
        priorizar_urls_para_enriquecimento=lambda **kwargs: ([], []),
        is_meaningful_extracted_text=lambda text: bool(text),
        metadata_has_minimum_signal=lambda data: bool(data),
        is_source_relevant_for_product=lambda *args, **kwargs: True,
        runtime=SimpleNamespace(
            logger="runtime_logger",
            is_source_relevant_for_product=lambda *args, **kwargs: False,
        ),
    )

    assert workflow.logger == "runtime_logger"
    assert workflow.is_source_relevant_for_product(None, source_name="", source_desc="", source_url="") is False
