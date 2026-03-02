"""Module file processing runtime service.

Contains backend logic related to file processing runtime service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from Backend.infrastructure.runtime_modules import file_processing_module


class FileProcessingRuntimeService:
    """Explicit runtime service surface for file processing flows."""

    def __init__(self) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._catalog_storage = None
        self._line_mapping = None
        self._tabular_ingestion = None
        self._tabular_preview = None
        self._pdf_asset = None
        self._pdf_processing = None
        self._pdf_job = None

    def _get_catalog_storage(self):
        """Run get catalog storage in this workflow."""
        if self._catalog_storage is None:
            self._catalog_storage = file_processing_module.CatalogStorageWorkflow()
        return self._catalog_storage

    def _get_line_mapping(self):
        """Run get line mapping in this workflow."""
        if self._line_mapping is None:
            self._line_mapping = file_processing_module.LineMappingWorkflow()
        return self._line_mapping

    def _get_tabular_ingestion(self):
        """Run get tabular ingestion in this workflow."""
        if self._tabular_ingestion is None:
            self._tabular_ingestion = file_processing_module.TabularIngestionWorkflow()
        return self._tabular_ingestion

    def _get_tabular_preview(self):
        """Run get tabular preview in this workflow."""
        if self._tabular_preview is None:
            self._tabular_preview = file_processing_module.TabularPreviewWorkflow()
        return self._tabular_preview

    def _get_pdf_asset(self):
        """Run get pdf asset in this workflow."""
        if self._pdf_asset is None:
            self._pdf_asset = file_processing_module.PdfAssetWorkflow()
        return self._pdf_asset

    def _get_pdf_processing(self):
        """Run get pdf processing in this workflow."""
        if self._pdf_processing is None:
            self._pdf_processing = file_processing_module.PdfProcessingWorkflow()
        return self._pdf_processing

    def _get_pdf_job(self):
        """Run get pdf job in this workflow."""
        if self._pdf_job is None:
            self._pdf_job = file_processing_module.PdfJobWorkflow()
        return self._pdf_job

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ) -> Any:
        """Run save uploaded catalog in this workflow."""
        return await self._get_catalog_storage().save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Delete catalog file for this workflow."""
        return self._get_catalog_storage().delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Return file path by id for this workflow."""
        return self._get_catalog_storage().get_file_path_by_id(db=db, file_id=file_id)

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run processar arquivo excel in this workflow."""
        return await self._get_tabular_ingestion().processar_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            sheet_name=sheet_name,
            product_type_id=product_type_id,
        )

    async def processar_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Run processar arquivo csv in this workflow."""
        return await self._get_tabular_ingestion().processar_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            product_type_id=product_type_id,
        )

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
        return await self._get_pdf_processing().processar_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            usar_llm=usar_llm,
            product_type_id=product_type_id,
            pages=pages,
            region=region,
        )

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Run preview arquivo excel in this workflow."""
        return await self._get_tabular_preview().preview_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Run preview arquivo csv in this workflow."""
        return await self._get_tabular_preview().preview_arquivo_csv(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        """Run preview arquivo pdf in this workflow."""
        return await self._get_pdf_processing().preview_arquivo_pdf(
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
        """Run gerar preview in this workflow."""
        return await self._get_pdf_processing().gerar_preview(
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
        """Run pdf bytes to images in this workflow."""
        return await self._get_pdf_asset().pdf_bytes_to_images(
            conteudo_arquivo=conteudo_arquivo,
            max_pages=max_pages,
            start_page=start_page,
            dpi=dpi,
        )

    def pdf_pages_to_images(
        self,
        db: Session,
        file: UploadFile,
        fornecedor_id: int,
        user_id: int,
        offset: int,
        limit: int,
    ) -> Dict[str, Any]:
        """Run pdf pages to images in this workflow."""
        return self._get_pdf_asset().pdf_pages_to_images(
            db=db,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    async def extrair_pagina_pdf(
        self,
        conteudo_pdf: bytes,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """Run extrair pagina pdf in this workflow."""
        return await self._get_pdf_asset().extrair_pagina_pdf(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Run generate pdf page images in this workflow."""
        return self._get_pdf_asset().generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Extract pdf region image for this workflow."""
        return self._get_pdf_asset().extract_pdf_region_image(
            file_path=file_path,
            page_number=page_number,
            region=region,
            dpi=dpi,
        )

    def parse_annotation_to_dataframe(
        self,
        annotation: object,
        vertical_tolerance: int = 5,
    ) -> pd.DataFrame:
        """Parse annotation to dataframe for this workflow."""
        return self._get_pdf_asset().parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Extract data from pdf region for this workflow."""
        return self._get_pdf_processing().extract_data_from_pdf_region(
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
        return await self._get_pdf_job().process_pdf_job(
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
        return self._get_pdf_job().extract_data_from_single_page(
            file_path=file_path,
            page_number=page_number,
        )

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run processar linha padronizada in this workflow."""
        return self._get_line_mapping().processar_linha_padronizada(
            linha_original=linha_original,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        )
