"""Document pipeline commands module responsibilities and runtime integration points."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class CatalogImportFinalizeCommand:
    """Represent Catalog Import Finalize Command and centralize its responsibilities inside this module."""
    file_id: int
    user_id: int
    product_type_id: Optional[int]
    fornecedor_id: int
    mapping: Optional[Dict[str, str]]
    pages: Optional[List[int]]
    region: Optional[List[float]]
    extraction_mode: str = "ocr"


@dataclass(frozen=True)
class WebEnrichmentStartCommand:
    """Represent Web Enrichment Start Command and centralize its responsibilities inside this module."""
    produto_id: int
    user_id: int
    termos_busca_override: Optional[str]
