from __future__ import annotations

"""Centralized test-only access to runtime internals.

This keeps private/runtime coupling out of individual tests while migration
compatibility is still active.
"""

import Backend.infrastructure.runtime_modules.file_processing_module as file_processing
import Backend.infrastructure.runtime_modules.ia_generation_module as ia_service
import Backend.infrastructure.runtime_modules.limit_module as limit_service
import Backend.infrastructure.runtime_modules.validator_crew_module as validator_crew
import Backend.infrastructure.runtime_modules.web_data_extractor_module as web_extractor

# Public symbol preferred by runtime-focused tests.
def processar_linha_padronizada(linha_original, mapeamento_colunas_usuario=None):
    return file_processing.get_line_mapping_workflow().processar_linha_padronizada(
        linha_original=linha_original,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
    )
LineNormalizationRuntime = file_processing.LineNormalizationRuntime
CatalogStorageWorkflow = file_processing.CatalogStorageWorkflow
LineMappingWorkflow = file_processing.LineMappingWorkflow
PdfJobWorkflow = file_processing.PdfJobWorkflow
TabularIngestionWorkflow = file_processing.TabularIngestionWorkflow
TabularPreviewWorkflow = file_processing.TabularPreviewWorkflow
WebExtractionEnrichmentWorkflow = web_extractor.WebExtractionEnrichmentWorkflow

# Transitional aliases for older tests.
_CatalogStorageWorkflow = CatalogStorageWorkflow
_LineMappingWorkflow = LineMappingWorkflow
_PdfJobWorkflow = PdfJobWorkflow
_TabularIngestionWorkflow = TabularIngestionWorkflow
_TabularPreviewWorkflow = TabularPreviewWorkflow
_WebExtractionEnrichmentWorkflow = WebExtractionEnrichmentWorkflow

__all__ = [
    "file_processing",
    "web_extractor",
    "ia_service",
    "limit_service",
    "validator_crew",
    "processar_linha_padronizada",
    "LineNormalizationRuntime",
    "CatalogStorageWorkflow",
    "LineMappingWorkflow",
    "PdfJobWorkflow",
    "TabularIngestionWorkflow",
    "TabularPreviewWorkflow",
    "WebExtractionEnrichmentWorkflow",
    "_CatalogStorageWorkflow",
    "_LineMappingWorkflow",
    "_PdfJobWorkflow",
    "_TabularIngestionWorkflow",
    "_TabularPreviewWorkflow",
    "_WebExtractionEnrichmentWorkflow",
]
