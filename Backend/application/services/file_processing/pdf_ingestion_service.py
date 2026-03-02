"""Module pdf ingestion service.

Contains backend logic related to pdf ingestion service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd

from Backend.application.services.file_processing.contracts import FileProcessingPort


class FileProcessingPdfIngestionService:
    """Ingestao e extracao de PDF."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._port = port

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Run processar arquivo pdf in this workflow."""
        return await self._port.processar_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            usar_llm=usar_llm,
            product_type_id=product_type_id,
            pages=pages,
            region=region,
        )

    async def extrair_pagina_pdf(
        self,
        conteudo_pdf: bytes,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Run extrair pagina pdf in this workflow."""
        return await self._port.extrair_pagina_pdf(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Extract data from pdf region for this workflow."""
        return self._port.extract_data_from_pdf_region(
            file_path=file_path,
            page_number=page_number,
            region=region,
        )

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """Process pdf job for this workflow."""
        return await self._port.process_pdf_job(
            job_id=job_id,
            pdf_path=pdf_path,
            start_page=start_page,
            mapping=mapping,
        )

    def extract_data_from_single_page(
        self,
        file_path: str,
        page_number: int,
    ) -> Dict[str, Any]:
        """Extract data from single page for this workflow."""
        return self._port.extract_data_from_single_page(
            file_path=file_path,
            page_number=page_number,
        )
