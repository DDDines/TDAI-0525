# catalogai_project/Backend/services/file_processing_service.py
import pandas as pd
import pdfplumber
import csv
import io  # Para ler o conteúdo do arquivo em memória
import chardet
import base64
from pdf2image import convert_from_bytes
from typing import List, Dict, Any, Union, Optional
from Backend.core.logging_config import get_logger
from Backend.services import web_data_extractor_service

logger = get_logger(__name__)

def _limpar_valor_extraido(valor: Any) -> Optional[str]:
    """Helper para limpar strings ou converter outros tipos para string, retornando None se vazio."""
    if valor is None:
        return None
    try:
        s = str(valor).strip()
        # Considerar 'nan', 'None' (string), '' como nulos após strip
        if s.lower() in ['', 'nan', 'none', '#n/a', 'na', '<na>']: # Adicionado #N/A, NA, <NA> comuns em planilhas
            return None
        return s
    except:
        return None


def _processar_linha_padronizada(
    linha_original: Dict[str, Any], 
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None
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
        "nome": "nome_base", "produto": "nome_base", "item": "nome_base", "title": "nome_base", "título": "nome_base", "titulo": "nome_base",
        "sku": "sku_original", "código": "sku_original", "codigo": "sku_original", "ref": "sku_original", "referência": "sku_original", "referencia": "sku_original",
        "marca": "marca", "fabricante": "marca", "brand": "marca",
        "categoria": "categoria_original", "category": "categoria_original",
        "descrição": "descricao_original", "descricao": "descricao_original", "description": "descricao_original",
        "ean": "ean_original", "gtin": "ean_original", "upc": "ean_original",
        "preço": "preco_original", "preco": "preco_original", "price": "preco_original", "valor": "preco_original",
        "url_imagem": "imagem_url_original", "imagem": "imagem_url_original", "image_url": "imagem_url_original",
        # Adicionar mais mapeamentos comuns conforme necessário
    }

    # Se o usuário fornecer um mapeamento, ele tem prioridade
    mapeamento_final = mapeamento_default.copy()
    if mapeamento_colunas_usuario:
        # Normalizar chaves do mapeamento do usuário também
        mapeamento_usuario_norm = {str(k).lower().strip(): v for k, v in mapeamento_colunas_usuario.items()}
        mapeamento_final.update(mapeamento_usuario_norm)

    for nome_coluna_original, valor_original in linha_original.items():
        valor_limpo = _limpar_valor_extraido(valor_original)
        if valor_limpo is None: # Ignora células completamente vazias/nulas
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
    if not produto_dados_padronizados.get("nome_base") and not produto_dados_padronizados.get("sku_original"):
        # Se não tem nome_base nem sku, mas tem outros dados, tenta pegar o primeiro valor não nulo como nome_base
        if dados_brutos_nao_mapeados:
            primeiro_valor_util = next((v for v in dados_brutos_nao_mapeados.values() if v), None)
            if primeiro_valor_util:
                 produto_dados_padronizados["nome_base"] = primeiro_valor_util
            else:  # Se realmente não há nada que possa ser um nome/identificador
                return {"motivo_descarte": "Faltam nome_base e sku_original", "linha_original": linha_original}
        else:
            return {"motivo_descarte": "Faltam nome_base e sku_original", "linha_original": linha_original}

    # Adiciona os campos não mapeados ao dicionário principal
    if dados_brutos_nao_mapeados:
        produto_dados_padronizados["dados_brutos_adicionais"] = dados_brutos_nao_mapeados
        
    return produto_dados_padronizados


async def processar_arquivo_excel(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    sheet_name: Optional[str] = None,
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
                    produtos_extraidos.append(produto_padronizado)
        return produtos_extraidos
    except Exception as e:
        logger.error("Erro ao processar arquivo Excel: %s", e)
        return [{"erro_processamento_excel": f"Falha ao ler arquivo Excel: {str(e)}"}]


async def processar_arquivo_csv(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
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
            primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""
            if ";" in primeira_linha:
                delimitador_provavel = ";"
            elif "\t" in primeira_linha:
                delimitador_provavel = "\t"

        leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador_provavel)
        for linha_dict_raw in leitor_csv:
            produto_padronizado = _processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
            if produto_padronizado:
                produtos_extraidos.append(produto_padronizado)
        return produtos_extraidos
    except Exception as e:
        logger.error("Erro ao processar arquivo CSV: %s", e)
        return [{"erro_processamento_csv": f"Falha ao ler arquivo CSV: {str(e)}"}]

async def processar_arquivo_pdf(
    conteudo_arquivo: bytes,
    mapeamento_colunas_usuario: Optional[Dict[str, str]] = None,
    usar_llm: bool = True,
) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    log_pdf: List[str] = []
    try:
        with pdfplumber.open(io.BytesIO(conteudo_arquivo)) as pdf:
            log_pdf.append(f"PDF com {len(pdf.pages)} páginas.")
            for i, page in enumerate(pdf.pages):
                # Tenta extrair tabelas da página
                # Configurações para extração de tabela podem ser ajustadas
                tables = page.extract_tables(table_settings={
                    "vertical_strategy": "lines", # ou "text"
                    "horizontal_strategy": "lines", # ou "text"
                })
                if tables:
                    log_pdf.append(f"Página {i+1}: Encontradas {len(tables)} tabelas.")
                    for table_num, table_data in enumerate(tables):
                        if not table_data or len(table_data) < 2: # Precisa de cabeçalho e pelo menos uma linha de dados
                            log_pdf.append(f"Página {i+1}, Tabela {table_num+1}: Tabela vazia ou sem dados suficientes.")
                            continue
                        
                        headers_raw = table_data[0]
                        headers = [_limpar_valor_extraido(h) or f"coluna_vazia_{idx}" for idx, h in enumerate(headers_raw)]
                        
                        for row_idx, row_data in enumerate(table_data[1:]):
                            if len(row_data) != len(headers):
                                log_pdf.append(f"Página {i+1}, Tabela {table_num+1}, Linha {row_idx+1}: Número de colunas ({len(row_data)}) não corresponde ao cabeçalho ({len(headers)}). Pulando.")
                                continue

                            linha_dict_raw = {headers[col_idx]: cell_data for col_idx, cell_data in enumerate(row_data)}
                            produto_padronizado = _processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
                            if produto_padronizado:
                                produtos_extraidos.append(produto_padronizado)
                else:
                    log_pdf.append(f"Página {i+1}: Nenhuma tabela encontrada com as configurações atuais.")

            if not produtos_extraidos and len(pdf.pages) > 0:  # Fallback se nenhuma tabela extraiu dados
                log_pdf.append(
                    "Nenhum produto extraído de tabelas. Extraindo texto de todas as páginas."
                )
                for i, page in enumerate(pdf.pages):
                    page_text = page.extract_text(x_tolerance=2, y_tolerance=2)
                    if page_text and page_text.strip():
                        log_pdf.append(f"Página {i+1}: Texto extraído.")
                        texto_chave = f"texto_completo_pagina_{i+1}"
                        if usar_llm:
                            try:
                                dados_produto = await web_data_extractor_service.extrair_dados_produto_com_llm(page_text)
                                if isinstance(dados_produto, dict):
                                    dados_produto["texto_bruto"] = page_text.strip()[:20000]
                                    produtos_extraidos.append(dados_produto)
                                else:
                                    produtos_extraidos.append({
                                        "nome_base": f"Texto da página {i+1}",
                                        "dados_brutos_adicionais": {texto_chave: page_text.strip()[:20000]},
                                    })
                                log_pdf.append(f"Página {i+1}: Texto processado com LLM.")
                            except Exception as llm_e:
                                log_pdf.append(f"Página {i+1}: Erro ao extrair dados com LLM: {str(llm_e)}")
                                produtos_extraidos.append({
                                    "nome_base": f"Conteúdo Bruto da Página {i+1} do PDF",
                                    "dados_brutos_adicionais": {texto_chave: page_text.strip()[:20000]},
                                })
                        else:
                            produtos_extraidos.append({
                                "nome_base": f"Conteúdo da Página {i+1}",
                                "dados_brutos_adicionais": {texto_chave: page_text.strip()[:20000]},
                            })
                            log_pdf.append(f"Página {i+1}: Texto armazenado sem uso do LLM.")
                    else:
                        log_pdf.append(f"Página {i+1}: Nenhum texto extraível encontrado.")
            
            if not produtos_extraidos: # Se ainda vazio
                 return [{"erro_processamento_pdf": "Nenhum dado de produto pôde ser extraído do PDF.", "log_pdf": log_pdf}]

        return produtos_extraidos
    except Exception as e:
        import traceback
        log_pdf.append(f"Erro crítico ao processar arquivo PDF: {str(e)}")
        logger.error("Erro ao processar arquivo PDF: %s", traceback.format_exc())
        return [{"erro_processamento_pdf": f"Falha crítica ao ler arquivo PDF: {str(e)}", "log_pdf": log_pdf}]


async def preview_arquivo_excel(conteudo_arquivo: bytes, max_rows: int = 5) -> Dict[str, Any]:
    """Retorna cabeçalhos e linhas de amostra de um arquivo Excel."""
    try:
        df = pd.read_excel(io.BytesIO(conteudo_arquivo), sheet_name=0)
        headers = [str(col) for col in df.columns]
        sample_rows = df.head(max_rows).fillna("").to_dict(orient="records")
        return {"headers": headers, "sample_rows": sample_rows}
    except Exception as e:
        logger.error("Erro ao gerar preview de arquivo Excel: %s", e)
        return {"error": f"Falha ao ler arquivo Excel: {str(e)}"}


async def preview_arquivo_csv(conteudo_arquivo: bytes, max_rows: int = 5) -> Dict[str, Any]:
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
            primeira_linha = conteudo_str.splitlines()[0] if conteudo_str.splitlines() else ""
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


async def preview_arquivo_pdf(conteudo_arquivo: bytes, max_rows: int = 5) -> Dict[str, Any]:
    """Tenta extrair cabeçalhos e linhas de amostra de tabelas em um PDF."""
    try:
        with pdfplumber.open(io.BytesIO(conteudo_arquivo)) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables(table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines"})
                if tables:
                    primeira_tabela = tables[0]
                    if len(primeira_tabela) < 2:
                        continue
                    headers_raw = primeira_tabela[0]
                    headers = [str(h).strip() if h is not None else f"coluna_vazia_{idx}" for idx, h in enumerate(headers_raw)]
                    sample_rows = []
                    for row in primeira_tabela[1: max_rows + 1]:
                        if len(row) != len(headers):
                            continue
                        sample_rows.append({headers[i]: row[i] for i in range(len(headers))})
                    return {"headers": headers, "sample_rows": sample_rows}
        return {"headers": [], "sample_rows": [], "message": "Nenhuma tabela encontrada no PDF"}
    except Exception as e:
        logger.error("Erro ao gerar preview de arquivo PDF: %s", e)
        return {"error": f"Falha ao ler arquivo PDF: {str(e)}"}


def pdf_pages_to_images(conteudo_arquivo: bytes, max_pages: int = 1) -> List[str]:
    """Converte páginas de um PDF em imagens base64."""
    try:
        pages = convert_from_bytes(conteudo_arquivo, fmt="png")
        images_b64: List[str] = []
        for i, page in enumerate(pages):
            if i >= max_pages:
                break
            buf = io.BytesIO()
            page.save(buf, format="PNG")
            images_b64.append(base64.b64encode(buf.getvalue()).decode("utf-8"))
        return images_b64
    except Exception as e:
        logger.error("Erro ao converter PDF em imagens: %s", e)
        return []


async def gerar_preview(conteudo_arquivo: bytes, ext: str, max_rows: int = 5) -> Dict[str, Any]:
    """Despacha para a função de preview correta com base na extensão."""
    ext = ext.lower()
    if ext in [".xlsx", ".xls"]:
        return await preview_arquivo_excel(conteudo_arquivo, max_rows)
    if ext == ".csv":
        return await preview_arquivo_csv(conteudo_arquivo, max_rows)
    if ext == ".pdf":
        return await preview_arquivo_pdf(conteudo_arquivo, max_rows)
    raise ValueError("Formato de arquivo não suportado para preview")
