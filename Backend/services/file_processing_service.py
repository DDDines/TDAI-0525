# catalogai_project/Backend/services/file_processing_service.py
import pandas as pd
from pdfplumber import open as pdf_open
import csv
import io
import chardet
import base64
import os
import asyncio
from sqlalchemy.orm import Session
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_bytes, convert_from_path
import time
from typing import List, Dict, Any, Union, Optional
from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile, HTTPException
import uuid
import pdfplumber

from Backend.core.logging_config import get_logger
from Backend.core.config import settings
from Backend import models, crud_fornecedores, schemas
from Backend.services import web_data_extractor_service

logger = get_logger(__name__)

# Maximum number of worker threads used when processing PDF pages
MAX_PREVIEW_WORKERS = int(os.getenv("PDF_PREVIEW_WORKERS", "0"))
_preview_executor = (
    ThreadPoolExecutor(max_workers=MAX_PREVIEW_WORKERS)
    if MAX_PREVIEW_WORKERS > 0
    else None
)


async def save_uploaded_catalog(
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
    directory = Path(settings.UPLOAD_DIRECTORY) / "catalogs"
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parent.parent / directory
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


def delete_catalog_file(stored_filename: str) -> None:
    """Remove a stored catalog file from disk if it exists."""
    directory = Path(settings.UPLOAD_DIRECTORY) / "catalogs"
    if not directory.is_absolute():
        directory = Path(__file__).resolve().parent.parent / directory
    path = directory / stored_filename
    try:
        if path.exists():
            path.unlink()
    except Exception:
        logger.exception("Erro ao remover arquivo %s", stored_filename)


def _limpar_valor_extraido(valor: Any) -> Optional[str]:
    """Helper para limpar strings ou converter outros tipos para string, retornando None se vazio."""
    if valor is None:
        return None
    try:
        s = str(valor).strip()
        # Considerar 'nan', 'None' (string), '' como nulos após strip
        if s.lower() in [
            "",
            "nan",
            "none",
            "#n/a",
            "na",
            "<na>",
        ]:  # Adicionado #N/A, NA, <NA> comuns em planilhas
            return None
        return s
    except:
        return None


def _processar_linha_padronizada(
    linha_original: Dict[str, Any],
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
) -> Optional[Dict[str, Any]]:
    """
    Tenta padronizar uma linha de dados extraída para campos comuns do Produto.
    'mapeamento_colunas_usuario' permite que o usuário mapeie colunas do arquivo
    para campos do Produto (ex: {"Nome do Item no Arquivo": "nome_base"}).
    Retorna um dicionário com chaves padronizadas ('nome_base', 'marca', etc.) e
    um campo 'dados_brutos_originais' com todos os campos não mapeados ou não reconhecidos.
    """
    produto_dados_padronizados: Dict[str, Any] = {}
    dados_brutos_nao_mapeados: Dict[str, Any] = {}

    # Mapeamento padrão (de nomes de coluna comuns em arquivos para nossos campos internos)
    # Chaves devem ser em minúsculo e sem espaços extra para matching.
    mapeamento_default = {
        "nome": "nome_base",
        "produto": "nome_base",
        "item": "nome_base",
        "title": "nome_base",
        "título": "nome_base",
        "titulo": "nome_base",
        "sku": "sku_original",
        "código": "sku_original",
        "codigo": "sku_original",
        "ref": "sku_original",
        "referência": "sku_original",
        "referencia": "sku_original",
        "marca": "marca",
        "fabricante": "marca",
        "brand": "marca",
        "categoria": "categoria_original",
        "category": "categoria_original",
        "descrição": "descricao_original",
        "descricao": "descricao_original",
        "description": "descricao_original",
        "ean": "ean_original",
        "gtin": "ean_original",
        "upc": "ean_original",
        "preço": "preco_original",
        "preco": "preco_original",
        "price": "preco_original",
        "valor": "preco_original",
        "url_imagem": "imagem_url_original",
        "imagem": "imagem_url_original",
        "image_url": "imagem_url_original",
        # Adicionar mais mapeamentos comuns conforme necessário
    }

    # Se o usuário fornecer um mapeamento, ele tem prioridade
    mapeamento_final = mapeamento_default.copy()
    if mapeamento_colunas_usuario:
        # Normalizar chaves do mapeamento do usuário também
        mapeamento_usuario_norm = {
            str(k).lower().strip(): v for k, v in mapeamento_colunas_usuario.items()
        }
        mapeamento_final.update(mapeamento_usuario_norm)

    for nome_coluna_original, valor_original in linha_original.items():
        valor_limpo = _limpar_valor_extraido(valor_original)
        if valor_limpo is None:  # Ignora células completamente vazias/nulas
            continue

        nome_coluna_norm = str(nome_coluna_original).lower().strip()
        campo_produto_destino = mapeamento_final.get(nome_coluna_norm)

        if campo_produto_destino:
            # Se o campo destino já existe e tem valor, não sobrescreve com um valor "menos específico"
            # (ex: se "nome_base" já foi pego de "produto", não sobrescrever com "item" se "item" for menos completo)
            # Esta lógica de prioridade pode ser complexa; por ora, simples atribuição se não preenchido.
            if campo_produto_destino not in produto_dados_padronizados:
                produto_dados_padronizados[campo_produto_destino] = valor_limpo
            # Ou uma lógica para concatenar/escolher o melhor valor se múltiplos mapearem para o mesmo campo
        else:
            # Guarda campos não mapeados diretamente em dados_brutos_originais
            dados_brutos_nao_mapeados[str(nome_coluna_original).strip()] = valor_limpo

    # Garante que 'nome_base' ou 'sku_original' exista, senão a linha é pouco útil
    if not produto_dados_padronizados.get(
        "nome_base"
    ) and not produto_dados_padronizados.get("sku_original"):
        # Se não tem nome_base nem sku, mas tem outros dados, tenta pegar o primeiro valor não nulo como nome_base
        if dados_brutos_nao_mapeados:
            primeiro_valor_util = next(
                (v for v in dados_brutos_nao_mapeados.values() if v), None
            )
            if primeiro_valor_util:
                produto_dados_padronizados["nome_base"] = primeiro_valor_util
            else:  # Se realmente não há nada que possa ser um nome/identificador
                return {
                    "motivo_descarte": "Faltam nome_base e sku_original",
                    "linha_original": linha_original,
                }
        else:
            return {
                "motivo_descarte": "Faltam nome_base e sku_original",
                "linha_original": linha_original,
            }

    # Adiciona os campos não mapeados ao dicionário principal
    if dados_brutos_nao_mapeados:
        produto_dados_padronizados["dados_brutos_adicionais"] = (
            dados_brutos_nao_mapeados
        )

    return produto_dados_padronizados


async def processar_arquivo_excel(
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
                    linha_dict_raw, mapeamento_colunas_usuario
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
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    product_type_id: Optional[int] = None,
) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    try:
        # Detectar encoding usando chardet para lidar com diferentes formatos
        try:
            import chardet  # Lazy import para evitar dependência desnecessária em outros caminhos

            detection = chardet.detect(conteudo_arquivo)
            encoding_detectada = (detection.get("encoding") or "utf-8").lower()
        except Exception:  # Falha na detecção: assume utf-8
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
            primeira_linha = (
                conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""
            )
            if ";" in primeira_linha:
                delimitador_provavel = ";"
            elif "\t" in primeira_linha:
                delimitador_provavel = "\t"

        leitor_csv = csv.DictReader(
            io.StringIO(conteudo_str), delimiter=delimitador_provavel
        )
        for linha_dict_raw in leitor_csv:
            produto_padronizado = _processar_linha_padronizada(
                linha_dict_raw, mapeamento_colunas_usuario
            )
            if produto_padronizado:
                if product_type_id is not None:
                    produto_padronizado["product_type_id"] = product_type_id
                produtos_extraidos.append(produto_padronizado)
        return produtos_extraidos
    except Exception as e:
        logger.error("Erro ao processar arquivo CSV: %s", e)
        return [{"erro_processamento_csv": f"Falha ao ler arquivo CSV: {str(e)}"}]


async def processar_arquivo_pdf(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    usar_llm: bool = True,
    product_type_id: Optional[int] = None,
    pages: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    log_pdf: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(conteudo_arquivo)) as pdf:
            log_pdf.append(f"PDF com {len(pdf.pages)} páginas.")
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                if pages and page_num not in pages:
                    continue
                # Tenta extrair tabelas da página
                # Configurações para extração de tabela podem ser ajustadas
                tables = page.extract_tables(
                    table_settings={
                        "vertical_strategy": "lines",  # ou "text"
                        "horizontal_strategy": "lines",  # ou "text"
                    }
                )
                if tables:
                    log_pdf.append(f"Página {i+1}: Encontradas {len(tables)} tabelas.")
                    for table_num, table_data in enumerate(tables):
                        if (
                            not table_data or len(table_data) < 2
                        ):  # Precisa de cabeçalho e pelo menos uma linha de dados
                            log_pdf.append(
                                f"Página {i+1}, Tabela {table_num+1}: Tabela vazia ou sem dados suficientes."
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
                                    f"Página {i+1}, Tabela {table_num+1}, Linha {row_idx+1}: Número de colunas ({len(row_data)}) não corresponde ao cabeçalho ({len(headers)}). Pulando."
                                )
                                continue

                            linha_dict_raw = {
                                headers[col_idx]: cell_data
                                for col_idx, cell_data in enumerate(row_data)
                            }
                            produto_padronizado = _processar_linha_padronizada(
                                linha_dict_raw, mapeamento_colunas_usuario
                            )
                            if produto_padronizado:
                                if product_type_id is not None:
                                    produto_padronizado["product_type_id"] = (
                                        product_type_id
                                    )
                                produtos_extraidos.append(produto_padronizado)
                else:
                    log_pdf.append(
                        f"Página {i+1}: Nenhuma tabela encontrada com as configurações atuais."
                    )

            if (
                not produtos_extraidos and len(pdf.pages) > 0
            ):  # Fallback se nenhuma tabela extraiu dados
                log_pdf.append(
                    "Nenhum produto extraído de tabelas. Extraindo texto de todas as páginas."
                )
                for i, page in enumerate(pdf.pages):
                    page_num = i + 1
                    if pages and page_num not in pages:
                        continue
                    page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if page_text and page_text.strip():
                        log_pdf.append(f"Página {i+1}: Texto extraído.")
                        texto_chave = f"texto_completo_pagina_{i+1}"
                        if usar_llm:
                            try:
                                dados_produto = await web_data_extractor_service.extrair_dados_produto_com_llm(
                                    page_text
                                )
                                if isinstance(dados_produto, dict):
                                    dados_produto["texto_bruto"] = page_text.strip()[
                                        :20000
                                    ]
                                    if product_type_id is not None:
                                        dados_produto["product_type_id"] = (
                                            product_type_id
                                        )
                                    produtos_extraidos.append(dados_produto)
                                else:
                                    item = {
                                        "nome_base": f"Texto da página {i+1}",
                                        "dados_brutos_adicionais": {
                                            texto_chave: page_text.strip()[:20000]
                                        },
                                    }
                                    if product_type_id is not None:
                                        item["product_type_id"] = product_type_id
                                    produtos_extraidos.append(item)
                                log_pdf.append(
                                    f"Página {i+1}: Texto processado com LLM."
                                )
                            except Exception as llm_e:
                                log_pdf.append(
                                    f"Página {i+1}: Erro ao extrair dados com LLM: {str(llm_e)}"
                                )
                                item = {
                                    "nome_base": f"Conteúdo Bruto da Página {i+1} do PDF",
                                    "dados_brutos_adicionais": {
                                        texto_chave: page_text.strip()[:20000]
                                    },
                                }
                                if product_type_id is not None:
                                    item["product_type_id"] = product_type_id
                                produtos_extraidos.append(item)
                        else:
                            item = {
                                "nome_base": f"Conteúdo da Página {i+1}",
                                "dados_brutos_adicionais": {
                                    texto_chave: page_text.strip()[:20000]
                                },
                            }
                            if product_type_id is not None:
                                item["product_type_id"] = product_type_id
                            produtos_extraidos.append(item)
                            log_pdf.append(
                                f"Página {i+1}: Texto armazenado sem uso do LLM."
                            )
                    else:
                        log_pdf.append(
                            f"Página {i+1}: Nenhum texto extraível encontrado."
                        )

            if not produtos_extraidos:  # Se ainda vazio
                return [
                    {
                        "erro_processamento_pdf": "Nenhum dado de produto pôde ser extraído do PDF.",
                        "log_pdf": log_pdf,
                    }
                ]

        return produtos_extraidos
    except Exception as e:
        import traceback

        log_pdf.append(f"Erro crítico ao processar arquivo PDF: {str(e)}")
        logger.error("Erro ao processar arquivo PDF: %s", traceback.format_exc())
        return [
            {
                "erro_processamento_pdf": f"Falha crítica ao ler arquivo PDF: {str(e)}",
                "log_pdf": log_pdf,
            }
        ]


async def preview_arquivo_excel(
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


async def preview_arquivo_csv(
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


async def preview_arquivo_pdf(
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


async def gerar_preview(
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


def pdf_pages_to_images(db: Session, file: UploadFile, fornecedor_id: int, user_id: int, offset: int, limit: int) -> Dict[str, Any]:
    """
    Salva um ficheiro PDF, cria um registo na base de dados, e converte um lote de páginas em imagens.
    """
    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    catalogs_dir = upload_dir / "catalogs"
    previews_dir = upload_dir / "previews"
    
    catalogs_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)
    
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
        # USA O CONTEÚDO EM MEMÓRIA PARA OBTER O TOTAL DE PÁGINAS
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
                
                image_url = f"/static/uploads/previews/{image_filename}"
                image_urls.append(image_url)

        except Exception as e:
            logger.error(f"Falha ao converter PDF para imagens: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Erro ao processar o PDF. Verifique se o Poppler está instalado corretamente.")

    return {"image_urls": image_urls, "total_pages": total_pages, "import_file_id": import_file.id}


def get_file_path_by_id(db: Session, file_id: str) -> str:
    """Retrieve the stored file path for a catalog import by ID."""
    import_file = (
        db.query(models.CatalogImportFile)
        .filter(models.CatalogImportFile.id == file_id)
        .first()
    )
    if not import_file:
        return None

    base_dir = os.path.join("Backend", "static", "uploads", "catalogs")
    return os.path.join(base_dir, import_file.file_name)


def extract_data_from_pdf_region(
    file_path: str, page_number: int, region: Optional[List[float]] = None
) -> pd.DataFrame:
    """Extract tables from a specific region of a PDF page."""

    all_rows: List[List[Any]] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if not (1 <= page_number <= len(pdf.pages)):
                raise ValueError(
                    f"Número de página inválido: {page_number}. PDF tem {len(pdf.pages)} páginas."
                )

            page = pdf.pages[page_number - 1]
            page_to_process = page
            if region and len(region) == 4:
                bbox = tuple(map(float, region))
                page_to_process = page.crop(bbox)

            tables = page_to_process.extract_tables(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "text",
                    "snap_tolerance": 5,
                }
            )

            if not tables:
                tables = page_to_process.extract_tables()

            if not tables:
                text = page_to_process.extract_text()
                if text:
                    lines = text.strip().split("\n")
                    header = [h.strip() for h in lines[0].split("  ")]
                    for line in lines[1:]:
                        all_rows.append([l.strip() for l in line.split("  ")])
                    return pd.DataFrame(all_rows, columns=header)
                return pd.DataFrame()

            header: List[str] = []
            for i, table in enumerate(tables):
                if i == 0:
                    header = table[0]
                    all_rows.extend(table[1:])
                else:
                    all_rows.extend(table)

        if not all_rows:
            return pd.DataFrame()

        return pd.DataFrame(all_rows, columns=header)

    except Exception as e:
        print(f"Erro ao processar o PDF: {e}")
        return pd.DataFrame()


async def extrair_pagina_pdf(
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

    # Use temporary file path for table extraction
    tmp_path = Path(os.getenv("TMPDIR", "/tmp")) / f"temp_{uuid.uuid4().hex}.pdf"
    tmp_path.write_bytes(conteudo_pdf)
    try:
        df = extract_data_from_pdf_region(str(tmp_path), page_number, region)
        table = df.values.tolist() if not df.empty else None
    finally:
        try:
            tmp_path.unlink()
        except Exception:
            pass

    return {"image": f"data:image/png;base64,{image_b64}", "text": text, "table": table}


def generate_pdf_page_images(pdf_path: str) -> List[str]:
    """Gera imagens PNG para todas as páginas de um PDF.

    As imagens são salvas no mesmo diretório do arquivo e os caminhos
    completos são retornados em uma lista.
    """

    poppler_dir = os.getenv("POPPLER_PATH") or settings.POPPLER_PATH
    kwargs = {"poppler_path": poppler_dir} if poppler_dir else {}

    images = convert_from_path(pdf_path, dpi=200, **kwargs)
    base_dir = Path(pdf_path).parent
    base_name = Path(pdf_path).stem
    urls: List[str] = []

    for idx, image in enumerate(images, start=1):
        img_path = base_dir / f"{base_name}_{idx}.png"
        image.save(img_path, "PNG")
        urls.append(str(img_path))

    return urls
