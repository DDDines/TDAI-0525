"""Module init.

Contains backend logic related to init and documents its role in the OOP architecture.
"""

from Backend.application.orchestrators.catalog_import import CatalogImportPipelineOrchestrator
from Backend.application.orchestrators.web_enrichment import WebEnrichmentPipelineOrchestrator

__all__ = [
    "CatalogImportPipelineOrchestrator",
    "WebEnrichmentPipelineOrchestrator",
]
