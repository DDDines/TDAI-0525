"""Module contracts.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session


class FileProcessingPort(Protocol):
    """Class FileProcessingPort.

    Encapsulates one responsibility in the backend architecture.
    """
    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ) -> Any: ...

    def delete_catalog_file(self, stored_filename: str) -> None: ...

    def get_file_path_by_id(
        self,
        db: Session,
        file_id: str | int,
    ) -> str: ...

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]: ...

    async def processar_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]: ...

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]: ...

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]: ...

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]: ...

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]: ...

    async def gerar_preview(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        max_rows: int = 5,
    ) -> Dict[str, Any]: ...

    async def pdf_bytes_to_images(
        self,
        conteudo_arquivo: bytes,
        max_pages: int = 1,
        start_page: int = 1,
        dpi: int = 200,
    ) -> List[str]: ...

    def pdf_pages_to_images(
        self,
        db: Session,
        file: UploadFile,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]: ...

    async def extrair_pagina_pdf(
        self,
        conteudo_pdf: bytes,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> Dict[str, Any]: ...

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]: ...

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes: ...

    def parse_annotation_to_dataframe(
        self,
        annotation: object,
        vertical_tolerance: int = 5,
    ) -> pd.DataFrame: ...

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame: ...

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None: ...

    def extract_data_from_single_page(
        self,
        file_path: str,
        page_number: int,
    ) -> Dict[str, Any]: ...

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]: ...
