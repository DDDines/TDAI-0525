"""Application-layer service for GPT-4o Vision-based PDF catalog extraction."""

from __future__ import annotations

from typing import Any, Dict, List, Optional


class VisionExtractionService:
    """Application-layer facade for extracting catalog products via GPT-4o Vision.

    Delegates to an injected adapter that calls the Vision runtime, keeping
    the application layer independent of the infrastructure implementation.
    """

    def __init__(self, adapter: Any) -> None:
        """Bind the service to the provided vision extraction adapter."""
        self._adapter = adapter

    async def extrair_pagina(
        self,
        *,
        page_image_data_url: str,
        page_text: Optional[str] = None,
        user: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Extract all products from a single PDF page image via GPT-4o Vision.

        Returns a list of product dicts.  Returns an empty list when no
        products are found or when the underlying API call fails.
        """
        return await self._adapter.extrair_pagina_com_gpt4_vision(
            page_image_data_url=page_image_data_url,
            page_text=page_text,
            user=user,
        )

    async def extrair_paginas(
        self,
        *,
        page_images: List[str],
        page_texts: Optional[List[Optional[str]]] = None,
        user: Optional[Any] = None,
    ) -> List[Dict[str, Any]]:
        """Extract products from multiple PDF page images sequentially.

        Combines the results from all pages into a single flat list.
        ``page_texts`` is optional; when provided its length must match
        ``page_images``.
        """
        texts: List[Optional[str]] = page_texts or [None] * len(page_images)
        all_products: List[Dict[str, Any]] = []
        for data_url, text in zip(page_images, texts):
            page_products = await self.extrair_pagina(
                page_image_data_url=data_url,
                page_text=text,
                user=user,
            )
            all_products.extend(page_products)
        return all_products
