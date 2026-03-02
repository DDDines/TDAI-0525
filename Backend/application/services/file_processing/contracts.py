"""Contracts.

"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session


class FileProcessingPort(Protocol):
    """Encapsulates File processing port."""
    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ) -> Any:
        """Persist an uploaded supplier catalog and return its metadata."""
        ...

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Delete a previously stored catalog file from storage."""
        ...

    def get_file_path_by_id(
        self,
        db: Session,
        file_id: str | int,
    ) -> str:
        """Resolve the absolute file path for a catalog file identifier."""
        ...

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Extract normalized product rows from an Excel file payload."""
        ...

    async def processar_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Extract normalized product rows from a CSV file payload."""
        ...

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract normalized product rows from a PDF file payload."""
        ...

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Build a tabular preview for an Excel upload."""
        ...

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Build a tabular preview for a CSV upload."""
        ...

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        """Build a visual preview for a PDF upload."""
        ...

    async def gerar_preview(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Dispatch preview generation according to the file extension."""
        ...

    async def pdf_bytes_to_images(
        self,
        conteudo_arquivo: bytes,
        max_pages: int = 1,
        start_page: int = 1,
        dpi: int = 200,
    ) -> List[str]:
        """Convert PDF bytes into page images encoded for API responses."""
        ...

    def pdf_pages_to_images(
        self,
        db: Session,
        file: UploadFile,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Render a page range from an uploaded PDF into image URLs."""
        ...

    async def extrair_pagina_pdf(
        self,
        conteudo_pdf: bytes,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Extract structured rows from one PDF page."""
        ...

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Generate and persist page images for a stored PDF file."""
        ...

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Crop a region from a PDF page and return image bytes."""
        ...

    def parse_annotation_to_dataframe(
        self,
        annotation: object,
        vertical_tolerance: int = 5,
    ) -> pd.DataFrame:
        """Convert OCR/table annotation output into a DataFrame."""
        ...

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Extract tabular data from a specific region of a PDF page."""
        ...

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        """A long-running pdf extraction job."""
        ...

    def extract_data_from_single_page(
        self,
        file_path: str,
        page_number: int,
    ) -> Dict[str, Any]:
        """Extract mapped product data from one page of a stored PDF."""
        ...

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """Normalize one extracted row using the user column mapping."""
        ...
