"""Init.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from Backend.application.contracts.pipeline_commands import (
    CatalogImportFinalizeCommand,
    WebEnrichmentStartCommand,
)

__all__ = [
    "CatalogImportFinalizeCommand",
    "WebEnrichmentStartCommand",
]
