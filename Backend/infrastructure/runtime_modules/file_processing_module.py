"""Document file processing module module responsibilities and runtime integration points."""

import pandas as pd
from pdfplumber import open as pdf_open
import csv
import io
import base64
import os
import re
import tempfile
import unicodedata
import asyncio
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_bytes
import time
from functools import partial
from typing import List, Dict, Any, Union, Optional, Callable
import shutil
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
import uuid
import pdfplumber
from pdfplumber.pdf import PDF as PdfPlumberPDF
from Backend.core.logging_config import get_logger
from Backend.core.config import settings
from Backend import database, models
from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)
from Backend.infrastructure.adapters.web_data_extractor_adapter import WebDataExtractorServiceAdapter
from Backend.infrastructure.repositories.catalog_import_file_repository import (
    CatalogImportFileRepository,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
logger = get_logger(__name__)
try:
    from pdfminer.pdfdocument import PDFPasswordIncorrect
except Exception:
    PDFPasswordIncorrect = None

class _FileProcessingImplementation:
    """Static implementation holder for file processing routines."""

    @staticmethod
    def _is_pdf_password_error(error: Exception) -> bool:
        """Detecta falha de senha em PDF sem depender de excecao especifica do pdfplumber."""
        if error is None:
            return False
        error_type_name = error.__class__.__name__.lower()
        message = str(error).lower()
        if 'password' in error_type_name:
            return True
        if 'password' in message or 'senha' in message:
            return True
        if 'decrypt' in message and 'pdf' in message:
            return True
        if PDFPasswordIncorrect is not None and isinstance(error, PDFPasswordIncorrect):
            return True
        return False

    @staticmethod
    def _resolve_storage_path(path_value: Union[str, Path]) -> Path:
        """Resolve caminhos relativos de storage sem duplicar prefixo Backend."""
        p = Path(path_value)
        if p.is_absolute():
            return p
        module_path = Path(__file__).resolve()
        backend_root = next((parent for parent in module_path.parents if parent.name.lower() == 'backend'), module_path.parents[2])
        project_root = backend_root.parent
        if p.parts and p.parts[0].lower() == 'backend':
            return project_root / p
        return backend_root / p

    @staticmethod
    def _build_file_security_service() -> CatalogImportSanitizationService:
        """Build the file security validator used before expensive parsing operations."""
        return CatalogImportSanitizationService(CatalogImportQualityService())

    @staticmethod
    def _resolve_max_upload_bytes() -> int:
        """Resolve the strict upload byte cap from settings with a safe fallback."""
        try:
            return max(0, int(getattr(settings, "MAX_UPLOAD_BYTES", 25 * 1024 * 1024) or 0))
        except Exception:
            return 25 * 1024 * 1024

    @classmethod
    def _validate_file_payload(
        cls,
        *,
        content: bytes,
        filename: Optional[str]=None,
        extension: Optional[str]=None,
        category: Optional[str]=None,
    ) -> Dict[str, Any]:
        """Validate size and signature before persisting or parsing uploaded content."""
        return cls._build_file_security_service().validate_uploaded_file_payload(
            content=content,
            filename=filename,
            extension=extension,
            category=category,
            max_bytes=cls._resolve_max_upload_bytes(),
        )

    @staticmethod
    def _build_file_security_http_exception(
        error: CatalogImportSanitizationService.FileSecurityValidationError,
    ) -> HTTPException:
        """Translate file validation failures into stable HTTP responses for the UI."""
        status_code = 413 if error.code == 'FILE_TOO_LARGE' else 400
        return HTTPException(
            status_code=status_code,
            detail={"code": error.code, "message": error.detail},
        )

    @staticmethod
    async def _save_uploaded_catalog_impl(file: UploadFile, fornecedor_id: Optional[int]=None) -> models.CatalogImportFile:
        """Salva o arquivo de catÃ¡logo no disco e retorna um objeto CatalogImportFile.
    
    
    
        Parameters
    
        ----------
    
        file: UploadFile
    
            Arquivo recebido na requisiÃ§Ã£o.
    
        fornecedor_id: Optional[int]
    
            Identificador do fornecedor para o qual o catÃ¡logo serÃ¡ importado.
    
        """
        directory = _FileProcessingImplementation._resolve_storage_path(Path(settings.UPLOAD_DIRECTORY) / 'catalogs')
        directory.mkdir(parents=True, exist_ok=True)
        ext = Path(file.filename).suffix
        unique_name = f'{uuid4().hex}{ext}'
        stored_path = directory / unique_name
        content = await file.read()
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=content,
                filename=file.filename,
            )
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            await file.close()
            raise _FileProcessingImplementation._build_file_security_http_exception(error) from error
        with open(stored_path, 'wb') as f_out:
            f_out.write(content)
        await file.close()
        return models.CatalogImportFile(original_filename=file.filename, stored_filename=unique_name, status='UPLOADED', fornecedor_id=fornecedor_id)

    @staticmethod
    def _delete_catalog_file_impl(stored_filename: str) -> None:
        """Remove a stored catalog file from disk if it exists."""
        directory = _FileProcessingImplementation._resolve_storage_path(Path(settings.UPLOAD_DIRECTORY) / 'catalogs')
        path = directory / stored_filename
        try:
            if path.exists():
                path.unlink()
        except Exception:
            logger.exception('Erro ao remover arquivo %s', stored_filename)

    @staticmethod
    def _limpar_valor_extraido(valor: Any) -> Optional[str]:
        """Helper para limpar strings ou converter outros tipos para string, retornando None se vazio."""
        return LineNormalizationRuntime().limpar_valor_extraido(valor)

    @staticmethod
    def _valor_tem_conteudo_util(valor: Any) -> bool:
        """Retorna True para valores Ãºteis (evita lixo de OCR como '!' ou '-')."""
        return LineNormalizationRuntime().valor_tem_conteudo_util(valor)

    @staticmethod
    def _norm_text(v: Any) -> str:
        """Execute norm text as part of this module workflow."""
        return LineNormalizationRuntime().norm_text(v)

    @staticmethod
    def _normalizar_mapeamento_usuario(mapeamento_colunas_usuario: Optional[Dict[str, str]], linha_original: Dict[str, Any]) -> Dict[str, str]:
        """Normaliza mapping do usuario e corrige formato invertido (campo->coluna)."""
        return LineNormalizationRuntime().normalizar_mapeamento_usuario(mapeamento_colunas_usuario=mapeamento_colunas_usuario, linha_original=linha_original)

    @staticmethod
    def _coerce_region_bbox(region: Optional[List[float]], page_width: float, page_height: float) -> tuple[Optional[tuple[float, float, float, float]], Optional[str]]:
        """Converte bbox para coordenada absoluta da pagina e faz clamp seguro."""
        return LineNormalizationRuntime().coerce_region_bbox(region=region, page_width=page_width, page_height=page_height)

    @staticmethod
    def _token_looks_like_code(token: str) -> bool:
        """Heuristica para identificar token de codigo/SKU."""
        return LineNormalizationRuntime().token_looks_like_code(token)

    @staticmethod
    def _split_sku_nome_auto(value: str) -> tuple[Optional[str], Optional[str]]:
        """Divide um texto combinado em SKU e Nome Base quando possivel."""
        return LineNormalizationRuntime().split_sku_nome_auto(value)

    @staticmethod
    def _processar_linha_padronizada(linha_original: Dict[str, Any], mapeamento_colunas_usuario: Optional[Dict[str, str]]=None) -> Optional[Dict[str, Any]]:
        """Padroniza uma linha para campos de Produto, suportando atributos dinamicos."""
        return LineMappingWorkflow().processar_linha_padronizada(linha_original=linha_original, mapeamento_colunas_usuario=mapeamento_colunas_usuario)

    @staticmethod
    async def _processar_arquivo_excel_impl(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, sheet_name: Optional[str]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel impl as part of this module workflow."""
        return await TabularIngestionEngineRuntime().processar_arquivo_excel(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, sheet_name=sheet_name, product_type_id=product_type_id)

    @staticmethod
    async def _processar_arquivo_csv_impl(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo csv impl as part of this module workflow."""
        return await TabularIngestionEngineRuntime().processar_arquivo_csv(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, product_type_id=product_type_id)

    @staticmethod
    async def _processar_arquivo_pdf_impl(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, usar_llm: bool=True, product_type_id: Optional[int]=None, pages: Optional[List[int]]=None, region: Optional[List[float]]=None, extraction_mode: str='ocr') -> List[Dict[str, Any]]:
        """Execute processar arquivo pdf impl as part of this module workflow."""
        return await PdfIngestionRuntime().processar_arquivo_pdf(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, usar_llm=usar_llm, product_type_id=product_type_id, pages=pages, region=region, extraction_mode=extraction_mode)

    @staticmethod
    async def _preview_arquivo_excel_impl(conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo excel impl as part of this module workflow."""
        return await TabularPreviewEngineRuntime().preview_arquivo_excel(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

    @staticmethod
    async def _preview_arquivo_csv_impl(conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo csv impl as part of this module workflow."""
        return await TabularPreviewEngineRuntime().preview_arquivo_csv(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

    @staticmethod
    async def _preview_arquivo_pdf_impl(conteudo_arquivo: bytes, ext: str, start_page: int=1, page_count: int=1, dpi: int=72) -> Dict[str, Any]:
        """Execute preview arquivo pdf impl as part of this module workflow."""
        return await PdfPreviewRuntime().preview_arquivo_pdf(conteudo_arquivo=conteudo_arquivo, ext=ext, start_page=start_page, page_count=page_count, dpi=dpi)

    @staticmethod
    async def _gerar_preview_impl(conteudo_arquivo: bytes, ext: str, max_rows: int=5) -> Dict[str, Any]:
        """Execute gerar preview impl as part of this module workflow."""
        return await PreviewDispatchRuntime().gerar_preview(conteudo_arquivo=conteudo_arquivo, ext=ext, max_rows=max_rows)

    @staticmethod
    async def _pdf_bytes_to_images_impl(conteudo_arquivo: bytes, max_pages: int=1, start_page: int=1, dpi: int=200) -> List[str]:
        """Convert PDF bytes to base64 encoded PNG images."""
        return await PdfImageConversionRuntime().pdf_bytes_to_images(conteudo_arquivo=conteudo_arquivo, max_pages=max_pages, start_page=start_page, dpi=dpi)

    @staticmethod
    def _pdf_pages_to_images_impl(db: Session, file: UploadFile, fornecedor_id: int, user_id: int, offset: int, limit: int) -> Dict[str, Any]:
        """
    
        Salva um ficheiro PDF, cria um registo na base de dados, e converte um lote de pÃ¡ginas em imagens.
    
        """
        upload_dir = _FileProcessingImplementation._resolve_storage_path(Path(settings.UPLOAD_DIRECTORY))
        catalogs_dir = upload_dir / 'catalogs'
        previews_dir = _FileProcessingImplementation._resolve_storage_path(Path(settings.PREVIEW_DIRECTORY))
        catalogs_dir.mkdir(parents=True, exist_ok=True)
        previews_dir.mkdir(parents=True, exist_ok=True)
        poppler_dir = os.getenv('POPPLER_PATH') or settings.POPPLER_PATH
        pdftoppm_path = shutil.which('pdftoppm', path=poppler_dir) if poppler_dir else shutil.which('pdftoppm')
        if pdftoppm_path is None:
            msg = 'Poppler (pdftoppm) executable not found. Install poppler-utils on Linux or set POPPLER_PATH to its directory.'
            logger.error(msg)
            raise HTTPException(status_code=500, detail=msg)
        random_filename = f'{uuid.uuid4().hex}.pdf'
        file_location = catalogs_dir / random_filename
        try:
            content = file.file.read()
        except Exception as e:
            logger.error(f'Erro ao ler o conteÃºdo do ficheiro stream: {e}')
            raise HTTPException(status_code=500, detail='Erro interno ao ler o ficheiro.')
        finally:
            file.file.close()
        try:
            with open(file_location, 'wb') as file_object:
                file_object.write(content)
        except Exception as e:
            logger.error(f'Erro ao salvar o arquivo carregado: {e}')
            raise HTTPException(status_code=500, detail='Erro interno ao salvar o arquivo.')
        import_file = FornecedorRepository(db).create_catalog_import_file(fornecedor_id=fornecedor_id, user_id=user_id, file_name=file.filename, original_file_path=str(file_location))
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                total_pages = len(pdf.pages)
        except Exception as e:
            logger.error(f'Erro ao ler PDF com pdfplumber: {e}')
            raise HTTPException(status_code=500, detail='NÃ£o foi possÃ­vel ler o ficheiro PDF.')
        first_page_to_convert = offset + 1
        last_page_to_convert = min(offset + limit, total_pages)
        image_urls = []
        if first_page_to_convert <= last_page_to_convert:
            try:
                poppler_path = settings.POPPLER_PATH if settings.POPPLER_PATH else None
                images = convert_from_bytes(content, dpi=200, poppler_path=poppler_path, first_page=first_page_to_convert, last_page=last_page_to_convert)
                for i, image in enumerate(images):
                    page_number = offset + i + 1
                    image_filename = f'preview_{import_file.id}_{page_number}.png'
                    image_path = previews_dir / image_filename
                    image.save(image_path, 'PNG')
                    image_url = f'/static/previews/{image_filename}'
                    image_urls.append(image_url)
            except Exception as e:
                logger.error(f'Falha ao converter PDF para imagens: {e}', exc_info=True)
                raise HTTPException(status_code=500, detail='Erro ao processar o PDF. Verifique se o Poppler estÃ¡ instalado corretamente.')
        return {'image_urls': image_urls, 'total_pages': total_pages, 'import_file_id': import_file.id}

    @staticmethod
    def _get_file_path_by_id_impl(db: Session, file_id: str) -> str:
        """Retrieve the stored file path for a catalog import by ID."""
        try:
            resolved_file_id = int(file_id)
        except (TypeError, ValueError):
            return None
        import_file = CatalogImportFileRepository(db).get_catalog_file(file_id=resolved_file_id)
        if not import_file:
            return None
        base_dir = os.path.join('Backend', 'static', 'uploads', 'catalogs')
        return os.path.join(base_dir, import_file.stored_filename)

    @staticmethod
    def _extract_data_from_pdf_region_impl(file_path: str, page_number: int, region: Optional[List[float]]=None, ocr_runtime_state: Optional[Any]=None) -> pd.DataFrame:
        """Extract table-like data from a PDF region with OCR fallback."""
        started_at = time.perf_counter()
        helper = _PdfRegionExtractionUtils
        ocr_state = ocr_runtime_state or OcrRuntimeState()
        try:
            with pdfplumber.open(file_path) as pdf:
                if not 1 <= page_number <= len(pdf.pages):
                    raise ValueError(f'Numero de pagina invalido: {page_number}. PDF tem {len(pdf.pages)} paginas.')
                page = pdf.pages[page_number - 1]
                page_to_process = page
                if region and len(region) == 4:
                    bbox = tuple(map(float, region))
                    page_to_process = page.crop(bbox)
                logger.info('extract_data_from_pdf_region: page=%s region=%s page_size=(%.1f,%.1f)', page_number, region, float(page_to_process.width), float(page_to_process.height))
                table_settings_candidates = [{'vertical_strategy': 'lines', 'horizontal_strategy': 'lines', 'snap_tolerance': 8, 'join_tolerance': 8, 'intersection_tolerance': 8}, {'vertical_strategy': 'lines', 'horizontal_strategy': 'text', 'snap_tolerance': 5}]
                tables: List[List[List[Any]]] = []
                for ts in table_settings_candidates:
                    try:
                        tables = page_to_process.extract_tables(table_settings=ts) or []
                        if tables:
                            break
                    except Exception:
                        continue
                if not tables:
                    try:
                        tables = page_to_process.extract_tables() or []
                    except Exception:
                        tables = []
                df_tables = helper.tables_to_df(tables)
                if not df_tables.empty:
                    logger.info('extract_data_from_pdf_region: table rows=%s cols=%s elapsed=%.2fs', len(df_tables.index), len(df_tables.columns), time.perf_counter() - started_at)
                    return df_tables
                text = page_to_process.extract_text()
                if text:
                    lines = [line for line in text.strip().split('\n') if line.strip()]
                    if len(lines) >= 2:
                        headers = helper.make_unique(lines[0].split())
                        rows_text: List[Dict[str, Any]] = []
                        for line in lines[1:]:
                            parts = line.split()
                            parts_fixed = parts + [''] * (len(headers) - len(parts))
                            parts_fixed = parts_fixed[:len(headers)]
                            rows_text.append({headers[i]: parts_fixed[i] for i in range(len(headers))})
                        df_text = helper.clean_df(pd.DataFrame(rows_text, columns=headers))
                        if not df_text.empty:
                            rows_count = len(df_text.index)
                            cols_count = len(df_text.columns)
                            if rows_count <= 1200 and cols_count <= 25:
                                logger.info('extract_data_from_pdf_region: text rows=%s cols=%s elapsed=%.2fs', rows_count, cols_count, time.perf_counter() - started_at)
                                return df_text
                            logger.info('extract_data_from_pdf_region: text descartado por estrutura suspeita rows=%s cols=%s', rows_count, cols_count)
                if not ocr_state.available or not ocr_state.exec_available:
                    logger.debug('extract_data_from_pdf_region: OCR indisponivel para fallback.')
                    return pd.DataFrame()
                try:
                    ocr_render_start = time.perf_counter()
                    dpi = int(os.getenv('OCR_REGION_DPI', '220'))
                    page_img = page_to_process.to_image(resolution=dpi)
                    buf = io.BytesIO()
                    page_img.original.save(buf, format='PNG')
                    image_cls = ocr_state.image_cls
                    if image_cls is None:
                        logger.debug('extract_data_from_pdf_region: OCR image class indisponivel.')
                        return pd.DataFrame()
                    img = image_cls.open(io.BytesIO(buf.getvalue()))
                    from PIL import ImageEnhance, ImageOps
                    img = img.convert('L')
                    img = ImageOps.autocontrast(img)
                    img = ImageEnhance.Contrast(img).enhance(1.6)
                    logger.info('extract_data_from_pdf_region: OCR render ok dpi=%s elapsed=%.2fs', dpi, time.perf_counter() - ocr_render_start)
                except Exception as e_img:
                    logger.error('Falha ao renderizar regiao para OCR: %s', e_img)
                    return pd.DataFrame()
                try:
                    ocr_start = time.perf_counter()
                    pytesseract_module = ocr_state.pytesseract
                    if pytesseract_module is None:
                        logger.debug('extract_data_from_pdf_region: pytesseract indisponivel.')
                        return pd.DataFrame()
                    ocr_data = pytesseract_module.image_to_data(img, output_type=pytesseract_module.Output.DICT, config='--psm 6 --oem 3')
                    logger.info('extract_data_from_pdf_region: OCR image_to_data concluido em %.2fs', time.perf_counter() - ocr_start)
                except Exception as e_ocr:
                    if not ocr_state.exec_failed_once:
                        logger.error('Falha no OCR da regiao: %s', e_ocr)
                        ocr_state.exec_failed_once = True
                    else:
                        logger.debug('Falha no OCR da regiao (suprimida apos primeira ocorrencia): %s', e_ocr)
                    return pd.DataFrame()
                n = len(ocr_data.get('text', []))
                words: List[Dict[str, Any]] = []
                for i in range(n):
                    txt = (ocr_data.get('text', [''])[i] or '').strip()
                    if not txt:
                        continue
                    conf_raw = ocr_data.get('conf', [''])[i]
                    try:
                        conf = float(conf_raw)
                    except Exception:
                        conf = -1.0
                    if 0 <= conf < 25:
                        continue
                    words.append({'text': txt, 'x': int(ocr_data.get('left', [0])[i] or 0), 'y': int(ocr_data.get('top', [0])[i] or 0), 'w': int(ocr_data.get('width', [0])[i] or 0), 'h': int(ocr_data.get('height', [0])[i] or 0), 'block': int(ocr_data.get('block_num', [0])[i] or 0), 'par': int(ocr_data.get('par_num', [0])[i] or 0), 'line': int(ocr_data.get('line_num', [0])[i] or 0)})
                if not words:
                    logger.info('OCR da regiao retornou vazio.')
                    return pd.DataFrame()
                lines_grouped = helper.group_words_by_line_ids(words)
                if not lines_grouped:
                    lines_grouped = helper.group_words_by_y(words)
                for line_words in lines_grouped:
                    line_words.sort(key=lambda item: item['x'])
                merged_lines: List[List[Dict[str, Any]]] = []
                for line_words in lines_grouped:
                    merged = helper.merge_words_in_line(line_words)
                    if merged:
                        merged_lines.append(merged)
                if not merged_lines:
                    logger.info('OCR da regiao nao produziu segmentos validos.')
                    return pd.DataFrame()
                header_guess = helper.detect_header_columns(merged_lines)
                if header_guess:
                    guessed_headers: List[str] = header_guess['headers']
                    guessed_bounds: List[int] = header_guess['bounds']
                    row_start_idx = int(header_guess['line_idx']) + 1
                    logger.info('extract_data_from_pdf_region: OCR header detectado headers=%s line_idx=%s', guessed_headers, header_guess['line_idx'])
                    raw_rows_guided: List[Dict[str, Any]] = []
                    for line in merged_lines[row_start_idx:]:
                        row = {header: '' for header in guessed_headers}
                        for seg in line:
                            idx_col = min(range(len(guessed_bounds)), key=lambda idx: abs(int(seg['x0']) - guessed_bounds[idx]))
                            key = guessed_headers[idx_col]
                            row[key] = f'{row[key]} {seg['text']}'.strip() if row[key] else seg['text']
                        raw_rows_guided.append(row)
                    filtered_guided = helper.filter_ocr_rows(raw_rows_guided)
                    if filtered_guided:
                        df_ocr_guided = helper.clean_df(pd.DataFrame(filtered_guided, columns=guessed_headers))
                        if not df_ocr_guided.empty:
                            logger.info('extract_data_from_pdf_region: OCR header-guided rows=%s cols=%s elapsed=%.2fs', len(df_ocr_guided.index), len(df_ocr_guided.columns), time.perf_counter() - started_at)
                            return df_ocr_guided
                    logger.info('extract_data_from_pdf_region: OCR header-guided sem linhas validas; fallback para cluster')
                x_positions = sorted((int(seg['x0']) for line in merged_lines for seg in line))
                max_x = max((int(word['x'] + word['w']) for word in words))
                region_px_width = max(1, max_x)
                tol_x = max(24, min(80, int(region_px_width / 35)))
                col_bounds = helper.cluster_positions(x_positions, tol_x)
                max_cols_target = max(8, int(os.getenv('OCR_MAX_COLUMNS', '16')))
                while len(col_bounds) > max_cols_target and tol_x < region_px_width:
                    tol_x = int(tol_x * 1.35)
                    col_bounds = helper.cluster_positions(x_positions, tol_x)
                headers = [f'col_{i}' for i in range(len(col_bounds))] or ['col_0']
                ocr_rows: List[Dict[str, Any]] = []
                for line in merged_lines:
                    row = {header: '' for header in headers}
                    for seg in line:
                        if col_bounds:
                            idx_col = min(range(len(col_bounds)), key=lambda idx: abs(int(seg['x0']) - col_bounds[idx]))
                        else:
                            idx_col = 0
                        key = headers[idx_col]
                        row[key] = f'{row[key]} {seg['text']}'.strip() if row[key] else seg['text']
                    ocr_rows.append(row)
                filtered_rows = helper.filter_ocr_rows(ocr_rows)
                if not filtered_rows:
                    logger.info('OCR da regiao retornou somente ruido.')
                    return pd.DataFrame()
                df_ocr = helper.clean_df(pd.DataFrame(filtered_rows, columns=headers))
                logger.info('extract_data_from_pdf_region: OCR rows=%s cols=%s words=%s lines=%s col_bounds=%s elapsed=%.2fs', len(df_ocr.index), len(df_ocr.columns), len(words), len(merged_lines), len(col_bounds), time.perf_counter() - started_at)
                return df_ocr
        except Exception as e:
            logger.error('Erro ao processar o PDF na extracao da regiao: %s', e)
            return pd.DataFrame()

    @staticmethod
    async def _extrair_pagina_pdf_impl(conteudo_pdf: bytes, page_number: int, region: Optional[List[float]]=None) -> Dict[str, Any]:
        """Return an image, text and optional table extracted from a PDF page."""
        with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:
            if not 1 <= page_number <= len(pdf.pages):
                raise ValueError(f'NÃºmero de pÃ¡gina invÃ¡lido: {page_number}. PDF tem {len(pdf.pages)} pÃ¡ginas.')
            page = pdf.pages[page_number - 1]
            page_to_process = page
            if region and len(region) == 4:
                bbox = tuple(map(float, region))
                page_to_process = page.crop(bbox)
            image = convert_from_bytes(conteudo_pdf, first_page=page_number, last_page=page_number, dpi=200, fmt='png')[0]
            buf = io.BytesIO()
            image.save(buf, format='PNG')
            image_b64 = base64.b64encode(buf.getvalue()).decode()
            text = page_to_process.extract_text() or ''
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
            tmp_file.write(conteudo_pdf)
            tmp_path = Path(tmp_file.name)
        try:
            df = PdfProcessingWorkflow().extract_data_from_pdf_region(file_path=str(tmp_path), page_number=page_number, region=region)
            if not df.empty:
                table = [list(df.columns)] + df.values.tolist()
            else:
                table = None
        finally:
            try:
                tmp_path.unlink()
            except Exception:
                pass
        return {'image': f'data:image/png;base64,{image_b64}', 'text': text, 'table': table}

    @staticmethod
    async def _process_pdf_job_impl(
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
        catalog_file_repository: Optional[CatalogImportFileRepository] = None,
    ) -> None:
        """Remaining pages of a pdf catalog import job."""
        if catalog_file_repository is None:
            raise ValueError("catalog_file_repository is required")
        catalog_file: Optional[models.CatalogImportFile] = None
        try:
            catalog_file = catalog_file_repository.get_catalog_file(file_id=job_id)
            if not catalog_file:
                logger.error('CatalogImportFile %s not found', job_id)
                return
            logger.info('process_pdf_job: start job_id=%s path=%s start_page=%s mapping_keys=%s', job_id, pdf_path, start_page, list(mapping.keys()) if mapping else [])
            with pdfplumber.open(pdf_path) as pdf:
                total_pages = len(pdf.pages)
            catalog_file.status = 'PROCESSING'
            catalog_file.total_pages = total_pages
            catalog_file.pages_processed = 0
            catalog_file_repository.update_catalog_file(catalog_file=catalog_file)
            products: List[Dict[str, Any]] = []
            for page in range(start_page, total_pages + 1):
                try:
                    raw_page = _FileProcessingImplementation._extract_data_from_single_page_impl(pdf_path, page)
                    page_rows = raw_page.get('rows', []) if isinstance(raw_page, dict) else []
                    logger.info('process_pdf_job: page=%s raw_rows_count=%s headers=%s', page, len(page_rows), raw_page.get('headers') if isinstance(raw_page, dict) else None)
                except Exception as e:
                    logger.error('Erro ao extrair dados da pagina %s: %s', page, e)
                    continue
                for row in page_rows:
                    produto = _FileProcessingImplementation._processar_linha_padronizada(row, mapping)
                    if produto:
                        products.append(produto)
                logger.info('process_pdf_job: page=%s products_accumulated=%s', page, len(products))
                catalog_file.pages_processed += 1
                if catalog_file.pages_processed % 5 == 0:
                    catalog_file_repository.update_catalog_file(catalog_file=catalog_file)
            catalog_file.result_summary = {'products': products}
            catalog_file.status = 'PENDING_REVIEW'
            catalog_file_repository.update_catalog_file(catalog_file=catalog_file)
            logger.info('process_pdf_job: done job_id=%s status=%s products=%s pages=%s', job_id, catalog_file.status, len(products), catalog_file.pages_processed)
        except Exception:
            logger.exception('Erro ao processar job de PDF')
            if catalog_file and catalog_file_repository:
                catalog_file.status = 'FAILED'
                catalog_file_repository.update_catalog_file(catalog_file=catalog_file)

    @staticmethod
    def _extract_data_from_single_page_impl(file_path: str, page_number: int) -> Dict[str, Any]:
        """Extract structured data from a single PDF page.
    
    
    
        The function first tries to parse tables and plain text using
    
        :mod:`pdfplumber`. If no data is extracted, the page is rendered
    
        with :mod:`PyMuPDF` and OCR is executed via ``pytesseract``.
    
    
    
        Parameters
    
        ----------
    
        file_path: str
    
            Absolute path to the PDF file on disk.
    
        page_number: int
    
            1-indexed page number to extract.
    
    
    
        Returns
    
        -------
    
        Dict[str, Any]
    
            A dictionary with ``headers`` and ``rows`` keys.
    
        """
        headers: List[str] = []
        rows: List[List[str]] = []
        try:
            with pdfplumber.open(file_path) as pdf:
                if not 1 <= page_number <= len(pdf.pages):
                    raise ValueError(f'NÃºmero de pÃ¡gina invÃ¡lido: {page_number}. PDF tem {len(pdf.pages)} pÃ¡ginas.')
                page = pdf.pages[page_number - 1]
                tables = page.extract_tables(table_settings={'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'})
                if tables:
                    for table in tables:
                        if table and len(table) >= 2:
                            headers = [str(h or '').strip() for h in table[0]]
                            rows = [[str(c or '').strip() for c in r] for r in table[1:]]
                            if any((any((cell for cell in r)) for r in rows)):
                                return {'headers': headers, 'rows': rows}
                text = page.extract_text() or ''
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                if len(lines) >= 2:
                    headers = lines[0].split()
                    rows = [ln.split() for ln in lines[1:]]
                    return {'headers': headers, 'rows': rows}
        except Exception as e:
            logger.error('Erro ao extrair com pdfplumber: %s', e)
        try:
            import fitz
            import pytesseract
            from PIL import Image
            doc = fitz.open(file_path)
            if not 1 <= page_number <= doc.page_count:
                raise ValueError(f'NÃºmero de pÃ¡gina invÃ¡lido: {page_number}. PDF tem {doc.page_count} pÃ¡ginas.')
            page = doc.load_page(page_number - 1)
            pix = page.get_pixmap(dpi=300)
            img = Image.open(io.BytesIO(pix.tobytes()))
            text = pytesseract.image_to_string(img)
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            if lines:
                headers = lines[0].split()
                rows = [ln.split() for ln in lines[1:]]
        except Exception as e:
            logger.error('Erro ao executar OCR da pÃ¡gina do PDF: %s', e)
        finally:
            try:
                doc.close()
            except Exception:
                pass
        return {'headers': headers, 'rows': rows}

    @staticmethod
    def _generate_pdf_page_images_impl(file_path: str, file_id: str) -> List[str]:
        """Generate pdf page images impl."""
        return PdfAssetUtilityRuntime().generate_pdf_page_images(file_path=file_path, file_id=file_id)

    @staticmethod
    def _extract_pdf_region_image_impl(file_path: str, page_number: int, region: Optional[List[float]]=None, dpi: int=300) -> bytes:
        """Extract pdf region image impl."""
        return PdfAssetUtilityRuntime().extract_pdf_region_image(file_path=file_path, page_number=page_number, region=region, dpi=dpi)

    @staticmethod
    def _parse_annotation_to_dataframe_impl(annotation: object, vertical_tolerance: int=5) -> pd.DataFrame:
        """Parse annotation to dataframe impl into structured data used by downstream logic."""
        return PdfAssetUtilityRuntime().parse_annotation_to_dataframe(annotation=annotation, vertical_tolerance=vertical_tolerance)
class OcrRuntimeState:
    """Estado de OCR encapsulado por instancia, sem variaveis globais mutaveis."""

    def __init__(self) -> None:
        """Initialize injected dependencies and runtime configuration for Ocr Runtime State."""
        self.available = False
        self.exec_available = False
        self.exec_failed_once = False
        self.pytesseract = None
        self.image_cls = None
        self._initialize()

    def _initialize(self) -> None:
        """Execute initialize as part of this module workflow."""
        try:
            import pytesseract as pytesseract_module
            from PIL import Image as pil_image_cls

            if shutil.which('tesseract') is None:
                candidate_paths = [
                    'C:\\Program Files\\Tesseract-OCR\\tesseract.exe',
                    'C:\\Program Files (x86)\\Tesseract-OCR\\tesseract.exe',
                ]
                for cpath in candidate_paths:
                    if os.path.exists(cpath):
                        pytesseract_module.pytesseract.tesseract_cmd = cpath
                        logger.info('Tesseract definido para caminho detectado: %s', cpath)
                        break

            pytesseract_module.get_tesseract_version()
            self.pytesseract = pytesseract_module
            self.image_cls = pil_image_cls
            self.available = True
            self.exec_available = True
        except Exception as e:
            self.available = False
            self.exec_available = False
            logger.warning('OCR indisponivel (pytesseract/tesseract): %s. Ajuste PATH/TESSDATA_PREFIX.', e)

class LineNormalizationRuntime:
    """Runtime OO para normalizacao de valores, mapeamento e split SKU/Nome."""

    def limpar_valor_extraido(self, valor: Any) -> Optional[str]:
        """Execute limpar valor extraido as part of this module workflow."""
        if valor is None:
            return None
        try:
            cleaned = str(valor).strip()
            if cleaned.lower() in {'', 'nan', 'none', '#n/a', 'na', '<na>'}:
                return None
            return cleaned
        except Exception:
            return None

    def valor_tem_conteudo_util(self, valor: Any) -> bool:
        """Execute valor tem conteudo util as part of this module workflow."""
        if valor is None:
            return False
        cleaned = str(valor).strip()
        if not cleaned:
            return False
        if len(re.sub('[^0-9A-Za-z\\u00C0-\\u00FF]', '', cleaned)) < 1:
            return False
        return True

    def norm_text(self, value: Any) -> str:
        """Execute norm text as part of this module workflow."""
        return str(value).lower().strip()

    def normalizar_mapeamento_usuario(self, mapeamento_colunas_usuario: Optional[Dict[str, str]], linha_original: Dict[str, Any]) -> Dict[str, str]:
        """Execute normalizar mapeamento usuario as part of this module workflow."""
        if not mapeamento_colunas_usuario:
            return {}
        linha_keys = {self.norm_text(key) for key in linha_original.keys()}
        normalized: Dict[str, str] = {}
        for key, value in mapeamento_colunas_usuario.items():
            if key is None or value is None:
                continue
            key_norm = self.norm_text(key)
            value_raw = str(value).strip()
            if not key_norm or not value_raw:
                continue
            normalized[key_norm] = value_raw
        if not normalized or not linha_keys:
            return normalized
        key_hits = sum((1 for key in normalized.keys() if key in linha_keys))
        value_hits = sum((1 for value in normalized.values() if self.norm_text(value) in linha_keys))
        if value_hits > key_hits:
            inverted: Dict[str, str] = {}
            for destination, source_col in normalized.items():
                source_norm = self.norm_text(source_col)
                inverted[source_norm] = destination
            logger.info('Mapeamento invertido detectado e normalizado: total=%s key_hits=%s value_hits=%s', len(normalized), key_hits, value_hits)
            return inverted
        return normalized

    def coerce_region_bbox(self, region: Optional[List[float]], page_width: float, page_height: float) -> tuple[Optional[tuple[float, float, float, float]], Optional[str]]:
        """Execute coerce region bbox as part of this module workflow."""
        if not region or len(region) != 4:
            return (None, None)
        try:
            x0, y0, x1, y1 = map(float, region)
        except Exception:
            return (None, 'invalid')
        raw_bbox = (x0, y0, x1, y1)
        normalized_mode = max((abs(value) for value in raw_bbox)) <= 2.5
        if normalized_mode:
            x0 = max(0.0, min(x0, 1.0)) * page_width
            y0 = max(0.0, min(y0, 1.0)) * page_height
            x1 = max(0.0, min(x1, 1.0)) * page_width
            y1 = max(0.0, min(y1, 1.0)) * page_height
        else:
            x0 = max(0.0, min(x0, page_width))
            y0 = max(0.0, min(y0, page_height))
            x1 = max(0.0, min(x1, page_width))
            y1 = max(0.0, min(y1, page_height))
        if x1 <= x0 or y1 <= y0:
            return (None, 'invalid_after_clamp')
        return ((x0, y0, x1, y1), 'normalized' if normalized_mode else 'absolute')

    def token_looks_like_code(self, token: str) -> bool:
        """Execute token looks like code as part of this module workflow."""
        value = token.strip().upper()
        if not value or len(value) > 32:
            return False
        if not re.fullmatch('[0-9A-Z./\\-]+', value):
            return False
        digits = sum((1 for ch in value if ch.isdigit()))
        letters = sum((1 for ch in value if ch.isalpha()))
        if digits >= 2:
            return True
        if digits == 1 and letters >= 1 and (len(value) <= 6):
            return True
        if digits == 0 and value in {'D', 'E', 'LD', 'LE', 'RH', 'LH', 'DIR', 'ESQ'}:
            return True
        return False

    def split_sku_nome_auto(self, value: str) -> tuple[Optional[str], Optional[str]]:
        """Execute split sku nome auto as part of this module workflow."""
        tokens = [tok for tok in str(value).split() if tok]
        if not tokens:
            return (None, None)
        sku_tokens: List[str] = []
        nome_tokens: List[str] = []
        for tok in tokens:
            if tok in {'_', '-', '--', '|', 'Â¦'}:
                continue
            has_lower = any((ch.isalpha() and ch.islower() for ch in tok))
            if not nome_tokens:
                if has_lower and sku_tokens:
                    nome_tokens.append(tok)
                    continue
                if self.token_looks_like_code(tok):
                    sku_tokens.append(tok)
                    continue
                if sku_tokens and any((ch.isalpha() for ch in tok)):
                    nome_tokens.append(tok)
                    continue
                nome_tokens.append(tok)
            else:
                nome_tokens.append(tok)
        sku = ' '.join(sku_tokens).strip() or None
        nome = ' '.join(nome_tokens).strip() or None
        if nome:
            nome = re.sub('^[\\W_]+', '', nome).strip() or None
        if not sku and nome:
            return (None, nome)
        if sku and (not nome):
            return (sku, None)
        return (sku, nome)
class LineMappingWorkflow:
    """Workflow OO para padronizacao de linhas extraidas de catalogos."""
    _DEFAULT_MAPPING = {'nome_base': 'nome_base', 'sku_original': 'sku_original', 'ean_original': 'ean_original', 'preco_original': 'preco_original', 'descricao_original': 'descricao_original', 'categoria_original': 'categoria_original', 'imagem_url_original': 'imagem_url_original', 'nome': 'nome_base', 'produto': 'nome_base', 'item': 'nome_base', 'title': 'nome_base', 'titulo': 'nome_base', 'tA-tulo': 'nome_base', 'sku': 'sku_original', 'codigo': 'sku_original', 'ref': 'sku_original', 'referencia': 'sku_original', 'n fab': 'auto:sku_nome', 'n_fab': 'auto:sku_nome', 'no fab': 'auto:sku_nome', 'nfab': 'auto:sku_nome', 'fab': 'auto:sku_nome', 'marca': 'marca', 'fabricante': 'marca', 'brand': 'marca', 'categoria': 'categoria_original', 'category': 'categoria_original', 'descricao': 'descricao_original', 'description': 'descricao_original', 'ean': 'ean_original', 'gtin': 'ean_original', 'upc': 'ean_original', 'preco': 'preco_original', 'price': 'preco_original', 'valor': 'preco_original', 'n original': 'attr:codigo_original', 'n_original': 'attr:codigo_original', 'numero original': 'attr:codigo_original', 'cod original': 'attr:codigo_original', 'codigo original': 'attr:codigo_original', 'original': 'attr:codigo_original', 'aplicacao': 'attr:aplicacao', 'application': 'attr:aplicacao', 'material': 'attr:material', 'url_imagem': 'imagem_url_original', 'imagem': 'imagem_url_original', 'image_url': 'imagem_url_original'}
    _ALIASES_DESTINO = {'sku': 'sku_original', 'ean': 'ean_original', 'preco': 'preco_original', 'price': 'preco_original', 'nome': 'nome_base'}
    _FALLBACK_DYNAMIC_BY_COLUMN = {'aplicacao': 'aplicacao', 'application': 'aplicacao', 'material': 'material', 'n original': 'codigo_original', 'numero original': 'codigo_original', 'codigo original': 'codigo_original', 'original': 'codigo_original'}
    _FALLBACK_SKU_COLUMNS = {'n fab', 'no fab', 'nfab', 'fab'}

    def __init__(self, runtime: Optional['LineMappingRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Line Mapping Workflow."""
        self._runtime = runtime

    def processar_linha_padronizada(self, linha_original: Dict[str, Any], mapeamento_colunas_usuario: Optional[Dict[str, str]]=None) -> Optional[Dict[str, Any]]:
        """Padroniza uma linha para campos de Produto, suportando atributos dinamicos."""
        if self._runtime is not None:
            return self._runtime.processar_linha_padronizada(linha_original=linha_original, mapeamento_colunas_usuario=mapeamento_colunas_usuario)
        produto_dados_padronizados: Dict[str, Any] = {}
        dados_brutos_nao_mapeados: Dict[str, Any] = {}
        dynamic_attributes: Dict[str, Any] = {}
        mapeamento_final = self._DEFAULT_MAPPING.copy()
        mapeamento_usuario_norm = _FileProcessingImplementation._normalizar_mapeamento_usuario(mapeamento_colunas_usuario, linha_original)
        if mapeamento_usuario_norm:
            mapeamento_final.update(mapeamento_usuario_norm)
        for nome_coluna_original, valor_original in linha_original.items():
            valor_limpo = _FileProcessingImplementation._limpar_valor_extraido(valor_original)
            if valor_limpo is None:
                continue
            nome_coluna_norm = str(nome_coluna_original).lower().strip()
            nome_coluna_flat = re.sub('[^a-z0-9]+', ' ', nome_coluna_norm).strip()
            campo_produto_destino = mapeamento_final.get(nome_coluna_norm) or mapeamento_final.get(nome_coluna_flat)
            if campo_produto_destino:
                campo_produto_destino = self._ALIASES_DESTINO.get(str(campo_produto_destino).strip().lower(), campo_produto_destino)
            if campo_produto_destino:
                dest_str = str(campo_produto_destino)
                dest_norm = dest_str.strip().lower()
                if dest_norm in {'auto:sku_nome', 'split:sku_nome', 'sku_nome_auto', 'sku+nome'}:
                    sku_auto, nome_auto = _FileProcessingImplementation._split_sku_nome_auto(valor_limpo)
                    if sku_auto and (not produto_dados_padronizados.get('sku_original')):
                        produto_dados_padronizados['sku_original'] = sku_auto
                    if nome_auto and (not produto_dados_padronizados.get('nome_base')):
                        produto_dados_padronizados['nome_base'] = nome_auto
                    if not nome_auto:
                        dados_brutos_nao_mapeados[f'{nome_coluna_original}_raw'] = valor_limpo
                    continue
                if dest_str.startswith(('attr:', 'dynamic:')):
                    attr_key = dest_str.split(':', 1)[1]
                    if attr_key:
                        dynamic_attributes[attr_key] = valor_limpo
                else:
                    if dest_norm == 'nome_base':
                        sku_auto, nome_auto = _FileProcessingImplementation._split_sku_nome_auto(valor_limpo)
                        if sku_auto and nome_auto:
                            if not produto_dados_padronizados.get('sku_original'):
                                produto_dados_padronizados['sku_original'] = sku_auto
                            if not produto_dados_padronizados.get('nome_base'):
                                produto_dados_padronizados['nome_base'] = nome_auto
                            continue
                    if dest_norm == 'sku_original':
                        sku_auto, nome_auto = _FileProcessingImplementation._split_sku_nome_auto(valor_limpo)
                        if sku_auto:
                            if not produto_dados_padronizados.get('sku_original'):
                                produto_dados_padronizados['sku_original'] = sku_auto
                            if nome_auto and (not produto_dados_padronizados.get('nome_base')):
                                produto_dados_padronizados['nome_base'] = nome_auto
                            continue
                    if dest_norm == 'descricao_original':
                        descricao_existente = _FileProcessingImplementation._limpar_valor_extraido(produto_dados_padronizados.get('descricao_original'))
                        if descricao_existente:
                            partes_existentes = [parte.strip() for parte in str(descricao_existente).split('|') if parte and parte.strip()]
                            if valor_limpo not in partes_existentes:
                                produto_dados_padronizados['descricao_original'] = f'{descricao_existente} | {valor_limpo}'
                        else:
                            produto_dados_padronizados['descricao_original'] = valor_limpo
                        continue
                    if campo_produto_destino not in produto_dados_padronizados:
                        produto_dados_padronizados[campo_produto_destino] = valor_limpo
            else:
                dados_brutos_nao_mapeados[str(nome_coluna_original).strip()] = valor_limpo
        if not produto_dados_padronizados.get('nome_base') and (not produto_dados_padronizados.get('sku_original')):
            if mapeamento_usuario_norm:
                return {'motivo_descarte': 'Faltam nome_base e sku_original', 'linha_original': linha_original}
            if dados_brutos_nao_mapeados:
                primeiro_valor_util = next((v for v in dados_brutos_nao_mapeados.values() if _FileProcessingImplementation._valor_tem_conteudo_util(v)), None)
                if primeiro_valor_util:
                    produto_dados_padronizados['nome_base'] = primeiro_valor_util
                else:
                    return {'motivo_descarte': 'Faltam nome_base e sku_original', 'linha_original': linha_original}
            else:
                return {'motivo_descarte': 'Faltam nome_base e sku_original', 'linha_original': linha_original}
        if produto_dados_padronizados.get('nome_base') and (not _FileProcessingImplementation._valor_tem_conteudo_util(produto_dados_padronizados.get('nome_base'))):
            if not produto_dados_padronizados.get('sku_original'):
                return {'motivo_descarte': 'nome_base sem conteÃºdo Ãºtil', 'linha_original': linha_original}
        if dados_brutos_nao_mapeados:
            produto_dados_padronizados['dados_brutos_adicionais'] = dados_brutos_nao_mapeados
        if dynamic_attributes:
            produto_dados_padronizados['dynamic_attributes'] = dynamic_attributes
        return produto_dados_padronizados

class LineMappingRuntime:
    """Runtime OO para reutilizar a rotina padrÃ£o de mapeamento de linha."""

    def __init__(self, workflow: Optional['LineMappingWorkflow']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Line Mapping Runtime."""
        self._workflow = workflow or LineMappingWorkflow()

    def processar_linha_padronizada(self, linha_original: Dict[str, Any], mapeamento_colunas_usuario: Optional[Dict[str, str]]=None) -> Optional[Dict[str, Any]]:
        """Execute processar linha padronizada as part of this module workflow."""
        return self._workflow.processar_linha_padronizada(linha_original=linha_original, mapeamento_colunas_usuario=mapeamento_colunas_usuario)
class TabularIngestionEngineRuntime:
    """Runtime OO para ingestao de arquivos tabulares (Excel/CSV)."""

    async def processar_arquivo_excel(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, sheet_name: Optional[str]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel as part of this module workflow."""
        produtos_extraidos: List[Dict[str, Any]] = []
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                category='excel',
            )
            xls = pd.ExcelFile(io.BytesIO(conteudo_arquivo))
            abas_processar = [sheet_name] if sheet_name else xls.sheet_names
            for aba in abas_processar:
                df = pd.read_excel(xls, sheet_name=aba)
                df.dropna(how='all', inplace=True)
                for _, linha_pandas in df.iterrows():
                    linha_dict_raw = {col: val if pd.notna(val) else None for col, val in linha_pandas.to_dict().items()}
                    produto_padronizado = _FileProcessingImplementation._processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
                    if produto_padronizado:
                        if product_type_id is not None:
                            produto_padronizado['product_type_id'] = product_type_id
                        produtos_extraidos.append(produto_padronizado)
            return produtos_extraidos
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            return [{'erro_processamento_excel': error.detail, 'error_code': error.code}]
        except Exception as e:
            logger.error('Erro ao processar arquivo Excel: %s', e)
            return [{'erro_processamento_excel': f'Falha ao ler arquivo Excel: {str(e)}'}]

    async def processar_arquivo_csv(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo csv as part of this module workflow."""
        produtos_extraidos: List[Dict[str, Any]] = []
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                category='csv',
            )
            try:
                import chardet
                detection = chardet.detect(conteudo_arquivo)
                encoding_detectada = (detection.get('encoding') or 'utf-8').lower()
            except Exception:
                encoding_detectada = 'utf-8'
            if encoding_detectada.startswith('utf-8'):
                conteudo_str = conteudo_arquivo.decode('utf-8-sig', errors='replace')
            else:
                conteudo_str = conteudo_arquivo.decode(encoding_detectada, errors='replace')
            linhas = conteudo_str.splitlines()
            sample = '\n'.join(linhas[:5]) if linhas else conteudo_str
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
                delimitador_provavel = dialect.delimiter
            except Exception:
                delimitador_provavel = ','
                primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ''
                if ';' in primeira_linha:
                    delimitador_provavel = ';'
                elif '\t' in primeira_linha:
                    delimitador_provavel = '\t'
            leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador_provavel)
            for linha_dict_raw in leitor_csv:
                produto_padronizado = _FileProcessingImplementation._processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
                if produto_padronizado:
                    if product_type_id is not None:
                        produto_padronizado['product_type_id'] = product_type_id
                    produtos_extraidos.append(produto_padronizado)
            return produtos_extraidos
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            return [{'erro_processamento_csv': error.detail, 'error_code': error.code}]
        except Exception as e:
            logger.error('Erro ao processar arquivo CSV: %s', e)
            return [{'erro_processamento_csv': f'Falha ao ler arquivo CSV: {str(e)}'}]

class PdfIngestionRuntime:
    """Runtime OO para ingestao de PDF."""

    def __init__(self, web_data_extractor_service: Optional[Any]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Ingestion Runtime."""
        self._web_data_extractor_service = web_data_extractor_service or WebDataExtractorServiceAdapter()

    @staticmethod
    def _is_discard_payload(produto_padronizado: Any) -> bool:
        """Identify line-mapping discard payloads that must not be imported as products."""
        return isinstance(produto_padronizado, dict) and bool(
            produto_padronizado.get('motivo_descarte')
        )

    @staticmethod
    def _extract_structured_rows_from_text(page_text: str) -> List[Dict[str, Any]]:
        """Parse plain-text PDF content into row-like dictionaries when possible."""
        rows: List[Dict[str, Any]] = []
        if not page_text or not page_text.strip():
            return rows
        lines = [line.strip() for line in page_text.splitlines() if line and line.strip()]
        for line in lines:
            if len(line) < 6:
                continue
            if ':' in line and len(line.split(':', 1)[0]) <= 40:
                # Typical narrative `key: value` metadata line, not catalog row.
                continue
            parts_by_gap = [part.strip() for part in re.split(r'\s{2,}|\t+', line) if part and part.strip()]
            line_tokens = [token for token in re.split(r'\s+', line) if token]
            has_code_hint = any(
                _FileProcessingImplementation._token_looks_like_code(token.upper())
                for token in line_tokens[:8]
            )
            if len(parts_by_gap) >= 2 and has_code_hint:
                rows.append({f'col_{idx}': value for idx, value in enumerate(parts_by_gap)})
                continue
            tokens = [token for token in line_tokens if token]
            if len(tokens) >= 3 and _FileProcessingImplementation._token_looks_like_code(tokens[0]):
                rows.append({'sku_original': tokens[0], 'nome_base': ' '.join(tokens[1:])})
        return rows

    @staticmethod
    def _is_low_confidence_dataframe(df_value: pd.DataFrame) -> bool:
        """Detect low-confidence OCR/text dataframe outputs that are likely narrative noise."""
        if df_value is None or df_value.empty:
            return True
        rows = int(len(df_value.index))
        cols = int(len(df_value.columns))
        values: List[str] = []
        row_signals: List[Dict[str, Any]] = []
        for row in df_value.to_dict(orient='records'):
            row_values: List[str] = []
            for value in row.values():
                cleaned = _FileProcessingImplementation._limpar_valor_extraido(value)
                if cleaned:
                    values.append(cleaned)
                    row_values.append(cleaned)
            if not row_values:
                continue
            row_text = ' '.join(row_values)
            row_tokens = [token for token in re.split(r'\s+', row_text) if token]
            row_compact = re.sub(r'[^0-9A-Za-z]', '', row_text)
            row_signals.append(
                {
                    'alnum_len': len(row_compact),
                    'has_digit': any(ch.isdigit() for ch in row_compact),
                    'has_code_hint': any(
                        _FileProcessingImplementation._token_looks_like_code(token.upper())
                        for token in row_tokens[:8]
                    ),
                    'has_context_word': any(
                        re.search(r'[A-Za-z]{4,}', token)
                        for token in row_tokens
                    ),
                    'token_count': len(row_tokens),
                }
            )
        if not values or not row_signals:
            return True
        joined = ' '.join(values)
        tokens = [token for token in re.split(r'\s+', joined) if token]
        has_digit = any(ch.isdigit() for ch in joined)
        has_code_hint = any(
            _FileProcessingImplementation._token_looks_like_code(token.upper())
            for token in tokens[:12]
        )
        has_context_word = any(re.search(r'[A-Za-z]{4,}', token) for token in tokens)
        strong_rows = sum(
            1
            for signal in row_signals
            if signal['alnum_len'] >= 10
            or signal['has_code_hint']
            or signal['has_context_word']
        )
        if strong_rows == 0:
            return True
        if rows <= 3 and cols <= 2:
            if not has_code_hint and not has_context_word:
                mean_alnum = sum(signal['alnum_len'] for signal in row_signals) / len(row_signals)
                if mean_alnum < 7:
                    return True
        if cols <= 1 and rows <= 3:
            if has_code_hint:
                return False
            if len(tokens) <= 3:
                return True
            if not has_digit and len(tokens) <= 6:
                return True
        return False

    def _append_produto(self, produtos_extraidos: List[Dict[str, Any]], produto_padronizado: Optional[Dict[str, Any]], product_type_id: Optional[int]) -> None:
        """Execute append produto as part of this module workflow."""
        if not produto_padronizado:
            return
        if self._is_discard_payload(produto_padronizado):
            return
        nome_base = _FileProcessingImplementation._limpar_valor_extraido(
            produto_padronizado.get('nome_base')
        )
        sku_original = _FileProcessingImplementation._limpar_valor_extraido(
            produto_padronizado.get('sku_original')
        )
        ean_original = _FileProcessingImplementation._limpar_valor_extraido(
            produto_padronizado.get('ean_original')
        )
        has_identity = bool(nome_base or sku_original or ean_original)
        if not has_identity:
            return
        if not sku_original and not ean_original:
            if self._looks_like_toc_or_page_marker(nome_base):
                return
            if self._is_weak_name_only_identity(nome_base):
                return
        if not sku_original and not ean_original:
            nome_tokens = [token for token in re.split(r'\s+', nome_base or '') if token]
            if (
                len(nome_tokens) < 2
                and not any(ch.isdigit() for ch in (nome_base or ''))
            ):
                return
        if product_type_id is not None:
            produto_padronizado['product_type_id'] = product_type_id
        produtos_extraidos.append(produto_padronizado)

    @staticmethod
    def _looks_like_toc_or_page_marker(nome_base: str) -> bool:
        """Reject table-of-contents/page-index rows misdetected as products."""
        cleaned = _FileProcessingImplementation._limpar_valor_extraido(nome_base)
        if not cleaned:
            return True
        if cleaned.startswith('Conteudo da Pagina '):
            return False
        normalized = unicodedata.normalize('NFKD', cleaned)
        normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = re.sub(r'[^a-zA-Z0-9]+', ' ', normalized).strip().lower()
        if normalized in {'codigo paginas', 'cedigo paginas', 'indice', 'sumario'}:
            return True
        if 'pagina' in normalized and len(normalized.split()) <= 3:
            return True
        return False

    @staticmethod
    def _is_weak_name_only_identity(nome_base: str) -> bool:
        """Reject low-signal identities when nome_base is the only populated field."""
        cleaned = _FileProcessingImplementation._limpar_valor_extraido(nome_base)
        if not cleaned:
            return True
        compact = re.sub(r'[^A-Za-z0-9]', '', cleaned)
        if not compact:
            return True
        if re.fullmatch(r'\d{1,5}', compact):
            return True
        if re.fullmatch(r'[A-Za-z]\d{1,4}', compact):
            return True
        return False

    async def processar_arquivo_pdf(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, usar_llm: bool=True, product_type_id: Optional[int]=None, pages: Optional[List[int]]=None, region: Optional[List[float]]=None, extraction_mode: str='ocr') -> List[Dict[str, Any]]:
        """Execute processar arquivo pdf as part of this module workflow."""
        produtos_extraidos: List[Dict[str, Any]] = []
        log_pdf: List[str] = []
        temp_pdf_path: Optional[Path] = None
        page_list_to_process: List[int] = []
        mode = str(extraction_mode or 'ocr').strip().lower()
        if mode not in {'table', 'ocr', 'ia'}:
            mode = 'ocr'
        allow_ocr_fallback = mode in {'ocr', 'ia'}
        allow_text_fallback = mode in {'ocr', 'ia'}
        allow_llm = bool(usar_llm) and mode == 'ia'
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                category='pdf',
            )
            if region and len(region) == 4:
                with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                    tmp_pdf.write(conteudo_arquivo)
                    temp_pdf_path = Path(tmp_pdf.name)
                logger.info('processar_arquivo_pdf: modo regiao ativo temp_pdf=%s', temp_pdf_path)
            pdf_obj: Optional[PdfPlumberPDF] = None
            try:
                pdf_obj = pdfplumber.open(io.BytesIO(conteudo_arquivo))
            except Exception as open_err:
                if _FileProcessingImplementation._is_pdf_password_error(open_err):
                    log_pdf.append(f'PDF protegido por senha: {str(open_err)}')
                    return [{'erro_processamento_pdf': 'PDF protegido por senha; nao foi possivel abrir sem senha.', 'log_pdf': log_pdf}]
                log_pdf.append(f'Falha ao abrir PDF: {str(open_err)}')
                return [{'erro_processamento_pdf': f'Falha ao abrir PDF: {str(open_err)}', 'log_pdf': log_pdf}]
            if pdf_obj is None:
                log_pdf.append('Falha desconhecida ao abrir o PDF.')
                return [{'erro_processamento_pdf': 'Falha desconhecida ao abrir o PDF.', 'log_pdf': log_pdf}]
            with pdf_obj as pdf:
                total_pages = len(pdf.pages)
                page_list_to_process = list(pages) if pages else list(range(1, total_pages + 1))
                log_pdf.append(f'PDF com {total_pages} paginas.')
                logger.info('processar_arquivo_pdf: total_paginas=%s paginas_processadas=%s region=%s', total_pages, page_list_to_process, region)
                for page_num in page_list_to_process:
                    if not 1 <= page_num <= total_pages:
                        continue
                    page = pdf.pages[page_num - 1]
                    page_to_process = page
                    bbox_abs, bbox_mode = _FileProcessingImplementation._coerce_region_bbox(region, float(page.width), float(page.height))
                    if bbox_abs:
                        page_to_process = page.crop(bbox_abs)
                        log_pdf.append(f'Pagina {page_num}: Aplicando recorte (crop) com bbox {bbox_abs} [modo={bbox_mode}].')
                        logger.info('processar_arquivo_pdf: page=%s bbox=%s mode=%s', page_num, bbox_abs, bbox_mode)
                    elif region:
                        log_pdf.append(f'Pagina {page_num}: BBox invalido ({bbox_mode}); ignorando recorte.')
                    if bbox_abs and temp_pdf_path and allow_ocr_fallback:
                        try:
                            df_region = _FileProcessingImplementation._extract_data_from_pdf_region_impl(
                                file_path=str(temp_pdf_path),
                                page_number=page_num,
                                region=list(bbox_abs),
                            )
                        except Exception as e_region:
                            log_pdf.append(f'Pagina {page_num}: Falha no extrator de regiao: {str(e_region)}')
                            df_region = pd.DataFrame()
                        if not df_region.empty:
                            region_rows = df_region.to_dict(orient='records')
                            log_pdf.append(f'Pagina {page_num}: Extracao por regiao retornou {len(region_rows)} linhas.')
                            logger.info('processar_arquivo_pdf: page=%s region_rows=%s region_cols=%s', page_num, len(region_rows), list(df_region.columns))
                            for row in region_rows:
                                self._append_produto(produtos_extraidos=produtos_extraidos, produto_padronizado=_FileProcessingImplementation._processar_linha_padronizada(row, mapeamento_colunas_usuario), product_type_id=product_type_id)
                            continue
                        log_pdf.append(f'Pagina {page_num}: Extracao por regiao nao retornou linhas.')
                    tables = page_to_process.extract_tables(table_settings={'vertical_strategy': 'lines', 'horizontal_strategy': 'lines'})
                    if tables:
                        log_pdf.append(f'Pagina {page_num}: Encontradas {len(tables)} tabelas.')
                        for table_num, table_data in enumerate(tables):
                            if not table_data or len(table_data) < 2:
                                log_pdf.append(f'Pagina {page_num}, Tabela {table_num + 1}: Tabela vazia ou sem dados.')
                                continue
                            headers_raw = table_data[0]
                            headers = [_FileProcessingImplementation._limpar_valor_extraido(h) or f'coluna_vazia_{idx}' for idx, h in enumerate(headers_raw)]
                            for row_idx, row_data in enumerate(table_data[1:]):
                                if len(row_data) != len(headers):
                                    log_pdf.append(f'Pagina {page_num}, Tabela {table_num + 1}, Linha {row_idx + 1}: Incompatibilidade de colunas. Pulando.')
                                    continue
                                linha_dict_raw = {headers[col_idx]: cell_data for col_idx, cell_data in enumerate(row_data)}
                                self._append_produto(produtos_extraidos=produtos_extraidos, produto_padronizado=_FileProcessingImplementation._processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario), product_type_id=product_type_id)
                    else:
                        log_pdf.append(f'Pagina {page_num}: Nenhuma tabela encontrada.')
                if not produtos_extraidos and page_list_to_process and allow_ocr_fallback:
                    if temp_pdf_path is None:
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                            tmp_pdf.write(conteudo_arquivo)
                            temp_pdf_path = Path(tmp_pdf.name)
                    for page_num in page_list_to_process:
                        if not 1 <= page_num <= total_pages:
                            continue
                        try:
                            df_page_region = _FileProcessingImplementation._extract_data_from_pdf_region_impl(
                                file_path=str(temp_pdf_path),
                                page_number=page_num,
                                region=None,
                            )
                        except Exception as region_fallback_exc:
                            log_pdf.append(
                                f'Pagina {page_num}: Falha no fallback de extracao tabular/ocr: {region_fallback_exc}'
                            )
                            continue
                        if df_page_region.empty:
                            continue
                        if self._is_low_confidence_dataframe(df_page_region):
                            log_pdf.append(
                                f'Pagina {page_num}: fallback tabular/OCR ignorado por baixa confianca.'
                            )
                            continue
                        region_rows = df_page_region.to_dict(orient='records')
                        before_count = len(produtos_extraidos)
                        for row in region_rows:
                            self._append_produto(
                                produtos_extraidos=produtos_extraidos,
                                produto_padronizado=_FileProcessingImplementation._processar_linha_padronizada(
                                    row,
                                    mapeamento_colunas_usuario,
                                ),
                                product_type_id=product_type_id,
                            )
                        if len(produtos_extraidos) > before_count:
                            log_pdf.append(
                                f'Pagina {page_num}: fallback tabular/OCR retornou {len(produtos_extraidos) - before_count} produto(s).'
                            )
                if not produtos_extraidos and page_list_to_process and allow_text_fallback:
                    log_pdf.append('Nenhum produto extraido de tabelas/regiao. Tentando extracao de texto bruto.')
                    for page_num in page_list_to_process:
                        if not 1 <= page_num <= total_pages:
                            continue
                        page = pdf.pages[page_num - 1]
                        page_to_process = page
                        bbox_abs, _ = _FileProcessingImplementation._coerce_region_bbox(region, float(page.width), float(page.height))
                        if bbox_abs:
                            page_to_process = page.crop(bbox_abs)
                        page_text = page_to_process.extract_text(x_tolerance=2, y_tolerance=2)
                        if page_text and page_text.strip():
                            log_pdf.append(f'Pagina {page_num}: Texto extraido.')
                            texto_chave = f'texto_completo_pagina_{page_num}'
                            structured_rows = self._extract_structured_rows_from_text(page_text)
                            if structured_rows:
                                before_count = len(produtos_extraidos)
                                for row in structured_rows:
                                    self._append_produto(
                                        produtos_extraidos=produtos_extraidos,
                                        produto_padronizado=_FileProcessingImplementation._processar_linha_padronizada(
                                            row,
                                            mapeamento_colunas_usuario,
                                        ),
                                        product_type_id=product_type_id,
                                    )
                                added_count = len(produtos_extraidos) - before_count
                                if added_count > 0:
                                    log_pdf.append(
                                        f'Pagina {page_num}: Texto estruturado gerou {added_count} produto(s).'
                                    )
                                    continue
                            if allow_llm:
                                try:
                                    dados_produto = await self._web_data_extractor_service.extrair_dados_produto_com_llm(page_text)
                                    if isinstance(dados_produto, dict):
                                        dados_produto['texto_bruto'] = page_text.strip()[:20000]
                                        before_count = len(produtos_extraidos)
                                        self._append_produto(
                                            produtos_extraidos=produtos_extraidos,
                                            produto_padronizado=dados_produto,
                                            product_type_id=product_type_id,
                                        )
                                        if len(produtos_extraidos) > before_count:
                                            log_pdf.append(f'Pagina {page_num}: Texto processado com LLM.')
                                        else:
                                            log_pdf.append(
                                                f'Pagina {page_num}: LLM retornou payload sem identidade de produto.'
                                            )
                                    else:
                                        log_pdf.append(
                                            f'Pagina {page_num}: LLM retornou formato inesperado; ignorando payload.'
                                        )
                                except Exception as llm_e:
                                    log_pdf.append(f'Pagina {page_num}: Erro ao processar com LLM: {str(llm_e)}')
                            else:
                                token_count = len([tok for tok in page_text.split() if tok])
                                if token_count <= 16:
                                    item = {
                                        'nome_base': f'Conteudo da Pagina {page_num}',
                                        'dados_brutos_adicionais': {
                                            texto_chave: page_text.strip()[:20000]
                                        },
                                    }
                                    self._append_produto(
                                        produtos_extraidos=produtos_extraidos,
                                        produto_padronizado=item,
                                        product_type_id=product_type_id,
                                    )
                                    log_pdf.append(
                                        f'Pagina {page_num}: Texto curto armazenado sem LLM para revisao manual.'
                                    )
                                else:
                                    log_pdf.append(
                                        f'Pagina {page_num}: Texto sem padrao de linha de produto; ignorado (usar regiao/mapeamento).'
                                    )
                        else:
                            log_pdf.append(f'Pagina {page_num}: Nenhum texto extraivel (pode ser imagem ou protegido).')
                if not produtos_extraidos:
                    return [{'erro_processamento_pdf': 'Nenhum dado de produto pode ser extraido do PDF (pode estar protegido, vazio ou somente imagem sem OCR).', 'log_pdf': log_pdf}]
            logger.info('processar_arquivo_pdf: concluido produtos_extraidos=%s paginas=%s', len(produtos_extraidos), len(page_list_to_process))
            return produtos_extraidos
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            log_pdf.append(f'{error.code}: {error.detail}')
            return [{'erro_processamento_pdf': error.detail, 'error_code': error.code, 'log_pdf': log_pdf}]
        except Exception as e:
            import traceback
            log_pdf.append(f'Erro critico ao processar arquivo PDF: {str(e)}')
            logger.error('Erro ao processar arquivo PDF: %s', traceback.format_exc())
            return [{'erro_processamento_pdf': f'Falha critica ao ler arquivo PDF: {str(e)}', 'log_pdf': log_pdf}]
        finally:
            if temp_pdf_path and temp_pdf_path.exists():
                try:
                    temp_pdf_path.unlink()
                except Exception:
                    logger.debug('processar_arquivo_pdf: nao foi possivel remover temp_pdf=%s', temp_pdf_path)

class TabularPreviewEngineRuntime:
    """Runtime OO para preview de planilhas/tabulares."""

    def _decode_csv_bytes(self, conteudo_arquivo: bytes) -> str:
        """Decode csv bytes for secure downstream consumption."""
        try:
            return conteudo_arquivo.decode('utf-8-sig')
        except UnicodeDecodeError:
            return conteudo_arquivo.decode('latin-1')

    def _detect_csv_delimiter(self, conteudo_str: str) -> str:
        """Execute detect csv delimiter as part of this module workflow."""
        sample = conteudo_str[:1024]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
            return dialect.delimiter
        except Exception:
            primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ''
            if ';' in primeira_linha:
                return ';'
            if '\t' in primeira_linha:
                return '\t'
            return ','

    async def preview_arquivo_excel(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo excel as part of this module workflow."""
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                category='excel',
            )
            df = pd.read_excel(io.BytesIO(conteudo_arquivo), sheet_name=0)
            headers = [str(col) for col in df.columns]
            sample_rows = df.head(max_rows).fillna('').to_dict(orient='records')
            return {'headers': headers, 'sample_rows': sample_rows}
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            return {'error': error.detail, 'error_code': error.code}
        except Exception as e:
            logger.error('Erro ao gerar preview de arquivo Excel: %s', e)
            return {'error': f'Falha ao ler arquivo Excel: {str(e)}'}

    async def preview_arquivo_csv(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo csv as part of this module workflow."""
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                category='csv',
            )
            conteudo_str = self._decode_csv_bytes(conteudo_arquivo)
            delimitador = self._detect_csv_delimiter(conteudo_str)
            leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador)
            headers = leitor_csv.fieldnames or []
            sample_rows: List[Dict[str, Any]] = []
            for idx, row in enumerate(leitor_csv):
                if idx >= max_rows:
                    break
                sample_rows.append(row)
            return {'headers': headers, 'sample_rows': sample_rows}
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            return {'error': error.detail, 'error_code': error.code}
        except Exception as e:
            logger.error('Erro ao gerar preview de arquivo CSV: %s', e)
            return {'error': f'Falha ao ler arquivo CSV: {str(e)}'}

class PdfPreviewRuntime:
    """Runtime OO para preview de PDF."""

    def __init__(self, preview_executor: Optional[ThreadPoolExecutor]=None, max_preview_workers: Optional[int]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Preview Runtime."""
        self._max_preview_workers = (
            int(os.getenv('PDF_PREVIEW_WORKERS', '0'))
            if max_preview_workers is None
            else int(max_preview_workers)
        )
        self._preview_executor = preview_executor or self._build_preview_executor()

    def _build_preview_executor(self) -> Optional[ThreadPoolExecutor]:
        """Build preview executor from current inputs and configuration."""
        if self._max_preview_workers <= 0:
            return None
        return ThreadPoolExecutor(max_workers=self._max_preview_workers)

    def _resolve_poppler_path(self) -> Optional[str]:
        """Resolve poppler path from injected repositories or runtime context."""
        return os.getenv('POPPLER_PATH') or settings.POPPLER_PATH

    def _build_page_processor(
        self,
        conteudo_arquivo: bytes,
        dpi: int,
        poppler_path: Optional[str],
    ):
        """Build page processor from current inputs and configuration."""
        return partial(
            self._process_page,
            conteudo_arquivo=conteudo_arquivo,
            dpi=dpi,
            poppler_path=poppler_path,
        )

    def _process_page(
        self,
        page_number: int,
        *,
        conteudo_arquivo: bytes,
        dpi: int,
        poppler_path: Optional[str],
    ) -> Dict[str, Any]:
        """Build preview metadata for a single PDF page."""
        with pdf_open(io.BytesIO(conteudo_arquivo)) as reader:
            page = reader.pages[page_number - 1]
            tables = page.extract_tables()
            result: Dict[str, Any] = {'page': page_number, 'has_table': bool(tables)}
            text = page.extract_text() or ''
            image = convert_from_bytes(
                conteudo_arquivo,
                first_page=page_number,
                last_page=page_number,
                fmt='png',
                dpi=dpi,
                poppler_path=poppler_path,
            )[0]
            png_buf = io.BytesIO()
            image.save(png_buf, format='PNG')
            png_b64 = base64.b64encode(png_buf.getvalue())
            jpeg_buf = io.BytesIO()
            image.convert('RGB').save(jpeg_buf, format='JPEG', optimize=True, quality=70)
            jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())
            if len(jpeg_b64) >= len(png_b64):
                jpeg_buf = io.BytesIO()
                image.convert('RGB').save(jpeg_buf, format='JPEG', optimize=True, quality=50)
                jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())
            if len(jpeg_b64) < len(png_b64):
                b64 = jpeg_b64.decode()
                mime = 'jpeg'
            else:
                b64 = png_b64.decode()
                mime = 'png'
            snippet = '\n'.join(text.splitlines()[:3])
            result.update({'snippet': snippet, 'preview_image': {'page': page_number, 'image': f'data:image/{mime};base64,{b64}'}})
        return result

    async def preview_arquivo_pdf(self, conteudo_arquivo: bytes, ext: str, start_page: int=1, page_count: int=1, dpi: int=72) -> Dict[str, Any]:
        """Execute preview arquivo pdf as part of this module workflow."""
        start = time.perf_counter()
        poppler_dir = self._resolve_poppler_path()
        pdftoppm_path = shutil.which('pdftoppm', path=poppler_dir) if poppler_dir else shutil.which('pdftoppm')
        if pdftoppm_path is None:
            msg = 'Poppler (pdftoppm) executable not found. Install poppler-utils on Linux or set POPPLER_PATH to its directory.'
            logger.error(msg)
            return {'error': msg}
        try:
            _FileProcessingImplementation._validate_file_payload(
                content=conteudo_arquivo,
                extension=ext,
                category='pdf',
            )
            with pdf_open(io.BytesIO(conteudo_arquivo)) as reader:
                num_pages = len(reader.pages)
            loop = asyncio.get_running_loop()
            if page_count == 0:
                page_count = num_pages
            end_page = min(start_page + page_count - 1, num_pages)
            pages_processed = end_page - start_page + 1
            poppler_path = self._resolve_poppler_path()
            preview: Dict[str, Any] = {'num_pages': num_pages, 'table_pages': [], 'sample_rows': {}, 'preview_images': []}
            process_page = self._build_page_processor(
                conteudo_arquivo=conteudo_arquivo,
                dpi=dpi,
                poppler_path=poppler_path,
            )
            tasks = [loop.run_in_executor(self._preview_executor, process_page, p) for p in range(start_page, end_page + 1)]
            results = await asyncio.gather(*tasks)
            for result in sorted(results, key=lambda item: item['page']):
                if result.get('has_table'):
                    preview['table_pages'].append(result['page'])
                if 'snippet' in result:
                    preview['sample_rows'][result['page']] = result['snippet']
                if 'preview_image' in result:
                    preview['preview_images'].append(result['preview_image'])
            duration = time.perf_counter() - start
            logger.info('PDF preview processed %s page(s) in %.4f seconds', pages_processed, duration)
            return preview
        except CatalogImportSanitizationService.FileSecurityValidationError as error:
            return {'error': error.detail, 'error_code': error.code}
        except Exception as e:
            logger.error('Erro ao gerar preview de arquivo PDF: %s', e)
            return {'error': f'Falha ao ler arquivo PDF: {str(e)}'}

class PreviewDispatchRuntime:
    """Runtime OO para despacho de preview por extensao."""

    def __init__(self, tabular_preview_runtime: Optional[TabularPreviewEngineRuntime]=None, pdf_preview_runtime: Optional[PdfPreviewRuntime]=None, extractor_factory: Optional['_PreviewExtractorFactory']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Preview Dispatch Runtime."""
        self._tabular_preview_runtime = tabular_preview_runtime or TabularPreviewEngineRuntime()
        self._pdf_preview_runtime = pdf_preview_runtime or PdfPreviewRuntime()
        self._extractor_factory = extractor_factory or _PreviewExtractorFactory(excel_extractor=_ExcelPreviewExtractor(self._tabular_preview_runtime), csv_extractor=_CsvPreviewExtractor(self._tabular_preview_runtime), pdf_extractor=_PdfPreviewExtractor(self._pdf_preview_runtime))

    async def gerar_preview(self, conteudo_arquivo: bytes, ext: str, max_rows: int=5) -> Dict[str, Any]:
        """Execute gerar preview as part of this module workflow."""
        ext_norm = ext.lower()
        extractor = self._extractor_factory.get_extractor(ext_norm)
        return await extractor.extract(conteudo_arquivo=conteudo_arquivo, ext=ext_norm, max_rows=max_rows)

class _PreviewExtractor:

    """Represent Preview Extractor and centralize its responsibilities inside this module."""
    async def extract(self, *, conteudo_arquivo: bytes, ext: str, max_rows: int) -> Dict[str, Any]:
        """Execute extract as part of this module workflow."""
        raise NotImplementedError

class _ExcelPreviewExtractor(_PreviewExtractor):

    """Represent Excel Preview Extractor and centralize its responsibilities inside this module."""
    def __init__(self, tabular_preview_runtime: TabularPreviewEngineRuntime) -> None:
        """Initialize injected dependencies and runtime configuration for Excel Preview Extractor."""
        self._tabular_preview_runtime = tabular_preview_runtime

    async def extract(self, *, conteudo_arquivo: bytes, ext: str, max_rows: int) -> Dict[str, Any]:
        """Execute extract as part of this module workflow."""
        _ = ext
        return await self._tabular_preview_runtime.preview_arquivo_excel(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

class _CsvPreviewExtractor(_PreviewExtractor):

    """Represent Csv Preview Extractor and centralize its responsibilities inside this module."""
    def __init__(self, tabular_preview_runtime: TabularPreviewEngineRuntime) -> None:
        """Initialize injected dependencies and runtime configuration for Csv Preview Extractor."""
        self._tabular_preview_runtime = tabular_preview_runtime

    async def extract(self, *, conteudo_arquivo: bytes, ext: str, max_rows: int) -> Dict[str, Any]:
        """Execute extract as part of this module workflow."""
        _ = ext
        return await self._tabular_preview_runtime.preview_arquivo_csv(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

class _PdfPreviewExtractor(_PreviewExtractor):

    """Represent Pdf Preview Extractor and centralize its responsibilities inside this module."""
    def __init__(self, pdf_preview_runtime: PdfPreviewRuntime) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Preview Extractor."""
        self._pdf_preview_runtime = pdf_preview_runtime

    async def extract(self, *, conteudo_arquivo: bytes, ext: str, max_rows: int) -> Dict[str, Any]:
        """Execute extract as part of this module workflow."""
        _ = max_rows
        return await self._pdf_preview_runtime.preview_arquivo_pdf(conteudo_arquivo=conteudo_arquivo, ext=ext, start_page=1, page_count=1)

class _PreviewExtractorFactory:

    """Represent Preview Extractor Factory and centralize its responsibilities inside this module."""
    def __init__(self, *, excel_extractor: _PreviewExtractor, csv_extractor: _PreviewExtractor, pdf_extractor: _PreviewExtractor) -> None:
        """Initialize injected dependencies and runtime configuration for Preview Extractor Factory."""
        self._extractors = {'.xlsx': excel_extractor, '.xls': excel_extractor, '.csv': csv_extractor, '.pdf': pdf_extractor}

    def get_extractor(self, ext_norm: str) -> _PreviewExtractor:
        """Retrieve extractor using the current service dependencies."""
        extractor = self._extractors.get(ext_norm)
        if extractor is None:
            raise ValueError('Formato de arquivo nao suportado para preview')
        return extractor

class PdfImageConversionRuntime:
    """Runtime OO para conversao de bytes PDF em imagens base64."""

    def _resolve_poppler_path(self) -> Optional[str]:
        """Resolve poppler path from injected repositories or runtime context."""
        return os.getenv('POPPLER_PATH') or settings.POPPLER_PATH

    def _ensure_poppler_available(self, poppler_dir: Optional[str]) -> Optional[str]:
        """Ensure poppler available exists or is valid before continuing the flow."""
        pdftoppm_path = shutil.which('pdftoppm', path=poppler_dir) if poppler_dir else shutil.which('pdftoppm')
        if pdftoppm_path is None:
            msg = 'Poppler (pdftoppm) executable not found. Install poppler-utilson Linux or set POPPLER_PATH to its directory.'
            logger.error(msg)
            raise RuntimeError(msg)
        return poppler_dir

    def _convert_sync(self, conteudo_arquivo: bytes, max_pages: int, start_page: int, dpi: int) -> List[str]:
        """Execute convert sync as part of this module workflow."""
        poppler_dir = self._resolve_poppler_path()
        poppler_path = self._ensure_poppler_available(poppler_dir)
        last_page = None if max_pages == 0 else start_page + max_pages - 1
        images = convert_from_bytes(
            conteudo_arquivo,
            first_page=start_page,
            last_page=last_page,
            dpi=dpi,
            fmt='png',
            poppler_path=poppler_path,
        )
        result: List[str] = []
        for img in images:
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            result.append(base64.b64encode(buf.getvalue()).decode())
        return result

    async def pdf_bytes_to_images(self, conteudo_arquivo: bytes, max_pages: int=1, start_page: int=1, dpi: int=200) -> List[str]:
        """Execute pdf bytes to images as part of this module workflow."""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: self._convert_sync(conteudo_arquivo=conteudo_arquivo, max_pages=max_pages, start_page=start_page, dpi=dpi))

class _PdfRegionExtractionUtils:

    """Represent Pdf Region Extraction Utils and centralize its responsibilities inside this module."""
    @staticmethod
    def make_unique(cols: List[Any]) -> List[str]:
        """Execute make unique as part of this module workflow."""
        seen: Dict[str, int] = {}
        unique: List[str] = []
        for col in cols:
            base = _FileProcessingImplementation._limpar_valor_extraido(col) or 'col'
            count = seen.get(base, 0)
            name = f'{base}_{count}' if count else base
            seen[base] = count + 1
            unique.append(name)
        return unique

    @staticmethod
    def clean_df(df: pd.DataFrame) -> pd.DataFrame:
        """Execute clean df as part of this module workflow."""
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna(axis=1, how='all')
        df = df.dropna(axis=0, how='all')
        df = df.fillna('')
        return df

    @staticmethod
    def median_int(values: List[int], default: int) -> int:
        """Execute median int as part of this module workflow."""
        if not values:
            return default
        sorted_values = sorted(values)
        mid = len(sorted_values) // 2
        if len(sorted_values) % 2 == 1:
            return int(sorted_values[mid])
        return int((sorted_values[mid - 1] + sorted_values[mid]) / 2)

    @staticmethod
    def cluster_positions(x_values: List[int], tolerance: int) -> List[int]:
        """Execute cluster positions as part of this module workflow."""
        clusters: List[int] = []
        for x in x_values:
            if not clusters or abs(x - clusters[-1]) > tolerance:
                clusters.append(x)
        return clusters

    @staticmethod
    def normalize_ocr_snippet(text: Any) -> str:
        """Normalize ocr snippet to keep behavior consistent across callers."""
        normalized = unicodedata.normalize('NFKD', str(text or ''))
        normalized = ''.join((ch for ch in normalized if not unicodedata.combining(ch)))
        normalized = normalized.upper()
        normalized = re.sub('[^A-Z0-9 ]+', ' ', normalized)
        normalized = re.sub('\\s+', ' ', normalized).strip()
        return normalized

    @classmethod
    def header_field_for_text(cls, text: str) -> Optional[str]:
        """Execute header field for text as part of this module workflow."""
        t = cls.normalize_ocr_snippet(text)
        if not t:
            return None
        if 'FAB' in t:
            return 'n_fab'
        if 'ORIGINAL' in t:
            return 'n_original'
        if 'DESCR' in t:
            return 'descricao'
        if 'APLIC' in t:
            return 'aplicacao'
        if 'MATERIAL' in t or t in {'MAT', 'MATER'}:
            return 'material'
        return None

    @classmethod
    def detect_header_columns(cls, merged_lines: List[List[Dict[str, Any]]]) -> Optional[Dict[str, Any]]:
        """Execute detect header columns as part of this module workflow."""
        if not merged_lines:
            return None
        ratio_by_field = {'n_fab': 0.04, 'n_original': 0.2, 'descricao': 0.38, 'aplicacao': 0.67, 'material': 0.88}
        marker_pairs = [('FAB', 'n_fab'), ('ORIGINAL', 'n_original'), ('DESCR', 'descricao'), ('APLIC', 'aplicacao'), ('MATERIAL', 'material')]
        best: Optional[Dict[str, Any]] = None
        line_limit = min(len(merged_lines), 40)
        for line_idx in range(line_limit):
            line = merged_lines[line_idx]
            field_positions: Dict[str, int] = {}
            for seg in line:
                field = cls.header_field_for_text(seg.get('text', ''))
                if not field:
                    continue
                x0 = int(seg.get('x0', 0) or 0)
                if field not in field_positions or x0 < field_positions[field]:
                    field_positions[field] = x0
            line_norm = cls.normalize_ocr_snippet(' '.join((seg.get('text', '') for seg in line)))
            marker_fields = [field for marker, field in marker_pairs if marker in line_norm]
            if len(field_positions) < 3 and len(marker_fields) >= 3:
                line_x0 = min((int(seg.get('x0', 0) or 0) for seg in line))
                line_x1 = max((int(seg.get('x1', seg.get('x0', 0)) or 0) for seg in line))
                line_width = max(1, line_x1 - line_x0)
                for field in marker_fields:
                    if field in field_positions:
                        continue
                    ratio = ratio_by_field.get(field, 0.5)
                    field_positions[field] = int(line_x0 + line_width * ratio)
            if len(field_positions) < 3:
                continue
            ordered = sorted(field_positions.items(), key=lambda item: item[1])
            candidate = {'line_idx': line_idx, 'headers': [name for name, _ in ordered], 'bounds': [x for _, x in ordered], 'score': len(field_positions)}
            if best is None:
                best = candidate
                continue
            if candidate['score'] > best['score']:
                best = candidate
        return best

    @classmethod
    def is_header_like_row(cls, text: str) -> bool:
        """Execute is header like row as part of this module workflow."""
        norm = cls.normalize_ocr_snippet(text)
        if not norm:
            return False
        markers = ('FAB', 'ORIGINAL', 'DESCR', 'APLIC', 'MATERIAL')
        hits = sum((1 for marker in markers if marker in norm))
        return hits >= 2

    @classmethod
    def filter_ocr_rows(cls, raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute filter ocr rows as part of this module workflow."""
        filtered_rows: List[Dict[str, Any]] = []
        for row in raw_rows:
            cleaned_row = {k: (v or '').strip() for k, v in row.items()}
            non_empty_values = [v for v in cleaned_row.values() if v]
            if not non_empty_values:
                continue
            joined = ' '.join(non_empty_values).strip()
            if cls.is_header_like_row(joined):
                continue
            if joined in {'-', '--', '!', '|', ':', ';', '.', ','}:
                continue
            alnum_count = len(re.sub('[^0-9A-Za-z\\u00C0-\\u00FF]', '', joined))
            if alnum_count < 2:
                continue
            filtered_rows.append(cleaned_row)
        return filtered_rows

    @classmethod
    def tables_to_df(cls, tables: List[List[List[Any]]]) -> pd.DataFrame:
        """Execute tables to df as part of this module workflow."""
        rows: List[Dict[str, Any]] = []
        headers: List[str] = []
        for table in tables:
            if not table or len(table) < 2:
                continue
            headers = cls.make_unique(table[0])
            for row in table[1:]:
                row_fixed = list(row) + [''] * (len(headers) - len(row))
                row_fixed = row_fixed[:len(headers)]
                rows.append({headers[i]: row_fixed[i] for i in range(len(headers))})
        if rows and headers:
            return cls.clean_df(pd.DataFrame(rows, columns=headers))
        return pd.DataFrame()

    @staticmethod
    def group_words_by_line_ids(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Group words by line ids."""
        buckets: Dict[tuple[int, int, int], List[Dict[str, Any]]] = {}
        for word in words:
            line_num = int(word.get('line', 0) or 0)
            if line_num <= 0:
                continue
            key = (int(word.get('block', 0) or 0), int(word.get('par', 0) or 0), line_num)
            buckets.setdefault(key, []).append(word)
        lines = list(buckets.values())
        lines.sort(key=lambda line_words: min((item['y'] for item in line_words)))
        return lines

    @classmethod
    def group_words_by_y(cls, words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Execute group words by y as part of this module workflow."""
        if not words:
            return []
        heights = [int(w.get('h', 0) or 0) for w in words if int(w.get('h', 0) or 0) > 0]
        tol_y = max(10, int(cls.median_int(heights, 12) * 0.8))
        words_sorted = sorted(words, key=lambda item: (item['y'], item['x']))
        lines_grouped: List[List[Dict[str, Any]]] = []
        for word in words_sorted:
            if lines_grouped and abs(word['y'] - lines_grouped[-1][0]['y']) <= tol_y:
                lines_grouped[-1].append(word)
            else:
                lines_grouped.append([word])
        return lines_grouped

    @classmethod
    def merge_words_in_line(cls, line_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute merge words in line as part of this module workflow."""
        if not line_words:
            return []
        sorted_words = sorted(line_words, key=lambda item: item['x'])
        widths = [int(w.get('w', 0) or 0) for w in sorted_words if int(w.get('w', 0) or 0) > 0]
        gap_threshold = max(14, int(cls.median_int(widths, 8) * 1.8))
        segments: List[Dict[str, Any]] = []
        for word in sorted_words:
            x0 = int(word['x'])
            x1 = int(word['x'] + word['w'])
            text = str(word['text']).strip()
            if not text:
                continue
            if not segments:
                segments.append({'x0': x0, 'x1': x1, 'parts': [text]})
                continue
            gap = x0 - int(segments[-1]['x1'])
            if gap <= gap_threshold:
                segments[-1]['x1'] = max(int(segments[-1]['x1']), x1)
                segments[-1]['parts'].append(text)
            else:
                segments.append({'x0': x0, 'x1': x1, 'parts': [text]})
        merged: List[Dict[str, Any]] = []
        for seg in segments:
            seg_text = ' '.join(seg['parts']).strip()
            merged.append({'x0': int(seg['x0']), 'x1': int(seg['x1']), 'text': seg_text})
        return merged

class PdfAssetUtilityRuntime:
    """Runtime OO para utilitarios de assets PDF."""

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate pdf page images as part of this module workflow."""
        try:
            import fitz
        except Exception as e:
            logger.error('PyMuPDF (fitz) not available: %s', e)
            raise
        output_dir = Path('Backend') / 'static' / 'previews' / str(file_id)
        output_dir.mkdir(parents=True, exist_ok=True)
        urls: List[str] = []
        with fitz.open(file_path) as doc:
            page_count = min(len(doc), 20)
            for i in range(page_count):
                page = doc.load_page(i)
                pix = page.get_pixmap(dpi=150)
                image_path = output_dir / f'page-{i + 1}.png'
                pix.save(str(image_path))
                url = f'/static/previews/{file_id}/page-{i + 1}.png'
                urls.append(url)
        return urls

    def extract_pdf_region_image(self, file_path: str, page_number: int, region: Optional[List[float]]=None, dpi: int=300) -> bytes:
        """Execute extract pdf region image as part of this module workflow."""
        logger.debug('Recebendo coordenadas: %s', region)
        with pdfplumber.open(file_path) as pdf:
            if not 1 <= page_number <= len(pdf.pages):
                raise ValueError(f'Numero de pagina invalido: {page_number}. PDF tem {len(pdf.pages)} paginas.')
            page = pdf.pages[page_number - 1]
            page_to_process = page
            if region and len(region) == 4:
                logger.debug('Recortando imagem')
                bbox = tuple(map(float, region))
                page_to_process = page.crop(bbox)
            page_image = page_to_process.to_image(resolution=dpi)
            buf = io.BytesIO()
            page_image.original.save(buf, format='PNG')
            return buf.getvalue()

    def parse_annotation_to_dataframe(self, annotation: object, vertical_tolerance: int=5) -> pd.DataFrame:
        """Parse annotation to dataframe into structured data used by downstream logic."""
        logger.debug('Iniciando analise do texto')
        try:
            words: List[Dict[str, Any]] = []
            for page in getattr(annotation, 'pages', []):
                for block in getattr(page, 'blocks', []):
                    for paragraph in getattr(block, 'paragraphs', []):
                        for word in getattr(paragraph, 'words', []):
                            text = ''.join([symbol.text for symbol in getattr(word, 'symbols', [])])
                            vertices = getattr(word.bounding_box, 'vertices', [])
                            xs = [vertex.x for vertex in vertices]
                            ys = [vertex.y for vertex in vertices]
                            x_min = min(xs) if xs else 0
                            y_min = min(ys) if ys else 0
                            words.append({'text': text, 'x': x_min, 'y': y_min})
            if not words:
                return pd.DataFrame()
            words.sort(key=lambda word: word['y'])
            lines: List[List[Dict[str, Any]]] = []
            for word in words:
                if lines and abs(word['y'] - lines[-1][0]['y']) <= vertical_tolerance:
                    lines[-1].append(word)
                else:
                    lines.append([word])
            for line in lines:
                line.sort(key=lambda word: word['x'])
            x_positions = sorted({word['x'] for line in lines for word in line})
            column_boundaries: List[int] = []
            x_tol = 20
            for x_pos in x_positions:
                if not column_boundaries or abs(x_pos - column_boundaries[-1]) > x_tol:
                    column_boundaries.append(x_pos)
            rows: List[List[str]] = []
            for line in lines:
                row = ['' for _ in column_boundaries]
                for word in line:
                    col_idx = min(range(len(column_boundaries)), key=lambda i: abs(word['x'] - column_boundaries[i]))
                    row[col_idx] = (row[col_idx] + ' ' + word['text']).strip()
                rows.append(row)
            columns = [f'col_{i + 1}' for i in range(len(column_boundaries))]
            return pd.DataFrame(rows, columns=columns)
        except Exception as e:
            logger.exception('Falha ao processar texto extraido')
            raise HTTPException(status_code=500, detail='Ocorreu um erro durante a extracao de dados.') from e

class CatalogStorageWorkflow:
    """Workflow OO para operacoes de storage de catalogo."""

    def __init__(self, runtime: Optional['CatalogStorageRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Catalog Storage Workflow."""
        self._runtime = runtime or CatalogStorageRuntime()

    async def save_uploaded_catalog(self, file: UploadFile, fornecedor_id: Optional[int]=None) -> models.CatalogImportFile:
        """Execute save uploaded catalog as part of this module workflow."""
        return await self._runtime.save_uploaded_catalog(file=file, fornecedor_id=fornecedor_id)

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete catalog file as part of this module workflow."""
        self._runtime.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str) -> str:
        """Retrieve file path by id using the current service dependencies."""
        return self._runtime.get_file_path_by_id(db=db, file_id=file_id)

class CatalogStorageRuntime:

    """Represent Catalog Storage Runtime and centralize its responsibilities inside this module."""
    async def save_uploaded_catalog(self, file: UploadFile, fornecedor_id: Optional[int]=None) -> models.CatalogImportFile:
        """Execute save uploaded catalog as part of this module workflow."""
        return await _FileProcessingImplementation._save_uploaded_catalog_impl(file=file, fornecedor_id=fornecedor_id)

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete catalog file as part of this module workflow."""
        _FileProcessingImplementation._delete_catalog_file_impl(stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str) -> str:
        """Retrieve file path by id using the current service dependencies."""
        return _FileProcessingImplementation._get_file_path_by_id_impl(db=db, file_id=file_id)
class TabularIngestionWorkflow:
    """Workflow OO para ingestÃ£o de arquivos tabulares (Excel/CSV)."""

    def __init__(self, runtime: Optional['TabularIngestionRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Tabular Ingestion Workflow."""
        self._runtime = runtime or TabularIngestionRuntime()

    async def processar_arquivo_excel(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, sheet_name: Optional[str]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel as part of this module workflow."""
        return await self._runtime.processar_arquivo_excel(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, sheet_name=sheet_name, product_type_id=product_type_id)

    async def processar_arquivo_csv(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo csv as part of this module workflow."""
        return await self._runtime.processar_arquivo_csv(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, product_type_id=product_type_id)

class TabularIngestionRuntime:

    """Represent Tabular Ingestion Runtime and centralize its responsibilities inside this module."""
    async def processar_arquivo_excel(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, sheet_name: Optional[str]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel as part of this module workflow."""
        return await _FileProcessingImplementation._processar_arquivo_excel_impl(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, sheet_name=sheet_name, product_type_id=product_type_id)

    async def processar_arquivo_csv(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, product_type_id: Optional[int]=None) -> List[Dict[str, Any]]:
        """Execute processar arquivo csv as part of this module workflow."""
        return await _FileProcessingImplementation._processar_arquivo_csv_impl(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, product_type_id=product_type_id)
class TabularPreviewWorkflow:
    """Workflow OO para preview tabular (Excel/CSV)."""

    def __init__(self, runtime: Optional['TabularPreviewRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Tabular Preview Workflow."""
        self._runtime = runtime or TabularPreviewRuntime()

    async def preview_arquivo_excel(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo excel as part of this module workflow."""
        return await self._runtime.preview_arquivo_excel(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

    async def preview_arquivo_csv(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo csv as part of this module workflow."""
        return await self._runtime.preview_arquivo_csv(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

class TabularPreviewRuntime:

    """Represent Tabular Preview Runtime and centralize its responsibilities inside this module."""
    async def preview_arquivo_excel(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo excel as part of this module workflow."""
        return await _FileProcessingImplementation._preview_arquivo_excel_impl(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)

    async def preview_arquivo_csv(self, conteudo_arquivo: bytes, max_rows: int=5) -> Dict[str, Any]:
        """Execute preview arquivo csv as part of this module workflow."""
        return await _FileProcessingImplementation._preview_arquivo_csv_impl(conteudo_arquivo=conteudo_arquivo, max_rows=max_rows)
class PdfAssetRuntime:
    """Runtime OO para dependencias de utilitarios de imagem/regiao de PDF."""
    RUNTIME_FIELDS = ('pdf_image_runtime', 'pdf_asset_runtime')

    def __init__(self, *, pdf_image_runtime: Optional[Any]=None, pdf_asset_runtime: Optional[Any]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Asset Runtime."""
        self.pdf_image_runtime = pdf_image_runtime or PdfImageConversionRuntime()
        self.pdf_asset_runtime = pdf_asset_runtime or PdfAssetUtilityRuntime()

    def apply_overrides(self, runtime: Any) -> 'PdfAssetRuntime':
        """Execute apply overrides as part of this module workflow."""
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self

class PdfAssetWorkflow:
    """Workflow OO para utilitarios de imagem/regiao de PDF."""

    def __init__(self, runtime: Optional[Any]=None, pdf_image_runtime: Optional[PdfImageConversionRuntime]=None, pdf_asset_runtime: Optional[PdfAssetRuntime]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Asset Workflow."""
        runtime_obj = PdfAssetRuntime(pdf_image_runtime=pdf_image_runtime, pdf_asset_runtime=pdf_asset_runtime)
        if runtime is not None:
            runtime_obj.apply_overrides(runtime)
        self._runtime = runtime_obj
        self._pdf_image_runtime = runtime_obj.pdf_image_runtime
        self._pdf_asset_runtime = runtime_obj.pdf_asset_runtime

    async def pdf_bytes_to_images(self, conteudo_arquivo: bytes, max_pages: int=1, start_page: int=1, dpi: int=200) -> List[str]:
        """Execute pdf bytes to images as part of this module workflow."""
        return await self._pdf_image_runtime.pdf_bytes_to_images(conteudo_arquivo=conteudo_arquivo, max_pages=max_pages, start_page=start_page, dpi=dpi)

    def pdf_pages_to_images(self, db: Session, file: UploadFile, fornecedor_id: int, user_id: int, offset: int, limit: int) -> Dict[str, Any]:
        """Execute pdf pages to images as part of this module workflow."""
        return _FileProcessingImplementation._pdf_pages_to_images_impl(db=db, file=file, fornecedor_id=fornecedor_id, user_id=user_id, offset=offset, limit=limit)

    async def extrair_pagina_pdf(self, conteudo_pdf: bytes, page_number: int, region: Optional[List[float]]=None) -> Dict[str, Any]:
        """Execute extrair pagina pdf as part of this module workflow."""
        return await _FileProcessingImplementation._extrair_pagina_pdf_impl(conteudo_pdf=conteudo_pdf, page_number=page_number, region=region)

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate pdf page images as part of this module workflow."""
        return self._pdf_asset_runtime.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(self, file_path: str, page_number: int, region: Optional[List[float]]=None, dpi: int=300) -> bytes:
        """Execute extract pdf region image as part of this module workflow."""
        return self._pdf_asset_runtime.extract_pdf_region_image(file_path=file_path, page_number=page_number, region=region, dpi=dpi)

    def parse_annotation_to_dataframe(self, annotation: object, vertical_tolerance: int=5) -> pd.DataFrame:
        """Parse annotation to dataframe into structured data used by downstream logic."""
        return self._pdf_asset_runtime.parse_annotation_to_dataframe(annotation=annotation, vertical_tolerance=vertical_tolerance)
class PdfProcessingRuntime:
    """Runtime OO para dependencias de processamento e preview de PDF."""
    RUNTIME_FIELDS = ('pdf_ingestion_runtime', 'pdf_preview_runtime', 'preview_dispatch_runtime', 'extract_data_from_pdf_region', 'ocr_runtime_state')

    def __init__(self, *, pdf_ingestion_runtime: Optional[Any]=None, pdf_preview_runtime: Optional[Any]=None, preview_dispatch_runtime: Optional[Any]=None, extract_data_from_pdf_region: Optional[Any]=None, ocr_runtime_state: Optional[OcrRuntimeState]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Processing Runtime."""
        self.pdf_ingestion_runtime = pdf_ingestion_runtime or PdfIngestionRuntime()
        self.pdf_preview_runtime = pdf_preview_runtime or PdfPreviewRuntime()
        self.preview_dispatch_runtime = preview_dispatch_runtime or PreviewDispatchRuntime()
        self.ocr_runtime_state = ocr_runtime_state or OcrRuntimeState()
        self.extract_data_from_pdf_region = extract_data_from_pdf_region or (
            lambda file_path, page_number, region=None: _FileProcessingImplementation._extract_data_from_pdf_region_impl(
                file_path=file_path,
                page_number=page_number,
                region=region,
                ocr_runtime_state=self.ocr_runtime_state,
            )
        )

    def apply_overrides(self, runtime: Any) -> 'PdfProcessingRuntime':
        """Execute apply overrides as part of this module workflow."""
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self

class PdfProcessingWorkflow:
    """Workflow OO para processamento e preview de PDF."""

    def __init__(self, runtime: Optional[Any]=None, pdf_ingestion_runtime: Optional[Any]=None, pdf_preview_runtime: Optional[Any]=None, preview_dispatch_runtime: Optional[Any]=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Processing Workflow."""
        runtime_obj = PdfProcessingRuntime(pdf_ingestion_runtime=pdf_ingestion_runtime, pdf_preview_runtime=pdf_preview_runtime, preview_dispatch_runtime=preview_dispatch_runtime)
        if runtime is not None:
            runtime_obj.apply_overrides(runtime)
        self._runtime = runtime_obj
        self._extract_data_from_pdf_region = runtime_obj.extract_data_from_pdf_region
        self._pdf_ingestion_runtime = runtime_obj.pdf_ingestion_runtime
        self._pdf_preview_runtime = runtime_obj.pdf_preview_runtime
        self._preview_dispatch_runtime = runtime_obj.preview_dispatch_runtime

    async def processar_arquivo_pdf(self, conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]]=None, usar_llm: bool=True, product_type_id: Optional[int]=None, pages: Optional[List[int]]=None, region: Optional[List[float]]=None, extraction_mode: str='ocr') -> List[Dict[str, Any]]:
        """Execute processar arquivo pdf as part of this module workflow."""
        return await self._pdf_ingestion_runtime.processar_arquivo_pdf(conteudo_arquivo=conteudo_arquivo, mapeamento_colunas_usuario=mapeamento_colunas_usuario, usar_llm=usar_llm, product_type_id=product_type_id, pages=pages, region=region, extraction_mode=extraction_mode)

    async def preview_arquivo_pdf(self, conteudo_arquivo: bytes, ext: str, start_page: int=1, page_count: int=1, dpi: int=72) -> Dict[str, Any]:
        """Execute preview arquivo pdf as part of this module workflow."""
        return await self._pdf_preview_runtime.preview_arquivo_pdf(conteudo_arquivo=conteudo_arquivo, ext=ext, start_page=start_page, page_count=page_count, dpi=dpi)

    async def gerar_preview(self, conteudo_arquivo: bytes, ext: str, max_rows: int=5) -> Dict[str, Any]:
        """Execute gerar preview as part of this module workflow."""
        return await self._preview_dispatch_runtime.gerar_preview(conteudo_arquivo=conteudo_arquivo, ext=ext, max_rows=max_rows)

    def extract_data_from_pdf_region(self, file_path: str, page_number: int, region: Optional[List[float]]=None) -> pd.DataFrame:
        """Extract data from pdf region."""
        return self._extract_data_from_pdf_region(file_path=file_path, page_number=page_number, region=region)
class PdfJobWorkflow:
    """Workflow OO para processamento assÃ­ncrono de jobs de PDF."""

    def __init__(self, runtime: Optional['PdfJobRuntime']=None) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Job Workflow."""
        self._runtime = runtime or PdfJobRuntime()

    async def process_pdf_job(self, job_id: int, pdf_path: str, start_page: int=1, mapping: Optional[Dict[str, str]]=None) -> None:
        """Execute pdf job and return the normalized execution result."""
        await self._runtime.process_pdf_job(job_id=job_id, pdf_path=pdf_path, start_page=start_page, mapping=mapping)

    def extract_data_from_single_page(self, file_path: str, page_number: int) -> Dict[str, Any]:
        """Extract data from single page."""
        return self._runtime.extract_data_from_single_page(file_path=file_path, page_number=page_number)

class PdfJobRuntime:

    """Represent Pdf Job Runtime and centralize its responsibilities inside this module."""
    def __init__(
        self,
        session_provider: Optional[Any] = None,
        catalog_import_file_repository_factory: Callable[[Session], CatalogImportFileRepository] = CatalogImportFileRepository,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Pdf Job Runtime."""
        if session_provider is None:
            self._session_factory = database.SessionLocal
        else:
            self._session_factory = session_provider.open_session
        self._catalog_import_file_repository_factory = catalog_import_file_repository_factory

    async def process_pdf_job(self, job_id: int, pdf_path: str, start_page: int=1, mapping: Optional[Dict[str, str]]=None) -> None:
        """Execute pdf job and return the normalized execution result."""
        session = self._session_factory()
        try:
            catalog_file_repository = self._catalog_import_file_repository_factory(session)
            await _FileProcessingImplementation._process_pdf_job_impl(
                job_id=job_id,
                pdf_path=pdf_path,
                start_page=start_page,
                mapping=mapping,
                catalog_file_repository=catalog_file_repository,
            )
        finally:
            session.close()

    def extract_data_from_single_page(self, file_path: str, page_number: int) -> Dict[str, Any]:
        """Extract data from single page."""
        return _FileProcessingImplementation._extract_data_from_single_page_impl(file_path=file_path, page_number=page_number)
class FileProcessingRuntime:
    """Composicao OO para fluxos de processamento de arquivo sem estado global."""

    def __init__(self, *, catalog_storage_workflow: Optional[CatalogStorageWorkflow]=None, line_mapping_workflow: Optional[LineMappingWorkflow]=None, tabular_ingestion_workflow: Optional[TabularIngestionWorkflow]=None, tabular_preview_workflow: Optional[TabularPreviewWorkflow]=None, pdf_asset_workflow: Optional[PdfAssetWorkflow]=None, pdf_processing_workflow: Optional[PdfProcessingWorkflow]=None, pdf_job_workflow: Optional[PdfJobWorkflow]=None) -> None:
        """Initialize injected dependencies and runtime configuration for File Processing Runtime."""
        self._catalog_storage = catalog_storage_workflow or CatalogStorageWorkflow()
        self._line_mapping = line_mapping_workflow or LineMappingWorkflow()
        self._tabular_ingestion = tabular_ingestion_workflow or TabularIngestionWorkflow()
        self._tabular_preview = tabular_preview_workflow or TabularPreviewWorkflow()
        self._pdf_asset = pdf_asset_workflow or PdfAssetWorkflow()
        self._pdf_processing = pdf_processing_workflow or PdfProcessingWorkflow()
        self._pdf_job = pdf_job_workflow or PdfJobWorkflow()

    async def save_uploaded_catalog(
        self,
        file: UploadFile,
        fornecedor_id: Optional[int] = None,
    ) -> models.CatalogImportFile:
        """Execute save uploaded catalog as part of this module workflow."""
        return await self._catalog_storage.save_uploaded_catalog(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        """Execute delete catalog file as part of this module workflow."""
        return self._catalog_storage.delete_catalog_file(stored_filename=stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str | int) -> str:
        """Retrieve file path by id using the current service dependencies."""
        return self._catalog_storage.get_file_path_by_id(db=db, file_id=file_id)

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Execute processar arquivo excel as part of this module workflow."""
        return await self._tabular_ingestion.processar_arquivo_excel(
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
        return await self._tabular_ingestion.processar_arquivo_csv(
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
        extraction_mode: str = "ocr",
    ) -> List[Dict[str, Any]]:
        """Execute processar arquivo pdf as part of this module workflow."""
        return await self._pdf_processing.processar_arquivo_pdf(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            usar_llm=usar_llm,
            product_type_id=product_type_id,
            pages=pages,
            region=region,
            extraction_mode=extraction_mode,
        )

    async def preview_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute preview arquivo excel as part of this module workflow."""
        return await self._tabular_preview.preview_arquivo_excel(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        max_rows: int = 5,
    ) -> Dict[str, Any]:
        """Execute preview arquivo csv as part of this module workflow."""
        return await self._tabular_preview.preview_arquivo_csv(
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
        return await self._pdf_processing.preview_arquivo_pdf(
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
        return await self._pdf_processing.gerar_preview(
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
        return await self._pdf_asset.pdf_bytes_to_images(
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
        return self._pdf_asset.pdf_pages_to_images(
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
        return await self._pdf_asset.extrair_pagina_pdf(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        """Execute generate pdf page images as part of this module workflow."""
        return self._pdf_asset.generate_pdf_page_images(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        """Execute extract pdf region image as part of this module workflow."""
        return self._pdf_asset.extract_pdf_region_image(
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
        return self._pdf_asset.parse_annotation_to_dataframe(
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
        return self._pdf_processing.extract_data_from_pdf_region(
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
        return await self._pdf_job.process_pdf_job(
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
        """Extract data from single page."""
        return self._pdf_job.extract_data_from_single_page(
            file_path=file_path,
            page_number=page_number,
        )

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Execute processar linha padronizada as part of this module workflow."""
        return self._line_mapping.processar_linha_padronizada(
            linha_original=linha_original,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        )

