"""Document orchestrator service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.orm import Session

from Backend.application.services.file_processing.contracts import FileProcessingPort
from Backend.application.services.file_processing.pdf_assets_service import (
    FileProcessingPdfAssetsService,
)
from Backend.application.services.file_processing.pdf_ingestion_service import (
    FileProcessingPdfIngestionService,
)
from Backend.application.services.file_processing.preview_service import (
    FileProcessingPreviewService,
)
from Backend.application.services.file_processing.storage_service import (
    FileProcessingStorageService,
)
from Backend.application.services.file_processing.tabular_ingestion_service import (
    FileProcessingTabularIngestionService,
)


class FileProcessingOrchestratorService:
    """Servico OO unificado para processamento de arquivos de catalogo."""

    def __init__(self, port: FileProcessingPort) -> None:
        """Initialize injected dependencies and runtime configuration for File Processing Orchestrator Service."""
        self._port = port
        self.storage = FileProcessingStorageService(port)
        self.tabular = FileProcessingTabularIngestionService(port)
        self.pdf = FileProcessingPdfIngestionService(port)
        self.preview = FileProcessingPreviewService(port)
        self.pdf_assets = FileProcessingPdfAssetsService(port)

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ):
        """Execute save uploaded catalog as part of this module workflow."""
        return await self.storage.save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete catalog file as part of this module workflow."""
        return self.storage.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Retrieve file path by id using the current service dependencies."""
        return self.storage.get_file_path_by_id(db=db, file_id=file_id)

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel as part of this module workflow."""
        return await self.tabular.processar_arquivo_excel(
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
        """Execute processar arquivo csv as part of this module workflow."""
        return await self.tabular.processar_arquivo_csv(
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
        """Execute processar arquivo pdf as part of this module workflow."""
        return await self.pdf.processar_arquivo_pdf(
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
        """Execute preview arquivo excel as part of this module workflow."""
        return await self.tabular.preview_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute preview arquivo csv as part of this module workflow."""
        return await self.tabular.preview_arquivo_csv(
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
        """Execute preview arquivo pdf as part of this module workflow."""
        return await self.preview.preview_arquivo_pdf(
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
        """Execute gerar preview as part of this module workflow."""
        return await self.preview.gerar_preview(
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
        """Execute pdf bytes to images as part of this module workflow."""
        return await self.preview.pdf_bytes_to_images(
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
        """Execute pdf pages to images as part of this module workflow."""
        return self.preview.pdf_pages_to_images(
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
        """Execute extrair pagina pdf as part of this module workflow."""
        return await self.pdf.extrair_pagina_pdf(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate pdf page images as part of this module workflow."""
        return self.pdf_assets.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Execute extract pdf region image as part of this module workflow."""
        return self.pdf_assets.extract_pdf_region_image(
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
        """Parse annotation to dataframe into structured data used by downstream logic."""
        return self.pdf_assets.parse_annotation_to_dataframe(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )

    def extract_data_from_pdf_region(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
    ) -> pd.DataFrame:
        """Extract data from pdf region."""
        return self.pdf.extract_data_from_pdf_region(
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
        """Execute pdf job and return the normalized execution result."""
        await self.pdf.process_pdf_job(
            job_id=job_id,
            pdf_path=pdf_path,
            start_page=start_page,
            mapping=mapping,
        )

    def extract_data_from_single_page(self, file_path: str, page_number: int) -> Dict[str, Any]:
        """Extract data from single page."""
        return self.pdf.extract_data_from_single_page(file_path=file_path, page_number=page_number)

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
    ) -> Optional[Dict[str, Any]]:
        """Execute processar linha padronizada as part of this module workflow."""
        return self.tabular.processar_linha_padronizada(
            linha_original,
            mapeamento_colunas_usuario,
        )
