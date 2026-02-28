from __future__ import annotations

import io
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException

from Backend.application.services.repository_runtime_support import (
    call_repository_method,
)


class CatalogImportPreviewService:
    """Encapsula preview e extracao auxiliar do fluxo de importacao de catalogos."""

    def __init__(
        self,
        *,
        models: Any,
        settings: Any,
        file_processing_service: Any,
        resolve_storage_path: Any,
        logger: Any,
        pdfplumber_module: Any,
        catalog_file_repository: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        if catalog_file_repository is None:
            catalog_file_repository = legacy_kwargs.pop("catalog_file_repository", None)
        if catalog_file_repository is None:
            from Backend.infrastructure.repositories.catalog_import_file_repository import (
                CatalogImportFileRepository,
            )

            catalog_file_repository = CatalogImportFileRepository

        self._models = models
        self._settings = settings
        self._file_processing_service = file_processing_service
        self._resolve_storage_path = resolve_storage_path
        self._logger = logger
        self._pdfplumber = pdfplumber_module
        self._catalog_file_repository = catalog_file_repository

    async def importar_catalogo_preview(
        self,
        *,
        file: Any,
        fornecedor_id: Optional[int],
        start_page: int,
        page_count: int,
        dpi: int,
        db: Any,
        user_id: int,
    ) -> Dict[str, Any]:
        """Gera preview de catalogo enviado e persiste o arquivo para uso posterior."""
        content = await file.read()
        started_at = time.perf_counter()
        await file.seek(0)

        catalog_record = await self._file_processing_service.save_uploaded_catalog(
            file, fornecedor_id
        )
        catalog_record.user_id = user_id
        call_repository_method(
            self._catalog_file_repository,
            "save_catalog_file",
            db=db,
            catalog_file=catalog_record,
        )

        ext = Path(catalog_record.original_filename).suffix.lower()
        try:
            if ext == ".pdf":
                preview = await self._file_processing_service.preview_arquivo_pdf(
                    content, ext, start_page, page_count, dpi
                )
            else:
                preview_tabular = await self._file_processing_service.gerar_preview(
                    content, ext
                )
                if preview_tabular.get("error"):
                    return {
                        "file_id": catalog_record.id,
                        "num_pages": 0,
                        "table_pages": [],
                        "sample_rows": [],
                        "preview_images": [],
                        "headers": [],
                        "error": preview_tabular.get("error"),
                    }
                preview = {
                    "num_pages": 1,
                    "table_pages": [1],
                    "sample_rows": preview_tabular.get("sample_rows", []),
                    "preview_images": [],
                    "headers": preview_tabular.get("headers", []),
                }

            duration = time.perf_counter() - started_at
            self._logger.info(
                "Preview generation for catalog file %s took %.4f seconds",
                catalog_record.id,
                duration,
            )
            return {
                **preview,
                "error": None,
                "file_id": catalog_record.id,
            }
        except Exception as exc:  # pragma: no cover - defensive path
            return {
                "file_id": catalog_record.id,
                "num_pages": 0,
                "table_pages": [],
                "sample_rows": {},
                "preview_images": [],
                "error": f"Falha ao gerar preview de PDF: {exc}",
            }

    def selecionar_regiao(
        self,
        *,
        file_id: int,
        page: int,
        bbox: List[float],
        bbox_norm: Optional[List[float]],
        db: Any,
        user_id: int,
    ) -> Dict[str, Any]:
        """Extrai linhas tabulares de uma regiao selecionada de um PDF para mapeamento."""
        record = self._get_record_or_404(db=db, file_id=file_id, user_id=user_id)
        file_path = self._build_catalog_path(record)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

        produtos: List[Dict[str, Any]] = []
        log: List[str] = []
        preview_headers: List[str] = []
        preview_rows: List[Dict[str, Any]] = []

        try:
            with self._pdfplumber.open(file_path) as pdf:
                if not (1 <= page <= len(pdf.pages)):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            "Numero de pagina invalido: "
                            f"{page}. PDF tem {len(pdf.pages)} paginas."
                        ),
                    )
                target_page = pdf.pages[page - 1]

                selected_bbox = list(bbox)
                if bbox_norm and len(bbox_norm) == 4:
                    selected_bbox = [
                        float(bbox_norm[0]) * target_page.width,
                        float(bbox_norm[1]) * target_page.height,
                        float(bbox_norm[2]) * target_page.width,
                        float(bbox_norm[3]) * target_page.height,
                    ]

                x0, y0, x1, y1 = map(float, selected_bbox)
                x0 = max(0.0, min(x0, float(target_page.width)))
                y0 = max(0.0, min(y0, float(target_page.height)))
                x1 = max(0.0, min(x1, float(target_page.width)))
                y1 = max(0.0, min(y1, float(target_page.height)))
                if x1 <= x0 or y1 <= y0:
                    raise HTTPException(
                        status_code=400,
                        detail="BBox invalido para a pagina selecionada.",
                    )
                selected_bbox = [x0, y0, x1, y1]

            df_region = self._file_processing_service.extract_data_from_pdf_region(
                str(file_path),
                page,
                selected_bbox,
            )

            if not df_region.empty:
                preview_headers = [str(col) for col in df_region.columns.tolist()]
                preview_rows = [self._normalize_preview_row(row) for row in df_region.to_dict(orient="records")]

                for row in preview_rows:
                    non_empty_values = [str(v).strip() for v in row.values() if str(v).strip()]
                    joined = " ".join(non_empty_values)
                    if len(non_empty_values) == 1 and not re.search(r"\d", joined):
                        continue
                    produto = self._file_processing_service.processar_linha_padronizada(
                        row,
                        None,
                    )
                    if produto:
                        produtos.append(produto)

                log.append(
                    f"Pagina {page}: extraidas {len(preview_rows)} linhas e {len(preview_headers)} colunas da regiao."
                )
            else:
                text_rows = self._extract_text_rows(
                    file_path=file_path,
                    page=page,
                    selected_bbox=selected_bbox,
                )
                if text_rows:
                    header_order: List[str] = []
                    for row in text_rows:
                        for key in row.keys():
                            if key not in header_order:
                                header_order.append(key)
                    preview_headers = header_order
                    preview_rows = text_rows
                    for row in text_rows:
                        produto = self._file_processing_service.processar_linha_padronizada(
                            row,
                            None,
                        )
                        if produto:
                            produtos.append(produto)
                    log.append(
                        f"Pagina {page}: extraidas {len(text_rows)} linhas por fallback de texto (chave:valor)."
                    )
                else:
                    log.append(
                        f"Pagina {page}: nenhuma linha extraida da regiao selecionada."
                    )

            self._logger.info(
                "selecionar_regiao: file_id=%s, page=%s, bbox=%s, bbox_norm=%s, produtos_extraidos=%s",
                file_id,
                page,
                selected_bbox,
                bbox_norm,
                len(produtos),
            )
            self._logger.info(
                "selecionar_regiao: preview_headers=%s",
                preview_headers[:30],
            )
            self._logger.info(
                "selecionar_regiao: preview_rows_sample=%s",
                preview_rows[:3],
            )
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        return {
            "produtos": produtos,
            "log": log,
            "preview_headers": preview_headers,
            "preview_rows": preview_rows[:100],
        }

    async def extrair_pagina_unica(
        self,
        *,
        file_id: int,
        page_number: int,
        db: Any,
        user_id: int,
    ) -> Dict[str, Any]:
        """Retorna imagem/texto/tabela de uma pagina de PDF."""
        record = self._get_record_or_404(db=db, file_id=file_id, user_id=user_id)
        file_path = self._build_catalog_path(record)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")

        content = file_path.read_bytes()
        try:
            return await self._file_processing_service.extrair_pagina_pdf(
                content,
                page_number,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    def _get_record_or_404(self, *, db: Any, file_id: int, user_id: int) -> Any:
        record = call_repository_method(
            self._catalog_file_repository,
            "get_catalog_file_for_user",
            db=db,
            file_id=file_id,
            user_id=user_id,
        )
        if not record:
            raise HTTPException(status_code=404, detail="Arquivo nao encontrado")
        return record

    def _build_catalog_path(self, record: Any) -> Path:
        return self._resolve_storage_path(
            Path(self._settings.UPLOAD_DIRECTORY) / "catalogs" / record.stored_filename
        )

    @staticmethod
    def _normalize_preview_row(row: Dict[str, Any]) -> Dict[str, Any]:
        normalized: Dict[str, Any] = {}
        for key, value in row.items():
            if value is None:
                normalized[str(key)] = None
                continue
            if isinstance(value, float) and str(value) == "nan":
                normalized[str(key)] = None
                continue
            normalized[str(key)] = value
        return normalized

    def _extract_text_rows(
        self,
        *,
        file_path: Path,
        page: int,
        selected_bbox: List[float],
    ) -> List[Dict[str, str]]:
        with self._pdfplumber.open(file_path) as pdf:
            target_page = pdf.pages[page - 1]
            cropped = target_page.crop(tuple(selected_bbox))
            raw_text = cropped.extract_text() or ""
        return self._parse_key_value_rows(raw_text)

    @staticmethod
    def _parse_key_value_rows(raw_text: str) -> List[Dict[str, str]]:
        rows: List[Dict[str, str]] = []
        current: Dict[str, str] = {}
        aliases = {
            "nome": "nome",
            "nome base": "nome_base",
            "marca": "marca",
            "descricao": "descricao",
            "descricao": "descricao",
            "sku": "sku",
            "ean": "ean",
            "codigo": "sku",
            "codigo": "sku",
        }

        for line in (raw_text or "").splitlines():
            line = str(line).strip()
            if not line:
                continue
            match = re.match(r"^\s*([^:]{1,60})\s*:\s*(.+?)\s*$", line)
            if not match:
                continue
            raw_key = match.group(1).strip().lower()
            value = match.group(2).strip()
            if not value:
                continue

            key = aliases.get(raw_key, raw_key.replace(" ", "_"))
            if key in current and current:
                rows.append(current)
                current = {}
            current[key] = value

        if current:
            rows.append(current)
        return rows
