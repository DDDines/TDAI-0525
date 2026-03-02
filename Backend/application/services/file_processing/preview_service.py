"""Module preview service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPreviewService:
    """Preview de conteudo tabular e PDF."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._port = port

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        """Execute preview_arquivo_pdf.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.preview_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
        )

    async def gerar_preview(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute gerar_preview.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.gerar_preview(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            max_rows=max_rows,
        )

    async def pdf_bytes_to_images(
        self,
        conteudo_arquivo: bytes,
        max_pages: int = 1,
        start_page: int = 1,
        dpi: int = 200,
    ) -> List[str]:
        """Execute pdf_bytes_to_images.

        This callable is documented to make behavior explicit for readers.
        """
        return await self._port.pdf_bytes_to_images(
            conteudo_arquivo=conteudo_arquivo,
            max_pages=max_pages,
            start_page=start_page,
            dpi=dpi,
        )

    def pdf_pages_to_images(
        self,
        db,
        file,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Execute pdf_pages_to_images.

        This callable is documented to make behavior explicit for readers.
        """
        return self._port.pdf_pages_to_images(
            db=db,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )
