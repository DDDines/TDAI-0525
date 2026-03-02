"""Pipeline commands.

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CatalogImportFinalizeCommand:
    """Encapsulates Catalog import finalize command."""
    file_id: int
    user_id: int
    product_type_id: Optional[int]
    fornecedor_id: int
    mapping: Optional[Dict[str, str]]
    pages: Optional[List[int]]
    region: Optional[List[float]]


@dataclass(frozen=True)
class WebEnrichmentStartCommand:
    """Encapsulates Web enrichment start command."""
    produto_id: int
    user_id: int
    termos_busca_override: Optional[str]
