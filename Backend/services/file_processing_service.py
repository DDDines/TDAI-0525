# catalogai_project/Backend/services/file_processing_service.py

import pandas as pd

from pdfplumber import open as pdf_open

import csv

import io

import chardet

import base64

import os
import re
import tempfile
import unicodedata

import asyncio

from sqlalchemy.orm import Session

from concurrent.futures import ThreadPoolExecutor

from pdf2image import convert_from_bytes, convert_from_path

import time

from typing import List, Dict, Any, Union, Optional

import shutil

from pathlib import Path

from uuid import uuid4

from fastapi import UploadFile, HTTPException

import uuid

import pdfplumber

from pdfplumber.pdf import PDF as PdfPlumberPDF



from Backend.core.logging_config import get_logger

from Backend.core.config import settings

from Backend import models, crud_fornecedores, schemas

from Backend.application.services.web_data_extractor_facade import (
    WebDataExtractorFacade,
)



logger = get_logger(__name__)
web_data_extractor_service = WebDataExtractorFacade()

try:
    from pdfminer.pdfdocument import PDFPasswordIncorrect
except Exception:
    PDFPasswordIncorrect = None


def _is_pdf_password_error(error: Exception) -> bool:
    """Detecta falha de senha em PDF sem depender de excecao especifica do pdfplumber."""
    if error is None:
        return False

    error_type_name = error.__class__.__name__.lower()
    message = str(error).lower()

    if "password" in error_type_name:
        return True
    if "password" in message or "senha" in message:
        return True
    if "decrypt" in message and "pdf" in message:
        return True

    if PDFPasswordIncorrect is not None and isinstance(error, PDFPasswordIncorrect):
        return True

    return False

def _resolve_storage_path(path_value: Union[str, Path]) -> Path:
    """Resolve caminhos relativos de storage sem duplicar prefixo Backend."""
    p = Path(path_value)
    if p.is_absolute():
        return p

    backend_root = Path(__file__).resolve().parent.parent
    project_root = backend_root.parent
    if p.parts and p.parts[0].lower() == "backend":
        return project_root / p
    return backend_root / p



# Maximum number of worker threads used when processing PDF pages

MAX_PREVIEW_WORKERS = int(os.getenv("PDF_PREVIEW_WORKERS", "0"))

_preview_executor = (

    ThreadPoolExecutor(max_workers=MAX_PREVIEW_WORKERS)

    if MAX_PREVIEW_WORKERS > 0

    else None

)



# Verifica disponibilidade do Tesseract (sem spam de log)
# Tenta caminhos padroes do Windows se nao estiver no PATH.
OCR_AVAILABLE = False
OCR_EXEC_AVAILABLE = False
OCR_EXEC_FAILED_ONCE = False

try:
    import pytesseract  # type: ignore
    from PIL import Image  # type: ignore

    if shutil.which('tesseract') is None:
        candidate_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        ]
        for cpath in candidate_paths:
            if os.path.exists(cpath):
                pytesseract.pytesseract.tesseract_cmd = cpath  # type: ignore
                logger.info('Tesseract definido para caminho detectado: %s', cpath)
                break

    pytesseract.get_tesseract_version()
    OCR_AVAILABLE = True
    OCR_EXEC_AVAILABLE = True
except Exception as e:
    OCR_AVAILABLE = False
    OCR_EXEC_AVAILABLE = False
    logger.warning(
        'OCR indisponivel (pytesseract/tesseract): %s. Ajuste PATH/TESSDATA_PREFIX.',
        e,
    )

async def _save_uploaded_catalog_impl(

    file: UploadFile, fornecedor_id: Optional[int] = None

) -> models.CatalogImportFile:

    """Salva o arquivo de catálogo no disco e retorna um objeto CatalogImportFile.



    Parameters

    ----------

    file: UploadFile

        Arquivo recebido na requisição.

    fornecedor_id: Optional[int]

        Identificador do fornecedor para o qual o catálogo será importado.

    """

    directory = _resolve_storage_path(Path(settings.UPLOAD_DIRECTORY) / "catalogs")

    directory.mkdir(parents=True, exist_ok=True)



    ext = Path(file.filename).suffix

    unique_name = f"{uuid4().hex}{ext}"

    stored_path = directory / unique_name



    content = await file.read()

    with open(stored_path, "wb") as f_out:

        f_out.write(content)

    await file.close()



    return models.CatalogImportFile(

        original_filename=file.filename,

        stored_filename=unique_name,

        status="UPLOADED",

        fornecedor_id=fornecedor_id,

    )





def _delete_catalog_file_impl(stored_filename: str) -> None:

    """Remove a stored catalog file from disk if it exists."""

    directory = _resolve_storage_path(Path(settings.UPLOAD_DIRECTORY) / "catalogs")

    path = directory / stored_filename

    try:

        if path.exists():

            path.unlink()

    except Exception:

        logger.exception("Erro ao remover arquivo %s", stored_filename)





class _LineNormalizationRuntime:
    """Runtime OO para normalizacao de valores, mapeamento e split SKU/Nome."""

    def limpar_valor_extraido(self, valor: Any) -> Optional[str]:
        if valor is None:
            return None
        try:
            cleaned = str(valor).strip()
            if cleaned.lower() in {"", "nan", "none", "#n/a", "na", "<na>"}:
                return None
            return cleaned
        except Exception:
            return None

    def valor_tem_conteudo_util(self, valor: Any) -> bool:
        if valor is None:
            return False
        cleaned = str(valor).strip()
        if not cleaned:
            return False
        if len(re.sub(r"[^0-9A-Za-z\u00C0-\u00FF]", "", cleaned)) < 1:
            return False
        return True

    def norm_text(self, value: Any) -> str:
        return str(value).lower().strip()

    def normalizar_mapeamento_usuario(
        self,
        mapeamento_colunas_usuario: Optional[Dict[str, str]],
        linha_original: Dict[str, Any],
    ) -> Dict[str, str]:
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

        key_hits = sum(1 for key in normalized.keys() if key in linha_keys)
        value_hits = sum(
            1 for value in normalized.values() if self.norm_text(value) in linha_keys
        )

        # Compatibilidade com mapeamentos antigos salvos como {campo_destino: coluna_origem}.
        if value_hits > key_hits:
            inverted: Dict[str, str] = {}
            for destination, source_col in normalized.items():
                source_norm = self.norm_text(source_col)
                if source_norm:
                    inverted[source_norm] = destination
            logger.info(
                "Mapeamento invertido detectado e normalizado: total=%s key_hits=%s value_hits=%s",
                len(normalized),
                key_hits,
                value_hits,
            )
            return inverted

        return normalized

    def coerce_region_bbox(
        self,
        region: Optional[List[float]],
        page_width: float,
        page_height: float,
    ) -> tuple[Optional[tuple[float, float, float, float]], Optional[str]]:
        if not region or len(region) != 4:
            return None, None

        try:
            x0, y0, x1, y1 = map(float, region)
        except Exception:
            return None, "invalid"

        raw_bbox = (x0, y0, x1, y1)
        normalized_mode = max(abs(value) for value in raw_bbox) <= 2.5

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
            return None, "invalid_after_clamp"

        return (x0, y0, x1, y1), ("normalized" if normalized_mode else "absolute")

    def token_looks_like_code(self, token: str) -> bool:
        value = token.strip().upper()
        if not value or len(value) > 32:
            return False
        if not re.fullmatch(r"[0-9A-Z./\-]+", value):
            return False
        digits = sum(1 for ch in value if ch.isdigit())
        letters = sum(1 for ch in value if ch.isalpha())
        if digits >= 2:
            return True
        # Ex.: A1, 1D, X3
        if digits == 1 and letters >= 1 and len(value) <= 6:
            return True
        # Ex.: D / E / LD / LE (lado direito/esquerdo em catalogos automotivos).
        if digits == 0 and value in {"D", "E", "LD", "LE", "RH", "LH", "DIR", "ESQ"}:
            return True
        return False

    def split_sku_nome_auto(self, value: str) -> tuple[Optional[str], Optional[str]]:
        tokens = [tok for tok in str(value).split() if tok]
        if not tokens:
            return None, None

        sku_tokens: List[str] = []
        nome_tokens: List[str] = []
        for tok in tokens:
            if tok in {"_", "-", "--", "|", "Â¦"}:
                continue
            has_lower = any(ch.isalpha() and ch.islower() for ch in tok)

            if not nome_tokens:
                if has_lower and sku_tokens:
                    nome_tokens.append(tok)
                    continue

                if self.token_looks_like_code(tok):
                    sku_tokens.append(tok)
                    continue

                if sku_tokens and any(ch.isalpha() for ch in tok):
                    nome_tokens.append(tok)
                    continue

                nome_tokens.append(tok)
            else:
                nome_tokens.append(tok)

        sku = " ".join(sku_tokens).strip() or None
        nome = " ".join(nome_tokens).strip() or None
        if nome:
            nome = re.sub(r"^[\W_]+", "", nome).strip() or None

        if not sku and nome:
            return None, nome
        if sku and not nome:
            return sku, None
        return sku, nome


_line_normalization_runtime = _LineNormalizationRuntime()


def _limpar_valor_extraido(valor: Any) -> Optional[str]:
    """Helper para limpar strings ou converter outros tipos para string, retornando None se vazio."""
    return _line_normalization_runtime.limpar_valor_extraido(valor)


def _valor_tem_conteudo_util(valor: Any) -> bool:
    """Retorna True para valores úteis (evita lixo de OCR como '!' ou '-')."""
    return _line_normalization_runtime.valor_tem_conteudo_util(valor)


def _norm_text(v: Any) -> str:
    return _line_normalization_runtime.norm_text(v)


def _normalizar_mapeamento_usuario(
    mapeamento_colunas_usuario: Optional[Dict[str, str]],
    linha_original: Dict[str, Any],
) -> Dict[str, str]:
    """Normaliza mapping do usuario e corrige formato invertido (campo->coluna)."""
    return _line_normalization_runtime.normalizar_mapeamento_usuario(
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        linha_original=linha_original,
    )


def _coerce_region_bbox(
    region: Optional[List[float]],
    page_width: float,
    page_height: float,
) -> tuple[Optional[tuple[float, float, float, float]], Optional[str]]:
    """Converte bbox para coordenada absoluta da pagina e faz clamp seguro."""
    return _line_normalization_runtime.coerce_region_bbox(
        region=region,
        page_width=page_width,
        page_height=page_height,
    )


def _token_looks_like_code(token: str) -> bool:
    """Heuristica para identificar token de codigo/SKU."""
    return _line_normalization_runtime.token_looks_like_code(token)


def _split_sku_nome_auto(value: str) -> tuple[Optional[str], Optional[str]]:
    """Divide um texto combinado em SKU e Nome Base quando possivel."""
    return _line_normalization_runtime.split_sku_nome_auto(value)

class _LineMappingWorkflow:
    """Workflow OO para padronizacao de linhas extraidas de catalogos."""

    _DEFAULT_MAPPING = {
        "nome_base": "nome_base",
        "sku_original": "sku_original",
        "ean_original": "ean_original",
        "preco_original": "preco_original",
        "descricao_original": "descricao_original",
        "categoria_original": "categoria_original",
        "imagem_url_original": "imagem_url_original",
        "nome": "nome_base",
        "produto": "nome_base",
        "item": "nome_base",
        "title": "nome_base",
        "titulo": "nome_base",
        "tA-tulo": "nome_base",
        "sku": "sku_original",
        "codigo": "sku_original",
        "ref": "sku_original",
        "referencia": "sku_original",
        "n fab": "auto:sku_nome",
        "n_fab": "auto:sku_nome",
        "no fab": "auto:sku_nome",
        "nfab": "auto:sku_nome",
        "fab": "auto:sku_nome",
        "marca": "marca",
        "fabricante": "marca",
        "brand": "marca",
        "categoria": "categoria_original",
        "category": "categoria_original",
        "descricao": "descricao_original",
        "description": "descricao_original",
        "ean": "ean_original",
        "gtin": "ean_original",
        "upc": "ean_original",
        "preco": "preco_original",
        "price": "preco_original",
        "valor": "preco_original",
        "n original": "attr:codigo_original",
        "n_original": "attr:codigo_original",
        "numero original": "attr:codigo_original",
        "cod original": "attr:codigo_original",
        "codigo original": "attr:codigo_original",
        "original": "attr:codigo_original",
        "aplicacao": "attr:aplicacao",
        "application": "attr:aplicacao",
        "material": "attr:material",
        "url_imagem": "imagem_url_original",
        "imagem": "imagem_url_original",
        "image_url": "imagem_url_original",
    }

    _ALIASES_DESTINO = {
        "sku": "sku_original",
        "ean": "ean_original",
        "preco": "preco_original",
        "price": "preco_original",
        "nome": "nome_base",
    }

    _FALLBACK_DYNAMIC_BY_COLUMN = {
        "aplicacao": "aplicacao",
        "application": "aplicacao",
        "material": "material",
        "n original": "codigo_original",
        "numero original": "codigo_original",
        "codigo original": "codigo_original",
        "original": "codigo_original",
    }

    _FALLBACK_SKU_COLUMNS = {"n fab", "no fab", "nfab", "fab"}

    def processar_linha_padronizada(
        self,
        linha_original: Dict[str, Any],
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Padroniza uma linha para campos de Produto, suportando atributos dinamicos."""

        produto_dados_padronizados: Dict[str, Any] = {}
        dados_brutos_nao_mapeados: Dict[str, Any] = {}
        dynamic_attributes: Dict[str, Any] = {}

        mapeamento_final = self._DEFAULT_MAPPING.copy()
        mapeamento_usuario_norm = _normalizar_mapeamento_usuario(
            mapeamento_colunas_usuario,
            linha_original,
        )
        if mapeamento_usuario_norm:
            mapeamento_final.update(mapeamento_usuario_norm)

        for nome_coluna_original, valor_original in linha_original.items():
            valor_limpo = _limpar_valor_extraido(valor_original)
            if valor_limpo is None:
                continue

            nome_coluna_norm = str(nome_coluna_original).lower().strip()
            nome_coluna_flat = re.sub(r"[^a-z0-9]+", " ", nome_coluna_norm).strip()
            campo_produto_destino = (
                mapeamento_final.get(nome_coluna_norm)
                or mapeamento_final.get(nome_coluna_flat)
            )
            if campo_produto_destino:
                campo_produto_destino = self._ALIASES_DESTINO.get(
                    str(campo_produto_destino).strip().lower(),
                    campo_produto_destino,
                )

            if campo_produto_destino:
                dest_str = str(campo_produto_destino)
                dest_norm = dest_str.strip().lower()
                if dest_norm in {"auto:sku_nome", "split:sku_nome", "sku_nome_auto", "sku+nome"}:
                    sku_auto, nome_auto = _split_sku_nome_auto(valor_limpo)
                    if sku_auto and not produto_dados_padronizados.get("sku_original"):
                        produto_dados_padronizados["sku_original"] = sku_auto
                    if nome_auto and not produto_dados_padronizados.get("nome_base"):
                        produto_dados_padronizados["nome_base"] = nome_auto
                    if not nome_auto:
                        dados_brutos_nao_mapeados[f"{nome_coluna_original}_raw"] = valor_limpo
                    continue

                if dest_str.startswith(("attr:", "dynamic:")):
                    attr_key = dest_str.split(":", 1)[1]
                    if attr_key:
                        dynamic_attributes[attr_key] = valor_limpo
                else:
                    if dest_norm == "nome_base":
                        sku_auto, nome_auto = _split_sku_nome_auto(valor_limpo)
                        if sku_auto and nome_auto:
                            if not produto_dados_padronizados.get("sku_original"):
                                produto_dados_padronizados["sku_original"] = sku_auto
                            if not produto_dados_padronizados.get("nome_base"):
                                produto_dados_padronizados["nome_base"] = nome_auto
                            continue
                    if dest_norm == "sku_original":
                        sku_auto, nome_auto = _split_sku_nome_auto(valor_limpo)
                        if sku_auto:
                            if not produto_dados_padronizados.get("sku_original"):
                                produto_dados_padronizados["sku_original"] = sku_auto
                            if nome_auto and not produto_dados_padronizados.get("nome_base"):
                                produto_dados_padronizados["nome_base"] = nome_auto
                            continue
                    if dest_norm == "descricao_original":
                        descricao_existente = _limpar_valor_extraido(
                            produto_dados_padronizados.get("descricao_original")
                        )
                        if descricao_existente:
                            partes_existentes = [
                                parte.strip()
                                for parte in str(descricao_existente).split("|")
                                if parte and parte.strip()
                            ]
                            if valor_limpo not in partes_existentes:
                                produto_dados_padronizados["descricao_original"] = (
                                    f"{descricao_existente} | {valor_limpo}"
                                )
                        else:
                            produto_dados_padronizados["descricao_original"] = valor_limpo
                        continue
                    if campo_produto_destino not in produto_dados_padronizados:
                        produto_dados_padronizados[campo_produto_destino] = valor_limpo
            else:
                if (
                    nome_coluna_flat in self._FALLBACK_SKU_COLUMNS
                    and not produto_dados_padronizados.get("sku_original")
                ):
                    produto_dados_padronizados["sku_original"] = valor_limpo
                    continue
                dynamic_key = self._FALLBACK_DYNAMIC_BY_COLUMN.get(nome_coluna_flat)
                if dynamic_key and dynamic_key not in dynamic_attributes:
                    dynamic_attributes[dynamic_key] = valor_limpo
                    continue
                dados_brutos_nao_mapeados[str(nome_coluna_original).strip()] = valor_limpo

        if not produto_dados_padronizados.get("nome_base") and not produto_dados_padronizados.get("sku_original"):
            # Quando existe mapeamento explicito do usuario, nao promovemos colunas nao mapeadas
            # para nome_base automaticamente (isso costuma virar ruido de OCR).
            if mapeamento_usuario_norm:
                return {
                    "motivo_descarte": "Faltam nome_base e sku_original",
                    "linha_original": linha_original,
                }
            if dados_brutos_nao_mapeados:
                primeiro_valor_util = next(
                    (v for v in dados_brutos_nao_mapeados.values() if _valor_tem_conteudo_util(v)),
                    None,
                )
                if primeiro_valor_util:
                    produto_dados_padronizados["nome_base"] = primeiro_valor_util
                else:
                    return {
                        "motivo_descarte": "Faltam nome_base e sku_original",
                        "linha_original": linha_original,
                    }
            else:
                return {
                    "motivo_descarte": "Faltam nome_base e sku_original",
                    "linha_original": linha_original,
                }

        if produto_dados_padronizados.get("nome_base") and not _valor_tem_conteudo_util(
            produto_dados_padronizados.get("nome_base")
        ):
            if not produto_dados_padronizados.get("sku_original"):
                return {"motivo_descarte": "nome_base sem conteúdo útil", "linha_original": linha_original}

        if dados_brutos_nao_mapeados:
            produto_dados_padronizados["dados_brutos_adicionais"] = dados_brutos_nao_mapeados

        if dynamic_attributes:
            produto_dados_padronizados["dynamic_attributes"] = dynamic_attributes

        return produto_dados_padronizados


_line_mapping_workflow = _LineMappingWorkflow()


def _processar_linha_padronizada(
    linha_original: Dict[str, Any],
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """Padroniza uma linha para campos de Produto, suportando atributos dinamicos."""
    return _line_mapping_workflow.processar_linha_padronizada(
        linha_original=linha_original,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
    )

class _TabularIngestionRuntime:
    """Runtime OO para ingestao de arquivos tabulares (Excel/CSV)."""

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        produtos_extraidos: List[Dict[str, Any]] = []
        try:
            xls = pd.ExcelFile(io.BytesIO(conteudo_arquivo))
            abas_processar = [sheet_name] if sheet_name else xls.sheet_names

            for aba in abas_processar:
                df = pd.read_excel(xls, sheet_name=aba)
                df.dropna(how="all", inplace=True)

                for _, linha_pandas in df.iterrows():
                    linha_dict_raw = {
                        col: val if pd.notna(val) else None
                        for col, val in linha_pandas.to_dict().items()
                    }
                    produto_padronizado = _processar_linha_padronizada(
                        linha_dict_raw,
                        mapeamento_colunas_usuario,
                    )
                    if produto_padronizado:
                        if product_type_id is not None:
                            produto_padronizado["product_type_id"] = product_type_id
                        produtos_extraidos.append(produto_padronizado)
            return produtos_extraidos
        except Exception as e:
            logger.error("Erro ao processar arquivo Excel: %s", e)
            return [{"erro_processamento_excel": f"Falha ao ler arquivo Excel: {str(e)}"}]

    async def processar_arquivo_csv(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        produtos_extraidos: List[Dict[str, Any]] = []
        try:
            # Detectar encoding usando chardet para lidar com diferentes formatos
            try:
                import chardet  # Lazy import para evitar dependencia desnecessaria em outros caminhos

                detection = chardet.detect(conteudo_arquivo)
                encoding_detectada = (detection.get("encoding") or "utf-8").lower()
            except Exception:
                encoding_detectada = "utf-8"

            if encoding_detectada.startswith("utf-8"):
                conteudo_str = conteudo_arquivo.decode("utf-8-sig", errors="replace")
            else:
                conteudo_str = conteudo_arquivo.decode(encoding_detectada, errors="replace")

            # Detectar delimitador usando csv.Sniffer em uma amostra de linhas
            linhas = conteudo_str.splitlines()
            sample = "\n".join(linhas[:5]) if linhas else conteudo_str
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
                delimitador_provavel = dialect.delimiter
            except Exception:
                delimitador_provavel = ","
                primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""
                if ";" in primeira_linha:
                    delimitador_provavel = ";"
                elif "\t" in primeira_linha:
                    delimitador_provavel = "\t"

            leitor_csv = csv.DictReader(
                io.StringIO(conteudo_str), delimiter=delimitador_provavel
            )
            for linha_dict_raw in leitor_csv:
                produto_padronizado = _processar_linha_padronizada(
                    linha_dict_raw,
                    mapeamento_colunas_usuario,
                )
                if produto_padronizado:
                    if product_type_id is not None:
                        produto_padronizado["product_type_id"] = product_type_id
                    produtos_extraidos.append(produto_padronizado)
            return produtos_extraidos
        except Exception as e:
            logger.error("Erro ao processar arquivo CSV: %s", e)
            return [{"erro_processamento_csv": f"Falha ao ler arquivo CSV: {str(e)}"}]


_tabular_ingestion_runtime = _TabularIngestionRuntime()


async def _processar_arquivo_excel_impl(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    sheet_name: Optional[str] = None,
    product_type_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return await _tabular_ingestion_runtime.processar_arquivo_excel(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        sheet_name=sheet_name,
        product_type_id=product_type_id,
    )


async def _processar_arquivo_csv_impl(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    product_type_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return await _tabular_ingestion_runtime.processar_arquivo_csv(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        product_type_id=product_type_id,
    )

async def _processar_arquivo_pdf_legacy_impl(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    usar_llm: bool = True,
    product_type_id: Optional[int] = None,
    pages: Optional[List[int]] = None,
    region: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    log_pdf: List[str] = []
    temp_pdf_path: Optional[Path] = None

    try:
        if region and len(region) == 4:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_pdf:
                tmp_pdf.write(conteudo_arquivo)
                temp_pdf_path = Path(tmp_pdf.name)
            logger.info(
                'processar_arquivo_pdf: modo regiao ativo temp_pdf=%s',
                temp_pdf_path,
            )

        pdf_obj: Optional[PdfPlumberPDF] = None
        try:
            pdf_obj = pdfplumber.open(io.BytesIO(conteudo_arquivo))
        except Exception as open_err:
            if _is_pdf_password_error(open_err):
                log_pdf.append(f'PDF protegido por senha: {str(open_err)}')
                return [
                    {
                        'erro_processamento_pdf': 'PDF protegido por senha; nao foi possivel abrir sem senha.',
                        'log_pdf': log_pdf,
                    }
                ]
            log_pdf.append(f'Falha ao abrir PDF: {str(open_err)}')
            return [
                {
                    'erro_processamento_pdf': f'Falha ao abrir PDF: {str(open_err)}',
                    'log_pdf': log_pdf,
                }
            ]

        if pdf_obj is None:
            log_pdf.append('Falha desconhecida ao abrir o PDF.')
            return [{'erro_processamento_pdf': 'Falha desconhecida ao abrir o PDF.', 'log_pdf': log_pdf}]

        with pdf_obj as pdf:
            total_pages = len(pdf.pages)
            page_list_to_process = list(pages) if pages else list(range(1, total_pages + 1))
            log_pdf.append(f'PDF com {total_pages} páginas.')
            logger.info(
                'processar_arquivo_pdf: total_paginas=%s paginas_processadas=%s region=%s',
                total_pages,
                page_list_to_process,
                region,
            )

            for page_num in page_list_to_process:
                if not (1 <= page_num <= total_pages):
                    continue

                page = pdf.pages[page_num - 1]
                page_to_process = page

                bbox_abs, bbox_mode = _coerce_region_bbox(
                    region,
                    float(page.width),
                    float(page.height),
                )
                if bbox_abs:
                    page_to_process = page.crop(bbox_abs)
                    log_pdf.append(
                        f'Página {page_num}: Aplicando recorte (crop) com bbox {bbox_abs} [modo={bbox_mode}].'
                    )
                    logger.info(
                        'processar_arquivo_pdf: page=%s bbox=%s mode=%s',
                        page_num,
                        bbox_abs,
                        bbox_mode,
                    )
                elif region:
                    log_pdf.append(
                        f'Página {page_num}: BBox inválido ({bbox_mode}); ignorando recorte.'
                    )

                if bbox_abs and temp_pdf_path:
                    try:
                        df_region = extract_data_from_pdf_region(
                            str(temp_pdf_path),
                            page_num,
                            list(bbox_abs),
                        )
                    except Exception as e_region:
                        log_pdf.append(
                            f'Página {page_num}: Falha no extrator de região: {str(e_region)}'
                        )
                        df_region = pd.DataFrame()

                    if not df_region.empty:
                        region_rows = df_region.to_dict(orient='records')
                        log_pdf.append(
                            f'Página {page_num}: Extração por região retornou {len(region_rows)} linhas.'
                        )
                        logger.info(
                            'processar_arquivo_pdf: page=%s region_rows=%s region_cols=%s',
                            page_num,
                            len(region_rows),
                            list(df_region.columns),
                        )
                        for row in region_rows:
                            produto_padronizado = _processar_linha_padronizada(
                                row,
                                mapeamento_colunas_usuario,
                            )
                            if produto_padronizado:
                                if product_type_id is not None:
                                    produto_padronizado['product_type_id'] = product_type_id
                                produtos_extraidos.append(produto_padronizado)
                        continue

                    log_pdf.append(
                        f'Página {page_num}: Extração por região não retornou linhas.'
                    )

                tables = page_to_process.extract_tables(
                    table_settings={
                        'vertical_strategy': 'lines',
                        'horizontal_strategy': 'lines',
                    }
                )

                if tables:
                    log_pdf.append(f'Página {page_num}: Encontradas {len(tables)} tabelas.')
                    for table_num, table_data in enumerate(tables):
                        if not table_data or len(table_data) < 2:
                            log_pdf.append(
                                f'Página {page_num}, Tabela {table_num+1}: Tabela vazia ou sem dados.'
                            )
                            continue

                        headers_raw = table_data[0]
                        headers = [
                            _limpar_valor_extraido(h) or f'coluna_vazia_{idx}'
                            for idx, h in enumerate(headers_raw)
                        ]

                        for row_idx, row_data in enumerate(table_data[1:]):
                            if len(row_data) != len(headers):
                                log_pdf.append(
                                    f'Página {page_num}, Tabela {table_num+1}, Linha {row_idx+1}: Incompatibilidade de colunas. Pulando.'
                                )
                                continue

                            linha_dict_raw = {
                                headers[col_idx]: cell_data
                                for col_idx, cell_data in enumerate(row_data)
                            }
                            produto_padronizado = _processar_linha_padronizada(
                                linha_dict_raw,
                                mapeamento_colunas_usuario,
                            )

                            if produto_padronizado:
                                if product_type_id is not None:
                                    produto_padronizado['product_type_id'] = product_type_id
                                produtos_extraidos.append(produto_padronizado)
                else:
                    log_pdf.append(f'Página {page_num}: Nenhuma tabela encontrada.')

            if not produtos_extraidos and page_list_to_process:
                log_pdf.append(
                    'Nenhum produto extraído de tabelas/região. Tentando extração de texto bruto.'
                )
                for page_num in page_list_to_process:
                    if not (1 <= page_num <= total_pages):
                        continue

                    page = pdf.pages[page_num - 1]
                    page_to_process = page
                    bbox_abs, _ = _coerce_region_bbox(
                        region,
                        float(page.width),
                        float(page.height),
                    )
                    if bbox_abs:
                        page_to_process = page.crop(bbox_abs)

                    page_text = page_to_process.extract_text(x_tolerance=2, y_tolerance=2)
                    if page_text and page_text.strip():
                        log_pdf.append(f'Página {page_num}: Texto extraído.')
                        texto_chave = f'texto_completo_pagina_{page_num}'

                        if usar_llm:
                            try:
                                dados_produto = await web_data_extractor_service.extrair_dados_produto_com_llm(
                                    page_text
                                )
                                if isinstance(dados_produto, dict):
                                    dados_produto['texto_bruto'] = page_text.strip()[:20000]
                                    if product_type_id is not None:
                                        dados_produto['product_type_id'] = product_type_id
                                    produtos_extraidos.append(dados_produto)
                                    log_pdf.append(
                                        f'Página {page_num}: Texto processado com LLM.'
                                    )
                                else:
                                    item = {
                                        'nome_base': f'Texto da página {page_num}',
                                        'dados_brutos_adicionais': {
                                            texto_chave: page_text.strip()[:20000]
                                        },
                                    }
                                    if product_type_id is not None:
                                        item['product_type_id'] = product_type_id
                                    produtos_extraidos.append(item)
                            except Exception as llm_e:
                                log_pdf.append(
                                    f'Página {page_num}: Erro ao processar com LLM: {str(llm_e)}'
                                )
                                item = {
                                    'nome_base': f'Conteúdo Bruto da Página {page_num}',
                                    'dados_brutos_adicionais': {
                                        texto_chave: page_text.strip()[:20000]
                                    },
                                }
                                if product_type_id is not None:
                                    item['product_type_id'] = product_type_id
                                produtos_extraidos.append(item)
                        else:
                            item = {
                                'nome_base': f'Conteúdo da Página {page_num}',
                                'dados_brutos_adicionais': {texto_chave: page_text.strip()[:20000]},
                            }
                            if product_type_id is not None:
                                item['product_type_id'] = product_type_id
                            produtos_extraidos.append(item)
                            log_pdf.append(f'Página {page_num}: Texto armazenado sem LLM.')
                    else:
                        log_pdf.append(
                            f'Página {page_num}: Nenhum texto extraível (pode ser imagem ou protegido).'
                        )

            if not produtos_extraidos:
                return [
                    {
                        'erro_processamento_pdf': 'Nenhum dado de produto pôde ser extraído do PDF (pode estar protegido, vazio ou somente imagem sem OCR).',
                        'log_pdf': log_pdf,
                    }
                ]

        logger.info(
            'processar_arquivo_pdf: concluido produtos_extraidos=%s paginas=%s',
            len(produtos_extraidos),
            len(page_list_to_process),
        )
        return produtos_extraidos

    except Exception as e:
        import traceback

        log_pdf.append(f'Erro crítico ao processar arquivo PDF: {str(e)}')
        logger.error('Erro ao processar arquivo PDF: %s', traceback.format_exc())
        return [
            {
                'erro_processamento_pdf': f'Falha crítica ao ler arquivo PDF: {str(e)}',
                'log_pdf': log_pdf,
            }
        ]
    finally:
        if temp_pdf_path and temp_pdf_path.exists():
            try:
                temp_pdf_path.unlink()
            except Exception:
                logger.debug(
                    'processar_arquivo_pdf: nao foi possivel remover temp_pdf=%s',
                    temp_pdf_path,
                )

class _PdfIngestionRuntime:
    """Runtime OO para ingestao de PDF."""

    def _append_produto(
        self,
        produtos_extraidos: List[Dict[str, Any]],
        produto_padronizado: Optional[Dict[str, Any]],
        product_type_id: Optional[int],
    ) -> None:
        if not produto_padronizado:
            return
        if product_type_id is not None:
            produto_padronizado["product_type_id"] = product_type_id
        produtos_extraidos.append(produto_padronizado)

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        produtos_extraidos: List[Dict[str, Any]] = []
        log_pdf: List[str] = []
        temp_pdf_path: Optional[Path] = None
        page_list_to_process: List[int] = []

        try:
            if region and len(region) == 4:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
                    tmp_pdf.write(conteudo_arquivo)
                    temp_pdf_path = Path(tmp_pdf.name)
                logger.info(
                    "processar_arquivo_pdf: modo regiao ativo temp_pdf=%s",
                    temp_pdf_path,
                )

            pdf_obj: Optional[PdfPlumberPDF] = None
            try:
                pdf_obj = pdfplumber.open(io.BytesIO(conteudo_arquivo))
            except Exception as open_err:
                if _is_pdf_password_error(open_err):
                    log_pdf.append(f"PDF protegido por senha: {str(open_err)}")
                    return [
                        {
                            "erro_processamento_pdf": "PDF protegido por senha; nao foi possivel abrir sem senha.",
                            "log_pdf": log_pdf,
                        }
                    ]
                log_pdf.append(f"Falha ao abrir PDF: {str(open_err)}")
                return [
                    {
                        "erro_processamento_pdf": f"Falha ao abrir PDF: {str(open_err)}",
                        "log_pdf": log_pdf,
                    }
                ]

            if pdf_obj is None:
                log_pdf.append("Falha desconhecida ao abrir o PDF.")
                return [
                    {
                        "erro_processamento_pdf": "Falha desconhecida ao abrir o PDF.",
                        "log_pdf": log_pdf,
                    }
                ]

            with pdf_obj as pdf:
                total_pages = len(pdf.pages)
                page_list_to_process = list(pages) if pages else list(
                    range(1, total_pages + 1)
                )
                log_pdf.append(f"PDF com {total_pages} paginas.")
                logger.info(
                    "processar_arquivo_pdf: total_paginas=%s paginas_processadas=%s region=%s",
                    total_pages,
                    page_list_to_process,
                    region,
                )

                for page_num in page_list_to_process:
                    if not (1 <= page_num <= total_pages):
                        continue

                    page = pdf.pages[page_num - 1]
                    page_to_process = page

                    bbox_abs, bbox_mode = _coerce_region_bbox(
                        region,
                        float(page.width),
                        float(page.height),
                    )
                    if bbox_abs:
                        page_to_process = page.crop(bbox_abs)
                        log_pdf.append(
                            f"Pagina {page_num}: Aplicando recorte (crop) com bbox {bbox_abs} [modo={bbox_mode}]."
                        )
                        logger.info(
                            "processar_arquivo_pdf: page=%s bbox=%s mode=%s",
                            page_num,
                            bbox_abs,
                            bbox_mode,
                        )
                    elif region:
                        log_pdf.append(
                            f"Pagina {page_num}: BBox invalido ({bbox_mode}); ignorando recorte."
                        )

                    if bbox_abs and temp_pdf_path:
                        try:
                            df_region = extract_data_from_pdf_region(
                                str(temp_pdf_path),
                                page_num,
                                list(bbox_abs),
                            )
                        except Exception as e_region:
                            log_pdf.append(
                                f"Pagina {page_num}: Falha no extrator de regiao: {str(e_region)}"
                            )
                            df_region = pd.DataFrame()

                        if not df_region.empty:
                            region_rows = df_region.to_dict(orient="records")
                            log_pdf.append(
                                f"Pagina {page_num}: Extracao por regiao retornou {len(region_rows)} linhas."
                            )
                            logger.info(
                                "processar_arquivo_pdf: page=%s region_rows=%s region_cols=%s",
                                page_num,
                                len(region_rows),
                                list(df_region.columns),
                            )
                            for row in region_rows:
                                self._append_produto(
                                    produtos_extraidos=produtos_extraidos,
                                    produto_padronizado=_processar_linha_padronizada(
                                        row, mapeamento_colunas_usuario
                                    ),
                                    product_type_id=product_type_id,
                                )
                            continue

                        log_pdf.append(
                            f"Pagina {page_num}: Extracao por regiao nao retornou linhas."
                        )

                    tables = page_to_process.extract_tables(
                        table_settings={
                            "vertical_strategy": "lines",
                            "horizontal_strategy": "lines",
                        }
                    )

                    if tables:
                        log_pdf.append(f"Pagina {page_num}: Encontradas {len(tables)} tabelas.")
                        for table_num, table_data in enumerate(tables):
                            if not table_data or len(table_data) < 2:
                                log_pdf.append(
                                    f"Pagina {page_num}, Tabela {table_num+1}: Tabela vazia ou sem dados."
                                )
                                continue

                            headers_raw = table_data[0]
                            headers = [
                                _limpar_valor_extraido(h) or f"coluna_vazia_{idx}"
                                for idx, h in enumerate(headers_raw)
                            ]

                            for row_idx, row_data in enumerate(table_data[1:]):
                                if len(row_data) != len(headers):
                                    log_pdf.append(
                                        f"Pagina {page_num}, Tabela {table_num+1}, Linha {row_idx+1}: Incompatibilidade de colunas. Pulando."
                                    )
                                    continue

                                linha_dict_raw = {
                                    headers[col_idx]: cell_data
                                    for col_idx, cell_data in enumerate(row_data)
                                }
                                self._append_produto(
                                    produtos_extraidos=produtos_extraidos,
                                    produto_padronizado=_processar_linha_padronizada(
                                        linha_dict_raw, mapeamento_colunas_usuario
                                    ),
                                    product_type_id=product_type_id,
                                )
                    else:
                        log_pdf.append(f"Pagina {page_num}: Nenhuma tabela encontrada.")

                if not produtos_extraidos and page_list_to_process:
                    log_pdf.append(
                        "Nenhum produto extraido de tabelas/regiao. Tentando extracao de texto bruto."
                    )
                    for page_num in page_list_to_process:
                        if not (1 <= page_num <= total_pages):
                            continue

                        page = pdf.pages[page_num - 1]
                        page_to_process = page
                        bbox_abs, _ = _coerce_region_bbox(
                            region,
                            float(page.width),
                            float(page.height),
                        )
                        if bbox_abs:
                            page_to_process = page.crop(bbox_abs)

                        page_text = page_to_process.extract_text(x_tolerance=2, y_tolerance=2)
                        if page_text and page_text.strip():
                            log_pdf.append(f"Pagina {page_num}: Texto extraido.")
                            texto_chave = f"texto_completo_pagina_{page_num}"

                            if usar_llm:
                                try:
                                    dados_produto = await web_data_extractor_service.extrair_dados_produto_com_llm(
                                        page_text
                                    )
                                    if isinstance(dados_produto, dict):
                                        dados_produto["texto_bruto"] = page_text.strip()[:20000]
                                        if product_type_id is not None:
                                            dados_produto["product_type_id"] = product_type_id
                                        produtos_extraidos.append(dados_produto)
                                        log_pdf.append(
                                            f"Pagina {page_num}: Texto processado com LLM."
                                        )
                                    else:
                                        item = {
                                            "nome_base": f"Texto da pagina {page_num}",
                                            "dados_brutos_adicionais": {
                                                texto_chave: page_text.strip()[:20000]
                                            },
                                        }
                                        if product_type_id is not None:
                                            item["product_type_id"] = product_type_id
                                        produtos_extraidos.append(item)
                                except Exception as llm_e:
                                    log_pdf.append(
                                        f"Pagina {page_num}: Erro ao processar com LLM: {str(llm_e)}"
                                    )
                                    item = {
                                        "nome_base": f"Conteudo Bruto da Pagina {page_num}",
                                        "dados_brutos_adicionais": {
                                            texto_chave: page_text.strip()[:20000]
                                        },
                                    }
                                    if product_type_id is not None:
                                        item["product_type_id"] = product_type_id
                                    produtos_extraidos.append(item)
                            else:
                                item = {
                                    "nome_base": f"Conteudo da Pagina {page_num}",
                                    "dados_brutos_adicionais": {
                                        texto_chave: page_text.strip()[:20000]
                                    },
                                }
                                if product_type_id is not None:
                                    item["product_type_id"] = product_type_id
                                produtos_extraidos.append(item)
                                log_pdf.append(f"Pagina {page_num}: Texto armazenado sem LLM.")
                        else:
                            log_pdf.append(
                                f"Pagina {page_num}: Nenhum texto extraivel (pode ser imagem ou protegido)."
                            )

                if not produtos_extraidos:
                    return [
                        {
                            "erro_processamento_pdf": "Nenhum dado de produto pode ser extraido do PDF (pode estar protegido, vazio ou somente imagem sem OCR).",
                            "log_pdf": log_pdf,
                        }
                    ]

            logger.info(
                "processar_arquivo_pdf: concluido produtos_extraidos=%s paginas=%s",
                len(produtos_extraidos),
                len(page_list_to_process),
            )
            return produtos_extraidos

        except Exception as e:
            import traceback

            log_pdf.append(f"Erro critico ao processar arquivo PDF: {str(e)}")
            logger.error("Erro ao processar arquivo PDF: %s", traceback.format_exc())
            return [
                {
                    "erro_processamento_pdf": f"Falha critica ao ler arquivo PDF: {str(e)}",
                    "log_pdf": log_pdf,
                }
            ]
        finally:
            if temp_pdf_path and temp_pdf_path.exists():
                try:
                    temp_pdf_path.unlink()
                except Exception:
                    logger.debug(
                        "processar_arquivo_pdf: nao foi possivel remover temp_pdf=%s",
                        temp_pdf_path,
                    )


_pdf_ingestion_runtime = _PdfIngestionRuntime()


async def _processar_arquivo_pdf_impl(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    usar_llm: bool = True,
    product_type_id: Optional[int] = None,
    pages: Optional[List[int]] = None,
    region: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    return await _pdf_ingestion_runtime.processar_arquivo_pdf(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        usar_llm=usar_llm,
        product_type_id=product_type_id,
        pages=pages,
        region=region,
    )


async def _preview_arquivo_excel_legacy_impl(

    conteudo_arquivo: bytes, max_rows: int = 5

) -> Dict[str, Any]:

    """Retorna cabeçalhos e linhas de amostra de um arquivo Excel."""

    try:

        df = pd.read_excel(io.BytesIO(conteudo_arquivo), sheet_name=0)

        headers = [str(col) for col in df.columns]

        sample_rows = df.head(max_rows).fillna("").to_dict(orient="records")

        return {"headers": headers, "sample_rows": sample_rows}

    except Exception as e:

        logger.error("Erro ao gerar preview de arquivo Excel: %s", e)

        return {"error": f"Falha ao ler arquivo Excel: {str(e)}"}





async def _preview_arquivo_csv_legacy_impl(

    conteudo_arquivo: bytes, max_rows: int = 5

) -> Dict[str, Any]:

    """Retorna cabeçalhos e linhas de amostra de um arquivo CSV."""

    try:

        try:

            conteudo_str = conteudo_arquivo.decode("utf-8-sig")

        except UnicodeDecodeError:

            conteudo_str = conteudo_arquivo.decode("latin-1")



        sample = conteudo_str[:1024]

        try:

            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])

            delimitador = dialect.delimiter

        except Exception:

            delimitador = ","

            primeira_linha = (

                conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""

            )

            if ";" in primeira_linha:

                delimitador = ";"

            elif "\t" in primeira_linha:

                delimitador = "\t"



        leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador)

        headers = leitor_csv.fieldnames or []

        sample_rows = []

        for i, row in enumerate(leitor_csv):

            if i >= max_rows:

                break

            sample_rows.append(row)

        return {"headers": headers, "sample_rows": sample_rows}

    except Exception as e:

        logger.error("Erro ao gerar preview de arquivo CSV: %s", e)

        return {"error": f"Falha ao ler arquivo CSV: {str(e)}"}





class _TabularPreviewRuntime:
    """Runtime OO para preview de planilhas/tabulares."""

    def _decode_csv_bytes(self, conteudo_arquivo: bytes) -> str:
        try:
            return conteudo_arquivo.decode("utf-8-sig")
        except UnicodeDecodeError:
            return conteudo_arquivo.decode("latin-1")

    def _detect_csv_delimiter(self, conteudo_str: str) -> str:
        sample = conteudo_str[:1024]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
            return dialect.delimiter
        except Exception:
            primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""
            if ";" in primeira_linha:
                return ";"
            if "\t" in primeira_linha:
                return "\t"
            return ","

    async def preview_arquivo_excel(
        self, conteudo_arquivo: bytes, max_rows: int = 5
    ) -> Dict[str, Any]:
        try:
            df = pd.read_excel(io.BytesIO(conteudo_arquivo), sheet_name=0)
            headers = [str(col) for col in df.columns]
            sample_rows = df.head(max_rows).fillna("").to_dict(orient="records")
            return {"headers": headers, "sample_rows": sample_rows}
        except Exception as e:
            logger.error("Erro ao gerar preview de arquivo Excel: %s", e)
            return {"error": f"Falha ao ler arquivo Excel: {str(e)}"}

    async def preview_arquivo_csv(
        self, conteudo_arquivo: bytes, max_rows: int = 5
    ) -> Dict[str, Any]:
        try:
            conteudo_str = self._decode_csv_bytes(conteudo_arquivo)
            delimitador = self._detect_csv_delimiter(conteudo_str)
            leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador)
            headers = leitor_csv.fieldnames or []
            sample_rows: List[Dict[str, Any]] = []
            for idx, row in enumerate(leitor_csv):
                if idx >= max_rows:
                    break
                sample_rows.append(row)
            return {"headers": headers, "sample_rows": sample_rows}
        except Exception as e:
            logger.error("Erro ao gerar preview de arquivo CSV: %s", e)
            return {"error": f"Falha ao ler arquivo CSV: {str(e)}"}


_tabular_preview_runtime = _TabularPreviewRuntime()


async def _preview_arquivo_excel_impl(
    conteudo_arquivo: bytes, max_rows: int = 5
) -> Dict[str, Any]:
    return await _tabular_preview_runtime.preview_arquivo_excel(
        conteudo_arquivo=conteudo_arquivo,
        max_rows=max_rows,
    )


async def _preview_arquivo_csv_impl(
    conteudo_arquivo: bytes, max_rows: int = 5
) -> Dict[str, Any]:
    return await _tabular_preview_runtime.preview_arquivo_csv(
        conteudo_arquivo=conteudo_arquivo,
        max_rows=max_rows,
    )


async def _preview_arquivo_pdf_legacy_impl(

    conteudo_arquivo: bytes,

    ext: str,

    start_page: int = 1,

    page_count: int = 1,

    dpi: int = 72,

) -> Dict[str, Any]:

    """Gera preview de um PDF com miniaturas e extração de texto.



    Parameters

    ----------

    conteudo_arquivo: bytes

        Conteúdo do arquivo PDF.

    ext: str

        Extensão do arquivo (mantida para compatibilidade).

    start_page: int, optional

        Página inicial (1-indexada) para geração do preview, por padrão ``1``.

    page_count: int, optional

        Quantidade de páginas a incluir no preview. ``0`` usa todas as páginas.

        Apenas as páginas nesse intervalo são analisadas para extrair texto,

        identificar tabelas e gerar imagens.

    dpi: int, optional

        Resolução usada ao converter as páginas em imagem. Padrão ``72``.



    As páginas são processadas em paralelo usando ``asyncio`` e a pool de

    ``ThreadPoolExecutor`` padrão do Python. O número de threads segue o limite

    ``min(32, os.cpu_count() + 4)`` a menos que outro executor seja

    configurado.

    """



    start = time.perf_counter()



    poppler_dir = os.getenv("POPPLER_PATH") or settings.POPPLER_PATH

    pdftoppm_path = (

        shutil.which("pdftoppm", path=poppler_dir)

        if poppler_dir

        else shutil.which("pdftoppm")

    )

    if pdftoppm_path is None:

        msg = (

            "Poppler (pdftoppm) executable not found. Install poppler-utils on Linux "

            "or set POPPLER_PATH to its directory."

        )

        logger.error(msg)

        return {"error": msg}



    try:

        with pdf_open(io.BytesIO(conteudo_arquivo)) as reader:

            num_pages = len(reader.pages)

        loop = asyncio.get_running_loop()

        if page_count == 0:

            page_count = num_pages

        end_page = min(start_page + page_count - 1, num_pages)

        pages_processed = end_page - start_page + 1



        preview: Dict[str, Any] = {

            "num_pages": num_pages,

            "table_pages": [],

            "sample_rows": {},

            "preview_images": [],

        }



        poppler_dir = os.getenv("POPPLER_PATH") or settings.POPPLER_PATH

        kwargs = {"poppler_path": poppler_dir} if poppler_dir else {}



        def _process_page(p: int) -> Dict[str, Any]:

            """Extract information for a single page."""

            with pdf_open(io.BytesIO(conteudo_arquivo)) as r:

                page = r.pages[p - 1]

                tables = page.extract_tables()

                result: Dict[str, Any] = {"page": p, "has_table": bool(tables)}



                text = page.extract_text() or ""

                image = convert_from_bytes(

                    conteudo_arquivo,

                    first_page=p,

                    last_page=p,

                    fmt="png",

                    dpi=dpi,

                    **kwargs,

                )[0]



                png_buf = io.BytesIO()

                image.save(png_buf, format="PNG")

                png_b64 = base64.b64encode(png_buf.getvalue())



                jpeg_buf = io.BytesIO()

                image.convert("RGB").save(

                    jpeg_buf,

                    format="JPEG",

                    optimize=True,

                    quality=70,

                )

                jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())



                if len(jpeg_b64) >= len(png_b64):

                    jpeg_buf = io.BytesIO()

                    image.convert("RGB").save(

                        jpeg_buf,

                        format="JPEG",

                        optimize=True,

                        quality=50,

                    )

                    jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())



                if len(jpeg_b64) < len(png_b64):

                    b64 = jpeg_b64.decode()

                    mime = "jpeg"

                else:

                    b64 = png_b64.decode()

                    mime = "png"



                snippet = "\n".join(text.splitlines()[:3])

                result.update(

                    {

                        "snippet": snippet,

                        "preview_image": {

                            "page": p,

                            "image": f"data:image/{mime};base64,{b64}",

                        },

                    }

                )



            return result



        executor = _preview_executor

        tasks = [

            loop.run_in_executor(executor, _process_page, p)

            for p in range(start_page, end_page + 1)

        ]

        results = await asyncio.gather(*tasks)



        for r in sorted(results, key=lambda x: x["page"]):

            if r.get("has_table"):

                preview["table_pages"].append(r["page"])

            if "snippet" in r:

                preview["sample_rows"][r["page"]] = r["snippet"]

            if "preview_image" in r:

                preview["preview_images"].append(r["preview_image"])



        duration = time.perf_counter() - start

        logger.info(

            "PDF preview processed %s page(s) in %.4f seconds", pages_processed, duration

        )

        return preview

    except Exception as e:

        logger.error("Erro ao gerar preview de arquivo PDF: %s", e)

        return {"error": f"Falha ao ler arquivo PDF: {str(e)}"}





class _PdfPreviewRuntime:
    """Runtime OO para preview de PDF."""

    def __init__(self, preview_executor: Optional[ThreadPoolExecutor] = None) -> None:
        self._preview_executor = preview_executor or _preview_executor

    def _resolve_poppler_path(self) -> Optional[str]:
        return os.getenv("POPPLER_PATH") or settings.POPPLER_PATH

    def _resolve_poppler_kwargs(self) -> Dict[str, Any]:
        poppler_dir = self._resolve_poppler_path()
        return {"poppler_path": poppler_dir} if poppler_dir else {}

    def _build_page_processor(
        self,
        conteudo_arquivo: bytes,
        dpi: int,
        kwargs: Dict[str, Any],
    ):
        def _process_page(page_number: int) -> Dict[str, Any]:
            with pdf_open(io.BytesIO(conteudo_arquivo)) as reader:
                page = reader.pages[page_number - 1]
                tables = page.extract_tables()
                result: Dict[str, Any] = {
                    "page": page_number,
                    "has_table": bool(tables),
                }

                text = page.extract_text() or ""
                image = convert_from_bytes(
                    conteudo_arquivo,
                    first_page=page_number,
                    last_page=page_number,
                    fmt="png",
                    dpi=dpi,
                    **kwargs,
                )[0]

                png_buf = io.BytesIO()
                image.save(png_buf, format="PNG")
                png_b64 = base64.b64encode(png_buf.getvalue())

                jpeg_buf = io.BytesIO()
                image.convert("RGB").save(
                    jpeg_buf,
                    format="JPEG",
                    optimize=True,
                    quality=70,
                )
                jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())

                if len(jpeg_b64) >= len(png_b64):
                    jpeg_buf = io.BytesIO()
                    image.convert("RGB").save(
                        jpeg_buf,
                        format="JPEG",
                        optimize=True,
                        quality=50,
                    )
                    jpeg_b64 = base64.b64encode(jpeg_buf.getvalue())

                if len(jpeg_b64) < len(png_b64):
                    b64 = jpeg_b64.decode()
                    mime = "jpeg"
                else:
                    b64 = png_b64.decode()
                    mime = "png"

                snippet = "\n".join(text.splitlines()[:3])
                result.update(
                    {
                        "snippet": snippet,
                        "preview_image": {
                            "page": page_number,
                            "image": f"data:image/{mime};base64,{b64}",
                        },
                    }
                )
            return result

        return _process_page

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        start = time.perf_counter()

        poppler_dir = self._resolve_poppler_path()
        pdftoppm_path = (
            shutil.which("pdftoppm", path=poppler_dir)
            if poppler_dir
            else shutil.which("pdftoppm")
        )
        if pdftoppm_path is None:
            msg = (
                "Poppler (pdftoppm) executable not found. Install poppler-utils on Linux "
                "or set POPPLER_PATH to its directory."
            )
            logger.error(msg)
            return {"error": msg}

        try:
            with pdf_open(io.BytesIO(conteudo_arquivo)) as reader:
                num_pages = len(reader.pages)

            loop = asyncio.get_running_loop()
            if page_count == 0:
                page_count = num_pages
            end_page = min(start_page + page_count - 1, num_pages)
            pages_processed = end_page - start_page + 1
            kwargs = self._resolve_poppler_kwargs()

            preview: Dict[str, Any] = {
                "num_pages": num_pages,
                "table_pages": [],
                "sample_rows": {},
                "preview_images": [],
            }

            process_page = self._build_page_processor(
                conteudo_arquivo=conteudo_arquivo,
                dpi=dpi,
                kwargs=kwargs,
            )
            tasks = [
                loop.run_in_executor(self._preview_executor, process_page, p)
                for p in range(start_page, end_page + 1)
            ]
            results = await asyncio.gather(*tasks)

            for result in sorted(results, key=lambda item: item["page"]):
                if result.get("has_table"):
                    preview["table_pages"].append(result["page"])
                if "snippet" in result:
                    preview["sample_rows"][result["page"]] = result["snippet"]
                if "preview_image" in result:
                    preview["preview_images"].append(result["preview_image"])

            duration = time.perf_counter() - start
            logger.info(
                "PDF preview processed %s page(s) in %.4f seconds",
                pages_processed,
                duration,
            )
            return preview
        except Exception as e:
            logger.error("Erro ao gerar preview de arquivo PDF: %s", e)
            return {"error": f"Falha ao ler arquivo PDF: {str(e)}"}


_pdf_preview_runtime = _PdfPreviewRuntime()


async def _preview_arquivo_pdf_impl(
    conteudo_arquivo: bytes,
    ext: str,
    start_page: int = 1,
    page_count: int = 1,
    dpi: int = 72,
) -> Dict[str, Any]:
    return await _pdf_preview_runtime.preview_arquivo_pdf(
        conteudo_arquivo=conteudo_arquivo,
        ext=ext,
        start_page=start_page,
        page_count=page_count,
        dpi=dpi,
    )


async def _gerar_preview_legacy_impl(

    conteudo_arquivo: bytes, ext: str, max_rows: int = 5

) -> Dict[str, Any]:

    """Despacha para a função de preview correta com base na extensão."""

    ext = ext.lower()

    if ext in [".xlsx", ".xls"]:

        return await preview_arquivo_excel(conteudo_arquivo, max_rows)

    if ext == ".csv":

        return await preview_arquivo_csv(conteudo_arquivo, max_rows)

    if ext == ".pdf":

        return await preview_arquivo_pdf(conteudo_arquivo, ext, 1, 1)

    raise ValueError("Formato de arquivo não suportado para preview")





class _PreviewDispatchRuntime:
    """Runtime OO para despacho de preview por extensao."""

    def __init__(
        self,
        tabular_preview_runtime: Optional[_TabularPreviewRuntime] = None,
        pdf_preview_runtime: Optional[_PdfPreviewRuntime] = None,
    ) -> None:
        self._tabular_preview_runtime = tabular_preview_runtime or _tabular_preview_runtime
        self._pdf_preview_runtime = pdf_preview_runtime or _pdf_preview_runtime

    async def gerar_preview(
        self, conteudo_arquivo: bytes, ext: str, max_rows: int = 5
    ) -> Dict[str, Any]:
        ext_norm = ext.lower()

        if ext_norm in [".xlsx", ".xls"]:
            return await self._tabular_preview_runtime.preview_arquivo_excel(
                conteudo_arquivo=conteudo_arquivo,
                max_rows=max_rows,
            )
        if ext_norm == ".csv":
            return await self._tabular_preview_runtime.preview_arquivo_csv(
                conteudo_arquivo=conteudo_arquivo,
                max_rows=max_rows,
            )
        if ext_norm == ".pdf":
            return await self._pdf_preview_runtime.preview_arquivo_pdf(
                conteudo_arquivo=conteudo_arquivo,
                ext=ext_norm,
                start_page=1,
                page_count=1,
            )

        raise ValueError("Formato de arquivo nao suportado para preview")


_preview_dispatch_runtime = _PreviewDispatchRuntime()


async def _gerar_preview_impl(
    conteudo_arquivo: bytes, ext: str, max_rows: int = 5
) -> Dict[str, Any]:
    return await _preview_dispatch_runtime.gerar_preview(
        conteudo_arquivo=conteudo_arquivo,
        ext=ext,
        max_rows=max_rows,
    )


async def _pdf_bytes_to_images_impl(

    conteudo_arquivo: bytes,

    max_pages: int = 1,

    start_page: int = 1,

    dpi: int = 200,

) -> List[str]:

    """Convert PDF bytes to base64 encoded PNG images."""



    loop = asyncio.get_running_loop()



    def _convert() -> List[str]:

        poppler_dir = os.getenv("POPPLER_PATH") or settings.POPPLER_PATH

        pdftoppm_path = (

            shutil.which("pdftoppm", path=poppler_dir)

            if poppler_dir

            else shutil.which("pdftoppm")

        )

        if pdftoppm_path is None:

            msg = (

                "Poppler (pdftoppm) executable not found. Install poppler-utils"

                "on Linux or set POPPLER_PATH to its directory."

            )

            logger.error(msg)

            raise RuntimeError(msg)

        kwargs = {"poppler_path": poppler_dir} if poppler_dir else {}



        last_page = None if max_pages == 0 else start_page + max_pages - 1



        images = convert_from_bytes(

            conteudo_arquivo,

            first_page=start_page,

            last_page=last_page,

            dpi=dpi,

            fmt="png",

            **kwargs,

        )



        result: List[str] = []

        for img in images:

            buf = io.BytesIO()

            img.save(buf, format="PNG")

            result.append(base64.b64encode(buf.getvalue()).decode())

        return result



    return await loop.run_in_executor(None, _convert)





def _pdf_pages_to_images_impl(db: Session, file: UploadFile, fornecedor_id: int, user_id: int, offset: int, limit: int) -> Dict[str, Any]:

    """

    Salva um ficheiro PDF, cria um registo na base de dados, e converte um lote de páginas em imagens.

    """

    upload_dir = _resolve_storage_path(Path(settings.UPLOAD_DIRECTORY))
    catalogs_dir = upload_dir / "catalogs"
    previews_dir = _resolve_storage_path(Path(settings.PREVIEW_DIRECTORY))

    

    catalogs_dir.mkdir(parents=True, exist_ok=True)

    previews_dir.mkdir(parents=True, exist_ok=True)



    poppler_dir = os.getenv("POPPLER_PATH") or settings.POPPLER_PATH

    pdftoppm_path = (

        shutil.which("pdftoppm", path=poppler_dir)

        if poppler_dir

        else shutil.which("pdftoppm")

    )

    if pdftoppm_path is None:

        msg = (

            "Poppler (pdftoppm) executable not found. Install poppler-utils on Linux "

            "or set POPPLER_PATH to its directory."

        )

        logger.error(msg)

        raise HTTPException(status_code=500, detail=msg)

    

    random_filename = f"{uuid.uuid4().hex}.pdf"

    file_location = catalogs_dir / random_filename



    # LÊ O FICHEIRO PARA A MEMÓRIA UMA ÚNICA VEZ

    try:

        content = file.file.read()

    except Exception as e:

        logger.error(f"Erro ao ler o conteúdo do ficheiro stream: {e}")

        raise HTTPException(status_code=500, detail="Erro interno ao ler o ficheiro.")

    finally:

        file.file.close()



    # Guarda o conteúdo lido no disco

    try:

        with open(file_location, "wb") as file_object:

            file_object.write(content)

    except Exception as e:

        logger.error(f"Erro ao salvar o arquivo carregado: {e}")

        raise HTTPException(status_code=500, detail="Erro interno ao salvar o arquivo.")



    # A chamada à função que já corrigimos

    import_file = crud_fornecedores.create_catalog_import_file(

        db=db,

        fornecedor_id=fornecedor_id,

        user_id=user_id,

        file_name=file.filename,

        original_file_path=str(file_location)

    )



    try:

        # USA O CONTEÚDO EM MEMÓRIA PARA OBTER O TOTAL DE PGINAS

        with pdfplumber.open(io.BytesIO(content)) as pdf:

            total_pages = len(pdf.pages)

    except Exception as e:

        logger.error(f"Erro ao ler PDF com pdfplumber: {e}")

        raise HTTPException(status_code=500, detail="Não foi possível ler o ficheiro PDF.")



    first_page_to_convert = offset + 1

    last_page_to_convert = min(offset + limit, total_pages)

    

    image_urls = []



    if first_page_to_convert <= last_page_to_convert:

        try:

            poppler_path = settings.POPPLER_PATH if settings.POPPLER_PATH else None

            

            # USA O CONTEÚDO EM MEMÓRIA PARA CONVERTER AS IMAGENS

            images = convert_from_bytes(

                content, # <-- MUDANÇA IMPORTANTE: usa o conteúdo em memória

                dpi=200,

                poppler_path=poppler_path,

                first_page=first_page_to_convert,

                last_page=last_page_to_convert

            )



            for i, image in enumerate(images):

                page_number = offset + i + 1

                image_filename = f"preview_{import_file.id}_{page_number}.png"

                image_path = previews_dir / image_filename

                image.save(image_path, "PNG")

                

                image_url = f"/static/previews/{image_filename}"

                image_urls.append(image_url)



        except Exception as e:

            logger.error(f"Falha ao converter PDF para imagens: {e}", exc_info=True)

            raise HTTPException(status_code=500, detail=f"Erro ao processar o PDF. Verifique se o Poppler está instalado corretamente.")



    return {"image_urls": image_urls, "total_pages": total_pages, "import_file_id": import_file.id}





def _get_file_path_by_id_impl(db: Session, file_id: str) -> str:

    """Retrieve the stored file path for a catalog import by ID."""

    import_file = (

        db.query(models.CatalogImportFile)

        .filter(models.CatalogImportFile.id == file_id)

        .first()

    )

    if not import_file:

        return None



    base_dir = os.path.join("Backend", "static", "uploads", "catalogs")

    return os.path.join(base_dir, import_file.stored_filename)





def _extract_data_from_pdf_region_impl(
    file_path: str, page_number: int, region: Optional[List[float]] = None
) -> pd.DataFrame:
    """Extract table-like data from a PDF region with OCR fallback."""

    started_at = time.perf_counter()

    def _make_unique(cols: List[Any]) -> List[str]:
        seen: Dict[str, int] = {}
        unique: List[str] = []
        for col in cols:
            base = _limpar_valor_extraido(col) or 'col'
            count = seen.get(base, 0)
            name = f"{base}_{count}" if count else base
            seen[base] = count + 1
            unique.append(name)
        return unique

    def _clean_df(df: pd.DataFrame) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        df = df.dropna(axis=1, how='all')
        df = df.dropna(axis=0, how='all')
        df = df.fillna('')
        return df

    def _median_int(values: List[int], default: int) -> int:
        if not values:
            return default
        sorted_values = sorted(values)
        mid = len(sorted_values) // 2
        if len(sorted_values) % 2 == 1:
            return int(sorted_values[mid])
        return int((sorted_values[mid - 1] + sorted_values[mid]) / 2)

    def _cluster_positions(x_values: List[int], tolerance: int) -> List[int]:
        clusters: List[int] = []
        for x in x_values:
            if not clusters or abs(x - clusters[-1]) > tolerance:
                clusters.append(x)
        return clusters

    def _normalize_ocr_snippet(text: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(text or ""))
        normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
        normalized = normalized.upper()
        normalized = re.sub(r"[^A-Z0-9 ]+", " ", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized

    def _header_field_for_text(text: str) -> Optional[str]:
        t = _normalize_ocr_snippet(text)
        if not t:
            return None
        if "FAB" in t:
            return "n_fab"
        if "ORIGINAL" in t:
            return "n_original"
        if "DESCR" in t:
            return "descricao"
        if "APLIC" in t:
            return "aplicacao"
        if "MATERIAL" in t or t in {"MAT", "MATER"}:
            return "material"
        return None

    def _detect_header_columns(
        merged_lines: List[List[Dict[str, Any]]]
    ) -> Optional[Dict[str, Any]]:
        if not merged_lines:
            return None

        ratio_by_field = {
            "n_fab": 0.04,
            "n_original": 0.20,
            "descricao": 0.38,
            "aplicacao": 0.67,
            "material": 0.88,
        }
        marker_pairs = [
            ("FAB", "n_fab"),
            ("ORIGINAL", "n_original"),
            ("DESCR", "descricao"),
            ("APLIC", "aplicacao"),
            ("MATERIAL", "material"),
        ]

        best: Optional[Dict[str, Any]] = None
        line_limit = min(len(merged_lines), 40)
        for line_idx in range(line_limit):
            line = merged_lines[line_idx]
            field_positions: Dict[str, int] = {}
            for seg in line:
                field = _header_field_for_text(seg.get("text", ""))
                if not field:
                    continue
                x0 = int(seg.get("x0", 0) or 0)
                if field not in field_positions or x0 < field_positions[field]:
                    field_positions[field] = x0

            # Fallback when OCR merges whole header in a single segment.
            line_norm = _normalize_ocr_snippet(" ".join(seg.get("text", "") for seg in line))
            marker_fields = [field for marker, field in marker_pairs if marker in line_norm]
            if len(field_positions) < 3 and len(marker_fields) >= 3:
                line_x0 = min(int(seg.get("x0", 0) or 0) for seg in line)
                line_x1 = max(int(seg.get("x1", seg.get("x0", 0)) or 0) for seg in line)
                line_width = max(1, line_x1 - line_x0)
                for field in marker_fields:
                    if field in field_positions:
                        continue
                    ratio = ratio_by_field.get(field, 0.5)
                    field_positions[field] = int(line_x0 + (line_width * ratio))

            if len(field_positions) < 3:
                continue

            ordered = sorted(field_positions.items(), key=lambda item: item[1])
            candidate = {
                "line_idx": line_idx,
                "headers": [name for name, _ in ordered],
                "bounds": [x for _, x in ordered],
                "score": len(field_positions),
            }
            if best is None:
                best = candidate
                continue
            if candidate["score"] > best["score"]:
                best = candidate
                continue
            if candidate["score"] == best["score"] and candidate["line_idx"] < best["line_idx"]:
                best = candidate

        return best

    def _is_header_like_row(text: str) -> bool:
        norm = _normalize_ocr_snippet(text)
        if not norm:
            return False
        markers = ("FAB", "ORIGINAL", "DESCR", "APLIC", "MATERIAL")
        hits = sum(1 for marker in markers if marker in norm)
        return hits >= 2

    def _filter_ocr_rows(raw_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered_rows: List[Dict[str, Any]] = []
        for row in raw_rows:
            cleaned_row = {k: (v or "").strip() for k, v in row.items()}
            non_empty_values = [v for v in cleaned_row.values() if v]
            if not non_empty_values:
                continue
            joined = " ".join(non_empty_values).strip()
            if _is_header_like_row(joined):
                continue
            if joined in {"-", "--", "!", "|", ":", ";", ".", ","}:
                continue
            alnum_count = len(re.sub(r"[^0-9A-Za-z\u00C0-\u00FF]", "", joined))
            if alnum_count < 2:
                continue
            if len(non_empty_values) == 1 and len(non_empty_values[0]) <= 1:
                continue
            filtered_rows.append(cleaned_row)
        return filtered_rows

    def _tables_to_df(tables: List[List[List[Any]]]) -> pd.DataFrame:
        rows: List[Dict[str, Any]] = []
        headers: List[str] = []
        for table in tables:
            if not table or len(table) < 2:
                continue
            headers = _make_unique(table[0])
            for row in table[1:]:
                row_fixed = list(row) + [''] * (len(headers) - len(row))
                row_fixed = row_fixed[: len(headers)]
                rows.append({headers[i]: row_fixed[i] for i in range(len(headers))})
        if rows and headers:
            return _clean_df(pd.DataFrame(rows, columns=headers))
        return pd.DataFrame()

    def _group_words_by_line_ids(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        buckets: Dict[tuple[int, int, int], List[Dict[str, Any]]] = {}
        for word in words:
            line_num = int(word.get('line', 0) or 0)
            if line_num <= 0:
                continue
            key = (
                int(word.get('block', 0) or 0),
                int(word.get('par', 0) or 0),
                line_num,
            )
            buckets.setdefault(key, []).append(word)
        lines = list(buckets.values())
        lines.sort(key=lambda line_words: min(item['y'] for item in line_words))
        return lines

    def _group_words_by_y(words: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        if not words:
            return []
        heights = [int(w.get('h', 0) or 0) for w in words if int(w.get('h', 0) or 0) > 0]
        tol_y = max(10, int(_median_int(heights, 12) * 0.8))
        words_sorted = sorted(words, key=lambda item: (item['y'], item['x']))
        lines_grouped: List[List[Dict[str, Any]]] = []
        for word in words_sorted:
            if lines_grouped and abs(word['y'] - lines_grouped[-1][0]['y']) <= tol_y:
                lines_grouped[-1].append(word)
            else:
                lines_grouped.append([word])
        return lines_grouped

    def _merge_words_in_line(line_words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not line_words:
            return []
        sorted_words = sorted(line_words, key=lambda item: item['x'])
        widths = [int(w.get('w', 0) or 0) for w in sorted_words if int(w.get('w', 0) or 0) > 0]
        gap_threshold = max(14, int(_median_int(widths, 8) * 1.8))
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
            if not seg_text:
                continue
            merged.append({'x0': int(seg['x0']), 'x1': int(seg['x1']), 'text': seg_text})
        return merged

    try:
        with pdfplumber.open(file_path) as pdf:
            if not (1 <= page_number <= len(pdf.pages)):
                raise ValueError(
                    f'Numero de pagina invalido: {page_number}. PDF tem {len(pdf.pages)} paginas.'
                )

            page = pdf.pages[page_number - 1]
            page_to_process = page
            if region and len(region) == 4:
                bbox = tuple(map(float, region))
                page_to_process = page.crop(bbox)

            logger.info(
                'extract_data_from_pdf_region: page=%s region=%s page_size=(%.1f,%.1f)',
                page_number,
                region,
                float(page_to_process.width),
                float(page_to_process.height),
            )

            # 1) Try structured table extraction first.
            table_settings_candidates = [
                {
                    'vertical_strategy': 'lines',
                    'horizontal_strategy': 'lines',
                    'snap_tolerance': 8,
                    'join_tolerance': 8,
                    'intersection_tolerance': 8,
                },
                {
                    'vertical_strategy': 'lines',
                    'horizontal_strategy': 'text',
                    'snap_tolerance': 5,
                },
            ]
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

            df_tables = _tables_to_df(tables)
            if not df_tables.empty:
                logger.info(
                    'extract_data_from_pdf_region: table rows=%s cols=%s elapsed=%.2fs',
                    len(df_tables.index),
                    len(df_tables.columns),
                    time.perf_counter() - started_at,
                )
                return df_tables

            # 2) Try plain text as fallback, but reject suspiciously fragmented output.
            text = page_to_process.extract_text()
            if text:
                lines = [line for line in text.strip().split('\n') if line.strip()]
                if len(lines) >= 2:
                    headers = _make_unique(lines[0].split())
                    rows_text: List[Dict[str, Any]] = []
                    for line in lines[1:]:
                        parts = line.split()
                        parts_fixed = parts + [''] * (len(headers) - len(parts))
                        parts_fixed = parts_fixed[: len(headers)]
                        rows_text.append({headers[i]: parts_fixed[i] for i in range(len(headers))})
                    df_text = _clean_df(pd.DataFrame(rows_text, columns=headers))
                    if not df_text.empty:
                        rows_count = len(df_text.index)
                        cols_count = len(df_text.columns)
                        if rows_count <= 1200 and cols_count <= 25:
                            logger.info(
                                'extract_data_from_pdf_region: text rows=%s cols=%s elapsed=%.2fs',
                                rows_count,
                                cols_count,
                                time.perf_counter() - started_at,
                            )
                            return df_text
                        logger.info(
                            'extract_data_from_pdf_region: text descartado por estrutura suspeita rows=%s cols=%s',
                            rows_count,
                            cols_count,
                        )

            # 3) OCR fallback for scanned/image pages.
            if not OCR_AVAILABLE or not OCR_EXEC_AVAILABLE:
                logger.debug('extract_data_from_pdf_region: OCR indisponivel para fallback.')
                return pd.DataFrame()

            try:
                ocr_render_start = time.perf_counter()
                dpi = int(os.getenv('OCR_REGION_DPI', '220'))
                page_img = page_to_process.to_image(resolution=dpi)
                buf = io.BytesIO()
                page_img.original.save(buf, format='PNG')
                img = Image.open(io.BytesIO(buf.getvalue()))

                # Light preprocessing keeps performance and helps OCR on colored backgrounds.
                from PIL import ImageEnhance, ImageOps

                img = img.convert('L')
                img = ImageOps.autocontrast(img)
                img = ImageEnhance.Contrast(img).enhance(1.6)
                logger.info(
                    'extract_data_from_pdf_region: OCR render ok dpi=%s elapsed=%.2fs',
                    dpi,
                    time.perf_counter() - ocr_render_start,
                )
            except Exception as e_img:
                logger.error('Falha ao renderizar regiao para OCR: %s', e_img)
                return pd.DataFrame()

            try:
                ocr_start = time.perf_counter()
                ocr_data = pytesseract.image_to_data(
                    img,
                    output_type=pytesseract.Output.DICT,
                    config='--psm 6 --oem 3',
                )
                logger.info(
                    'extract_data_from_pdf_region: OCR image_to_data concluido em %.2fs',
                    time.perf_counter() - ocr_start,
                )
            except Exception as e_ocr:
                global OCR_EXEC_FAILED_ONCE
                if not OCR_EXEC_FAILED_ONCE:
                    logger.error('Falha no OCR da regiao: %s', e_ocr)
                    OCR_EXEC_FAILED_ONCE = True
                else:
                    logger.debug(
                        'Falha no OCR da regiao (suprimida apos primeira ocorrencia): %s',
                        e_ocr,
                    )
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
                words.append(
                    {
                        'text': txt,
                        'x': int(ocr_data.get('left', [0])[i] or 0),
                        'y': int(ocr_data.get('top', [0])[i] or 0),
                        'w': int(ocr_data.get('width', [0])[i] or 0),
                        'h': int(ocr_data.get('height', [0])[i] or 0),
                        'block': int(ocr_data.get('block_num', [0])[i] or 0),
                        'par': int(ocr_data.get('par_num', [0])[i] or 0),
                        'line': int(ocr_data.get('line_num', [0])[i] or 0),
                    }
                )

            if not words:
                logger.info('OCR da regiao retornou vazio.')
                return pd.DataFrame()

            lines_grouped = _group_words_by_line_ids(words)
            if not lines_grouped:
                lines_grouped = _group_words_by_y(words)
            for line_words in lines_grouped:
                line_words.sort(key=lambda item: item['x'])

            merged_lines: List[List[Dict[str, Any]]] = []
            for line_words in lines_grouped:
                merged = _merge_words_in_line(line_words)
                if merged:
                    merged_lines.append(merged)
            if not merged_lines:
                logger.info('OCR da regiao nao produziu segmentos validos.')
                return pd.DataFrame()

            # 3.1) Header-guided OCR parsing (improves scanned catalogs with stable table header).
            header_guess = _detect_header_columns(merged_lines)
            if header_guess:
                guessed_headers: List[str] = header_guess["headers"]
                guessed_bounds: List[int] = header_guess["bounds"]
                row_start_idx = int(header_guess["line_idx"]) + 1
                logger.info(
                    "extract_data_from_pdf_region: OCR header detectado headers=%s line_idx=%s",
                    guessed_headers,
                    header_guess["line_idx"],
                )

                raw_rows_guided: List[Dict[str, Any]] = []
                for line in merged_lines[row_start_idx:]:
                    row = {header: "" for header in guessed_headers}
                    for seg in line:
                        idx_col = min(
                            range(len(guessed_bounds)),
                            key=lambda idx: abs(int(seg["x0"]) - guessed_bounds[idx]),
                        )
                        key = guessed_headers[idx_col]
                        row[key] = (f"{row[key]} {seg['text']}").strip() if row[key] else seg["text"]
                    raw_rows_guided.append(row)

                filtered_guided = _filter_ocr_rows(raw_rows_guided)
                if filtered_guided:
                    df_ocr_guided = _clean_df(pd.DataFrame(filtered_guided, columns=guessed_headers))
                    if not df_ocr_guided.empty:
                        logger.info(
                            "extract_data_from_pdf_region: OCR header-guided rows=%s cols=%s elapsed=%.2fs",
                            len(df_ocr_guided.index),
                            len(df_ocr_guided.columns),
                            time.perf_counter() - started_at,
                        )
                        return df_ocr_guided
                logger.info(
                    "extract_data_from_pdf_region: OCR header-guided sem linhas validas; fallback para cluster"
                )

            x_positions = sorted(int(seg['x0']) for line in merged_lines for seg in line)
            if not x_positions:
                logger.info('OCR da regiao nao produziu colunas validas.')
                return pd.DataFrame()

            max_x = max(int(word['x'] + word['w']) for word in words)
            region_px_width = max(1, max_x)
            tol_x = max(24, min(80, int(region_px_width / 35)))
            col_bounds = _cluster_positions(x_positions, tol_x)
            max_cols_target = max(8, int(os.getenv('OCR_MAX_COLUMNS', '16')))
            while len(col_bounds) > max_cols_target and tol_x < region_px_width:
                tol_x = int(tol_x * 1.35)
                col_bounds = _cluster_positions(x_positions, tol_x)

            headers = [f'col_{i}' for i in range(len(col_bounds))] or ['col_0']
            ocr_rows: List[Dict[str, Any]] = []
            for line in merged_lines:
                row = {header: '' for header in headers}
                for seg in line:
                    if col_bounds:
                        idx_col = min(
                            range(len(col_bounds)),
                            key=lambda idx: abs(int(seg['x0']) - col_bounds[idx]),
                        )
                    else:
                        idx_col = 0
                    key = headers[idx_col]
                    row[key] = (f"{row[key]} {seg['text']}").strip() if row[key] else seg['text']
                ocr_rows.append(row)

            filtered_rows = _filter_ocr_rows(ocr_rows)

            if not filtered_rows:
                logger.info('OCR da regiao retornou somente ruido.')
                return pd.DataFrame()

            df_ocr = _clean_df(pd.DataFrame(filtered_rows, columns=headers))
            logger.info(
                'extract_data_from_pdf_region: OCR rows=%s cols=%s words=%s lines=%s col_bounds=%s elapsed=%.2fs',
                len(df_ocr.index),
                len(df_ocr.columns),
                len(words),
                len(merged_lines),
                len(col_bounds),
                time.perf_counter() - started_at,
            )
            return df_ocr

    except Exception as e:
        logger.error('Erro ao processar o PDF na extracao da regiao: %s', e)
        return pd.DataFrame()

async def _extrair_pagina_pdf_impl(

    conteudo_pdf: bytes, page_number: int, region: Optional[List[float]] = None

) -> Dict[str, Any]:

    """Return an image, text and optional table extracted from a PDF page."""



    with pdfplumber.open(io.BytesIO(conteudo_pdf)) as pdf:

        if not (1 <= page_number <= len(pdf.pages)):

            raise ValueError(

                f"Número de página inválido: {page_number}. PDF tem {len(pdf.pages)} páginas."

            )



        page = pdf.pages[page_number - 1]

        page_to_process = page

        if region and len(region) == 4:

            bbox = tuple(map(float, region))

            page_to_process = page.crop(bbox)



        image = convert_from_bytes(

            conteudo_pdf,

            first_page=page_number,

            last_page=page_number,

            dpi=200,

            fmt="png",

        )[0]



        buf = io.BytesIO()

        image.save(buf, format="PNG")

        image_b64 = base64.b64encode(buf.getvalue()).decode()



        text = page_to_process.extract_text() or ""



    # Use a real temporary file (portable across Linux/Windows).
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(conteudo_pdf)
        tmp_path = Path(tmp_file.name)

    try:
        df = extract_data_from_pdf_region(str(tmp_path), page_number, region)
        if not df.empty:
            table = [list(df.columns)] + df.values.tolist()
        else:
            table = None
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass



    return {"image": f"data:image/png;base64,{image_b64}", "text": text, "table": table}









async def _process_pdf_job_impl(
    job_id: int, pdf_path: str, start_page: int = 1, mapping: Optional[Dict[str, str]] = None
) -> None:
    """Process remaining pages of a PDF catalog import job."""

    db: Optional[Session] = None
    catalog_file: Optional[models.CatalogImportFile] = None
    try:
        db = SessionLocal()
        catalog_file = db.query(models.CatalogImportFile).filter_by(id=job_id).first()
        if not catalog_file:
            logger.error("CatalogImportFile %s not found", job_id)
            return

        logger.info("process_pdf_job: start job_id=%s path=%s start_page=%s mapping_keys=%s", job_id, pdf_path, start_page, list(mapping.keys()) if mapping else [])

        with pdfplumber.open(pdf_path) as pdf:
            total_pages = len(pdf.pages)

        catalog_file.status = "PROCESSING"
        catalog_file.total_pages = total_pages
        catalog_file.pages_processed = 0
        db.commit()

        products: List[Dict[str, Any]] = []

        for page in range(start_page, total_pages + 1):
            try:
                raw_page = extract_data_from_single_page(pdf_path, page)
                page_rows = raw_page.get("rows", []) if isinstance(raw_page, dict) else []
                logger.info(
                    "process_pdf_job: page=%s raw_rows_count=%s headers=%s",
                    page,
                    len(page_rows),
                    raw_page.get("headers") if isinstance(raw_page, dict) else None,
                )
            except Exception as e:  # pragma: no cover - robustness
                logger.error("Erro ao extrair dados da pagina %s: %s", page, e)
                continue

            for row in page_rows:
                produto = _processar_linha_padronizada(row, mapping)
                if produto:
                    products.append(produto)

            logger.info("process_pdf_job: page=%s products_accumulated=%s", page, len(products))

            catalog_file.pages_processed += 1
            if catalog_file.pages_processed % 5 == 0:
                db.commit()

        catalog_file.result_summary = {"products": products}
        catalog_file.status = "PENDING_REVIEW"
        db.commit()
        logger.info("process_pdf_job: done job_id=%s status=%s products=%s pages=%s", job_id, catalog_file.status, len(products), catalog_file.pages_processed)
    except Exception:
        logger.exception("Erro ao processar job de PDF")
        if db and catalog_file:
            catalog_file.status = "FAILED"
            db.commit()
    finally:
        if db:
            db.close()


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

            if not (1 <= page_number <= len(pdf.pages)):

                raise ValueError(

                    f"Número de página inválido: {page_number}. PDF tem {len(pdf.pages)} páginas."

                )



            page = pdf.pages[page_number - 1]

            tables = page.extract_tables(

                table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"}

            )



            if tables:

                for table in tables:

                    if table and len(table) >= 2:

                        headers = [str(h or "").strip() for h in table[0]]

                        rows = [[str(c or "").strip() for c in r] for r in table[1:]]

                        if any(any(cell for cell in r) for r in rows):

                            return {"headers": headers, "rows": rows}



            text = page.extract_text() or ""

            lines = [l.strip() for l in text.splitlines() if l.strip()]

            if len(lines) >= 2:

                headers = lines[0].split()

                rows = [ln.split() for ln in lines[1:]]

                if rows:

                    return {"headers": headers, "rows": rows}

    except Exception as e:  # pragma: no cover - runtime logging

        logger.error("Erro ao extrair com pdfplumber: %s", e)



    try:  # OCR fallback

        import fitz  # type: ignore

        import pytesseract  # type: ignore

        from PIL import Image  # type: ignore



        doc = fitz.open(file_path)

        if not (1 <= page_number <= doc.page_count):

            raise ValueError(

                f"Número de página inválido: {page_number}. PDF tem {doc.page_count} páginas."

            )



        page = doc.load_page(page_number - 1)

        pix = page.get_pixmap(dpi=300)

        img = Image.open(io.BytesIO(pix.tobytes()))



        text = pytesseract.image_to_string(img)

        lines = [l.strip() for l in text.splitlines() if l.strip()]

        if lines:

            headers = lines[0].split()

            rows = [ln.split() for ln in lines[1:]]

    except Exception as e:  # pragma: no cover - optional dependency might be missing

        logger.error("Erro ao executar OCR da página do PDF: %s", e)

    finally:

        try:

            doc.close()  # type: ignore

        except Exception:

            pass



    return {"headers": headers, "rows": rows}





def _generate_pdf_page_images_impl(file_path: str, file_id: str) -> List[str]:

    """Render pages of a PDF into PNG images.



    Parameters

    ----------

    file_path: str

        Absolute path to the PDF file to render.

    file_id: str

        Identifier used to build the output directory name.



    Returns

    -------

    List[str]

        Relative URLs for the generated preview images.

    """



    try:

        import fitz  # PyMuPDF

    except Exception as e:  # pragma: no cover - library might be missing

        logger.error("PyMuPDF (fitz) not available: %s", e)

        raise



    output_dir = Path("Backend") / "static" / "previews" / str(file_id)

    output_dir.mkdir(parents=True, exist_ok=True)



    urls: List[str] = []



    with fitz.open(file_path) as doc:

        page_count = min(len(doc), 20)

        for i in range(page_count):

            page = doc.load_page(i)

            pix = page.get_pixmap(dpi=150)

            image_path = output_dir / f"page-{i + 1}.png"

            pix.save(str(image_path))

            url = f"/static/previews/{file_id}/page-{i + 1}.png"

            urls.append(url)



    return urls



def _extract_pdf_region_image_impl(file_path: str, page_number: int, region: Optional[List[float]] = None, dpi: int = 300) -> bytes:

    """Return PNG bytes for a specific region of a PDF page."""

    logger.debug("Recebendo coordenadas: %s", region)

    with pdfplumber.open(file_path) as pdf:

        if not (1 <= page_number <= len(pdf.pages)):

            raise ValueError(

                f"Número de página inválido: {page_number}. PDF tem {len(pdf.pages)} páginas."

            )

        page = pdf.pages[page_number - 1]

        page_to_process = page

        if region and len(region) == 4:

            logger.debug("Recortando imagem")

            bbox = tuple(map(float, region))

            page_to_process = page.crop(bbox)

        page_image = page_to_process.to_image(resolution=dpi)

        buf = io.BytesIO()

        page_image.original.save(buf, format="PNG")

        return buf.getvalue()





def _parse_annotation_to_dataframe_impl(annotation: object, vertical_tolerance: int = 5) -> pd.DataFrame:

    """Parse OCR annotation with geometry into a structured DataFrame."""

    logger.debug("Iniciando análise do texto")

    try:

        words: List[Dict[str, Any]] = []

        for page in getattr(annotation, "pages", []):

            for block in getattr(page, "blocks", []):

                for paragraph in getattr(block, "paragraphs", []):

                    for word in getattr(paragraph, "words", []):

                        text = "".join([s.text for s in getattr(word, "symbols", [])])

                        vertices = getattr(word.bounding_box, "vertices", [])

                        xs = [v.x for v in vertices]

                        ys = [v.y for v in vertices]

                        x_min = min(xs) if xs else 0

                        y_min = min(ys) if ys else 0

                        words.append({"text": text, "x": x_min, "y": y_min})

        if not words:

            return pd.DataFrame()

        words.sort(key=lambda w: w["y"])

        lines: List[List[Dict[str, Any]]] = []

        for w in words:

            if lines and abs(w["y"] - lines[-1][0]["y"]) <= vertical_tolerance:

                lines[-1].append(w)

            else:

                lines.append([w])

        for line in lines:

            line.sort(key=lambda w: w["x"])

        x_positions = sorted({w["x"] for line in lines for w in line})

        column_boundaries: List[int] = []

        x_tol = 20

        for x in x_positions:

            if not column_boundaries or abs(x - column_boundaries[-1]) > x_tol:

                column_boundaries.append(x)

        rows: List[List[str]] = []

        for line in lines:

            row = ["" for _ in column_boundaries]

            for w in line:

                col_idx = min(range(len(column_boundaries)), key=lambda i: abs(w["x"] - column_boundaries[i]))

                row[col_idx] = (row[col_idx] + " " + w["text"]).strip()

            rows.append(row)

        columns = [f"col_{i+1}" for i in range(len(column_boundaries))]

        return pd.DataFrame(rows, columns=columns)

    except Exception as e:

        logger.exception("Falha ao processar texto extraído")

        raise HTTPException(status_code=500, detail="Ocorreu um erro durante a extração de dados.") from e



class _CatalogStorageWorkflow:
    """Workflow OO para operacoes de storage de catalogo."""

    async def save_uploaded_catalog(
        self, file: UploadFile, fornecedor_id: Optional[int] = None
    ) -> models.CatalogImportFile:
        return await _save_uploaded_catalog_impl(
            file=file,
            fornecedor_id=fornecedor_id,
        )

    def delete_catalog_file(self, stored_filename: str) -> None:
        _delete_catalog_file_impl(stored_filename)

    def get_file_path_by_id(self, db: Session, file_id: str) -> str:
        return _get_file_path_by_id_impl(db=db, file_id=file_id)


_catalog_storage_workflow = _CatalogStorageWorkflow()


async def save_uploaded_catalog(
    file: UploadFile, fornecedor_id: Optional[int] = None
) -> models.CatalogImportFile:
    return await _catalog_storage_workflow.save_uploaded_catalog(
        file=file,
        fornecedor_id=fornecedor_id,
    )


def delete_catalog_file(stored_filename: str) -> None:
    _catalog_storage_workflow.delete_catalog_file(stored_filename)


def get_file_path_by_id(db: Session, file_id: str) -> str:
    return _catalog_storage_workflow.get_file_path_by_id(db=db, file_id=file_id)


class _TabularIngestionWorkflow:
    """Workflow OO para ingestão de arquivos tabulares (Excel/CSV)."""

    async def processar_arquivo_excel(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        sheet_name: Optional[str] = None,
        product_type_id: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        return await _processar_arquivo_excel_impl(
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
        return await _processar_arquivo_csv_impl(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            product_type_id=product_type_id,
        )


_tabular_ingestion_workflow = _TabularIngestionWorkflow()


async def processar_arquivo_excel(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    sheet_name: Optional[str] = None,
    product_type_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return await _tabular_ingestion_workflow.processar_arquivo_excel(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        sheet_name=sheet_name,
        product_type_id=product_type_id,
    )


async def processar_arquivo_csv(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    product_type_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    return await _tabular_ingestion_workflow.processar_arquivo_csv(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        product_type_id=product_type_id,
    )


class _TabularPreviewWorkflow:
    """Workflow OO para preview tabular (Excel/CSV)."""

    async def preview_arquivo_excel(
        self, conteudo_arquivo: bytes, max_rows: int = 5
    ) -> Dict[str, Any]:
        return await _preview_arquivo_excel_impl(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )

    async def preview_arquivo_csv(
        self, conteudo_arquivo: bytes, max_rows: int = 5
    ) -> Dict[str, Any]:
        return await _preview_arquivo_csv_impl(
            conteudo_arquivo=conteudo_arquivo,
            max_rows=max_rows,
        )


_tabular_preview_workflow = _TabularPreviewWorkflow()


async def preview_arquivo_excel(
    conteudo_arquivo: bytes, max_rows: int = 5
) -> Dict[str, Any]:
    return await _tabular_preview_workflow.preview_arquivo_excel(
        conteudo_arquivo=conteudo_arquivo,
        max_rows=max_rows,
    )


async def preview_arquivo_csv(
    conteudo_arquivo: bytes, max_rows: int = 5
) -> Dict[str, Any]:
    return await _tabular_preview_workflow.preview_arquivo_csv(
        conteudo_arquivo=conteudo_arquivo,
        max_rows=max_rows,
    )


class _PdfAssetWorkflow:
    """Workflow OO para utilitarios de imagem/regiao de PDF."""

    async def pdf_bytes_to_images(
        self,
        conteudo_arquivo: bytes,
        max_pages: int = 1,
        start_page: int = 1,
        dpi: int = 200,
    ) -> List[str]:
        return await _pdf_bytes_to_images_impl(
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
        return _pdf_pages_to_images_impl(
            db=db,
            file=file,
            fornecedor_id=fornecedor_id,
            user_id=user_id,
            offset=offset,
            limit=limit,
        )

    async def extrair_pagina_pdf(
        self, conteudo_pdf: bytes, page_number: int, region: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        return await _extrair_pagina_pdf_impl(
            conteudo_pdf=conteudo_pdf,
            page_number=page_number,
            region=region,
        )

    def generate_pdf_page_images(self, file_path: str, file_id: str) -> List[str]:
        return _generate_pdf_page_images_impl(file_path=file_path, file_id=file_id)

    def extract_pdf_region_image(
        self,
        file_path: str,
        page_number: int,
        region: Optional[List[float]] = None,
        dpi: int = 300,
    ) -> bytes:
        return _extract_pdf_region_image_impl(
            file_path=file_path,
            page_number=page_number,
            region=region,
            dpi=dpi,
        )

    def parse_annotation_to_dataframe(
        self, annotation: object, vertical_tolerance: int = 5
    ) -> pd.DataFrame:
        return _parse_annotation_to_dataframe_impl(
            annotation=annotation,
            vertical_tolerance=vertical_tolerance,
        )


_pdf_asset_workflow = _PdfAssetWorkflow()


async def pdf_bytes_to_images(
    conteudo_arquivo: bytes,
    max_pages: int = 1,
    start_page: int = 1,
    dpi: int = 200,
) -> List[str]:
    return await _pdf_asset_workflow.pdf_bytes_to_images(
        conteudo_arquivo=conteudo_arquivo,
        max_pages=max_pages,
        start_page=start_page,
        dpi=dpi,
    )


def pdf_pages_to_images(
    db: Session,
    file: UploadFile,
    fornecedor_id: int,
    user_id: int,
    offset: int,
    limit: int,
) -> Dict[str, Any]:
    return _pdf_asset_workflow.pdf_pages_to_images(
        db=db,
        file=file,
        fornecedor_id=fornecedor_id,
        user_id=user_id,
        offset=offset,
        limit=limit,
    )


async def extrair_pagina_pdf(
    conteudo_pdf: bytes, page_number: int, region: Optional[List[float]] = None
) -> Dict[str, Any]:
    return await _pdf_asset_workflow.extrair_pagina_pdf(
        conteudo_pdf=conteudo_pdf,
        page_number=page_number,
        region=region,
    )


def generate_pdf_page_images(file_path: str, file_id: str) -> List[str]:
    return _pdf_asset_workflow.generate_pdf_page_images(
        file_path=file_path,
        file_id=file_id,
    )


def extract_pdf_region_image(
    file_path: str,
    page_number: int,
    region: Optional[List[float]] = None,
    dpi: int = 300,
) -> bytes:
    return _pdf_asset_workflow.extract_pdf_region_image(
        file_path=file_path,
        page_number=page_number,
        region=region,
        dpi=dpi,
    )


def parse_annotation_to_dataframe(
    annotation: object, vertical_tolerance: int = 5
) -> pd.DataFrame:
    return _pdf_asset_workflow.parse_annotation_to_dataframe(
        annotation=annotation,
        vertical_tolerance=vertical_tolerance,
    )


class _PdfProcessingWorkflow:
    """Workflow OO para processamento e preview de PDF."""

    async def processar_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
        usar_llm: bool = True,
        product_type_id: Optional[int] = None,
        pages: Optional[List[int]] = None,
        region: Optional[List[float]] = None,
    ) -> List[Dict[str, Any]]:
        return await _processar_arquivo_pdf_impl(
            conteudo_arquivo=conteudo_arquivo,
            mapeamento_colunas_usuario=mapeamento_colunas_usuario,
            usar_llm=usar_llm,
            product_type_id=product_type_id,
            pages=pages,
            region=region,
        )

    async def preview_arquivo_pdf(
        self,
        conteudo_arquivo: bytes,
        ext: str,
        start_page: int = 1,
        page_count: int = 1,
        dpi: int = 72,
    ) -> Dict[str, Any]:
        return await _preview_arquivo_pdf_impl(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            start_page=start_page,
            page_count=page_count,
            dpi=dpi,
        )

    async def gerar_preview(
        self, conteudo_arquivo: bytes, ext: str, max_rows: int = 5
    ) -> Dict[str, Any]:
        return await _gerar_preview_impl(
            conteudo_arquivo=conteudo_arquivo,
            ext=ext,
            max_rows=max_rows,
        )

    def extract_data_from_pdf_region(
        self, file_path: str, page_number: int, region: Optional[List[float]] = None
    ) -> pd.DataFrame:
        return _extract_data_from_pdf_region_impl(
            file_path=file_path,
            page_number=page_number,
            region=region,
        )


_pdf_processing_workflow = _PdfProcessingWorkflow()


async def processar_arquivo_pdf(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    usar_llm: bool = True,
    product_type_id: Optional[int] = None,
    pages: Optional[List[int]] = None,
    region: Optional[List[float]] = None,
) -> List[Dict[str, Any]]:
    return await _pdf_processing_workflow.processar_arquivo_pdf(
        conteudo_arquivo=conteudo_arquivo,
        mapeamento_colunas_usuario=mapeamento_colunas_usuario,
        usar_llm=usar_llm,
        product_type_id=product_type_id,
        pages=pages,
        region=region,
    )


async def preview_arquivo_pdf(
    conteudo_arquivo: bytes,
    ext: str,
    start_page: int = 1,
    page_count: int = 1,
    dpi: int = 72,
) -> Dict[str, Any]:
    return await _pdf_processing_workflow.preview_arquivo_pdf(
        conteudo_arquivo=conteudo_arquivo,
        ext=ext,
        start_page=start_page,
        page_count=page_count,
        dpi=dpi,
    )


async def gerar_preview(
    conteudo_arquivo: bytes, ext: str, max_rows: int = 5
) -> Dict[str, Any]:
    return await _pdf_processing_workflow.gerar_preview(
        conteudo_arquivo=conteudo_arquivo,
        ext=ext,
        max_rows=max_rows,
    )


def extract_data_from_pdf_region(
    file_path: str, page_number: int, region: Optional[List[float]] = None
) -> pd.DataFrame:
    return _pdf_processing_workflow.extract_data_from_pdf_region(
        file_path=file_path,
        page_number=page_number,
        region=region,
    )


class _PdfJobWorkflow:
    """Workflow OO para processamento assíncrono de jobs de PDF."""

    async def process_pdf_job(
        self,
        job_id: int,
        pdf_path: str,
        start_page: int = 1,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        await _process_pdf_job_impl(
            job_id=job_id,
            pdf_path=pdf_path,
            start_page=start_page,
            mapping=mapping,
        )

    def extract_data_from_single_page(
        self, file_path: str, page_number: int
    ) -> Dict[str, Any]:
        return _extract_data_from_single_page_impl(
            file_path=file_path,
            page_number=page_number,
        )


_pdf_job_workflow = _PdfJobWorkflow()


async def process_pdf_job(
    job_id: int, pdf_path: str, start_page: int = 1, mapping: Optional[Dict[str, str]] = None
) -> None:
    await _pdf_job_workflow.process_pdf_job(
        job_id=job_id,
        pdf_path=pdf_path,
        start_page=start_page,
        mapping=mapping,
    )


def extract_data_from_single_page(file_path: str, page_number: int) -> Dict[str, Any]:
    return _pdf_job_workflow.extract_data_from_single_page(
        file_path=file_path,
        page_number=page_number,
    )


class FileProcessingLegacyService:
    """OO compatibility layer for legacy file processing module."""

    async def save_uploaded_catalog(self, *args: Any, **kwargs: Any):
        return await save_uploaded_catalog(*args, **kwargs)

    def delete_catalog_file(self, *args: Any, **kwargs: Any):
        return delete_catalog_file(*args, **kwargs)

    async def processar_arquivo_excel(self, *args: Any, **kwargs: Any):
        return await processar_arquivo_excel(*args, **kwargs)

    async def processar_arquivo_csv(self, *args: Any, **kwargs: Any):
        return await processar_arquivo_csv(*args, **kwargs)

    async def processar_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await processar_arquivo_pdf(*args, **kwargs)

    async def preview_arquivo_pdf(self, *args: Any, **kwargs: Any):
        return await preview_arquivo_pdf(*args, **kwargs)

    async def gerar_preview(self, *args: Any, **kwargs: Any):
        return await gerar_preview(*args, **kwargs)

    async def extrair_pagina_pdf(self, *args: Any, **kwargs: Any):
        return await extrair_pagina_pdf(*args, **kwargs)

    def pdf_pages_to_images(self, *args: Any, **kwargs: Any):
        return pdf_pages_to_images(*args, **kwargs)

    def generate_pdf_page_images(self, *args: Any, **kwargs: Any):
        return generate_pdf_page_images(*args, **kwargs)

    def get_file_path_by_id(self, *args: Any, **kwargs: Any):
        return get_file_path_by_id(*args, **kwargs)

    def extract_pdf_region_image(self, *args: Any, **kwargs: Any):
        return extract_pdf_region_image(*args, **kwargs)

    def parse_annotation_to_dataframe(self, *args: Any, **kwargs: Any):
        return parse_annotation_to_dataframe(*args, **kwargs)

    def extract_data_from_pdf_region(self, *args: Any, **kwargs: Any):
        return extract_data_from_pdf_region(*args, **kwargs)

    def extract_data_from_single_page(self, *args: Any, **kwargs: Any):
        return extract_data_from_single_page(*args, **kwargs)

    def processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return _processar_linha_padronizada(*args, **kwargs)

    def _processar_linha_padronizada(self, *args: Any, **kwargs: Any):
        return _processar_linha_padronizada(*args, **kwargs)


file_processing_legacy_service = FileProcessingLegacyService()
