"""Module init.

Contains backend logic related to init and documents its role in the OOP architecture.
"""

from Backend.application.use_cases.catalog_import_processing import (
    CatalogImportProcessingUseCase,
)
from Backend.application.use_cases.web_enrichment_processing import (
    WebEnrichmentProcessingUseCase,
)

__all__ = [
    "CatalogImportProcessingUseCase",
    "WebEnrichmentProcessingUseCase",
]
