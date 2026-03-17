"""Vision extraction adapter — OOP port adapter for GPT-4o Vision-based PDF extraction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from Backend.infrastructure.runtime_modules.vision_extraction_module import (
    VisionExtractionRuntime,
)


class VisionExtractionServiceAdapter:
    """OOP port adapter backed by GPT-4o Vision for high-fidelity catalog extraction."""

    def __init__(self, runtime: Optional[VisionExtractionRuntime] = None) -> None:
        """Initialize injected dependencies and runtime configuration for Vision Extraction Service Adapter."""
        self._runtime = runtime or VisionExtractionRuntime()

    async def extrair_pagina_com_gpt4_vision(
        self,
        *,
        page_image_data_url: str,
        page_text: Optional[str] = None,
        user: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Extract all products from one PDF page image via GPT-4o Vision."""
        return await self._runtime.extrair_pagina_com_gpt4_vision(
            page_image_data_url=page_image_data_url,
            page_text=page_text,
            user=user,
        )
