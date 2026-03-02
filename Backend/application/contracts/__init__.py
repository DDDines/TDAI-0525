"""Module init.

Contains backend logic related to init and documents its role in the OOP architecture.
"""

from Backend.application.contracts.pipeline_commands import (
    CatalogImportFinalizeCommand,
    WebEnrichmentStartCommand,
)

__all__ = [
    "CatalogImportFinalizeCommand",
    "WebEnrichmentStartCommand",
]
