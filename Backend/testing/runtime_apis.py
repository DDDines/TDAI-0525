from __future__ import annotations

"""Centralized test-only access to runtime internals.

This keeps private/runtime coupling out of individual tests while migration
compatibility is still active.
"""

import Backend.services.file_processing_service as file_processing
import Backend.services.ia_generation_service as ia_service
import Backend.services.limit_service as limit_service
import Backend.services.validator_crew as validator_crew
import Backend.services.web_data_extractor_service as web_extractor

# Direct internal symbols still used by a subset of runtime-focused tests.
_processar_linha_padronizada = file_processing._processar_linha_padronizada
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
    "_processar_linha_padronizada",
    "_CatalogStorageWorkflow",
    "_LineMappingWorkflow",
    "_PdfJobWorkflow",
    "_TabularIngestionWorkflow",
    "_TabularPreviewWorkflow",
    "_WebExtractionEnrichmentWorkflow",
]
