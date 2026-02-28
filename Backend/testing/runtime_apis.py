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
processar_linha_padronizada = file_processing.processar_linha_padronizada
_CatalogStorageWorkflow = file_processing._CatalogStorageWorkflow
_LineMappingWorkflow = file_processing._LineMappingWorkflow
_PdfJobWorkflow = file_processing._PdfJobWorkflow
_TabularIngestionWorkflow = file_processing._TabularIngestionWorkflow
_TabularPreviewWorkflow = file_processing._TabularPreviewWorkflow
_WebExtractionEnrichmentWorkflow = web_extractor._WebExtractionEnrichmentWorkflow

__all__ = [
    "file_processing",
    "web_extractor",
    "ia_service",
    "limit_service",
    "validator_crew",
    "processar_linha_padronizada",
    "_CatalogStorageWorkflow",
    "_LineMappingWorkflow",
    "_PdfJobWorkflow",
    "_TabularIngestionWorkflow",
    "_TabularPreviewWorkflow",
    "_WebExtractionEnrichmentWorkflow",
]
