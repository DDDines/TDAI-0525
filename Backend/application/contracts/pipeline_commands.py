"""Module pipeline commands.

Contains backend logic related to pipeline commands and documents its role in the OOP architecture.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CatalogImportFinalizeCommand:
    """Represent catalog import finalize command and centralize responsibilities for this module."""
    file_id: int
    user_id: int
    product_type_id: Optional[int]
    fornecedor_id: int
    mapping: Optional[Dict[str, str]]
    pages: Optional[List[int]]
    region: Optional[List[float]]


@dataclass(frozen=True)
class WebEnrichmentStartCommand:
    """Represent web enrichment start command and centralize responsibilities for this module."""
    produto_id: int
    user_id: int
    termos_busca_override: Optional[str]
