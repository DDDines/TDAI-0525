# tdai_project/Backend/services/file_processing_service.py
import pandas as pd
import pdfplumber
import csv
import io # Para ler o conteúdo do arquivo em memória
from typing import List, Dict, Any, Union, Optional

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
            else: # Se realmente não há nada que possa ser um nome/identificador
                return None # Ignora a linha
        else:
            return None # Ignora a linha

    # Adiciona os campos não mapeados ao dicionário principal
    if dados_brutos_nao_mapeados:
        produto_dados_padronizados["dados_brutos_adicionais"] = dados_brutos_nao_mapeados
        
    return produto_dados_padronizados


async def processar_arquivo_excel(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    try:
        df = pd.read_excel(io.BytesIO(conteudo_arquivo), sheet_name=0) # Lê a primeira aba
        df.dropna(how='all', inplace=True) # Remove linhas totalmente vazias
        
        # Não converter para string globalmente aqui, _limpar_valor_extraido fará isso por célula
        # df = df.astype(str).replace({'nan': None, 'None': None}) 

        for _, linha_pandas in df.iterrows():
            # Converte a Series do pandas para dict, tratando NaNs que podem virar float
            linha_dict_raw = {col: val if pd.notna(val) else None for col, val in linha_pandas.to_dict().items()}
            produto_padronizado = _processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
            if produto_padronizado:
                produtos_extraidos.append(produto_padronizado)
        return produtos_extraidos
    except Exception as e:
        print(f"Erro ao processar arquivo Excel: {e}")
        return [{"erro_processamento_excel": f"Falha ao ler arquivo Excel: {str(e)}"}]


async def processar_arquivo_csv(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    produtos_extraidos: List[Dict[str, Any]] = []
    try:
        try:
            conteudo_str = conteudo_arquivo.decode('utf-8-sig') # Tenta utf-8 com BOM
        except UnicodeDecodeError:
            try:
                conteudo_str = conteudo_arquivo.decode('latin-1')
            except UnicodeDecodeError:
                conteudo_str = conteudo_arquivo.decode('cp1252', errors='replace') # Windows Latin-1
            
        # Detectar delimitador (simples, pode ser melhorado com sniffer completo)
        delimitador_provavel = ','
        if ';' in conteudo_str.splitlines()[0]: # Checa na primeira linha
            delimitador_provavel = ';'
        elif '\t' in conteudo_str.splitlines()[0]:
            delimitador_provavel = '\t'

        leitor_csv = csv.DictReader(io.StringIO(conteudo_str), delimiter=delimitador_provavel)
        for linha_dict_raw in leitor_csv:
            produto_padronizado = _processar_linha_padronizada(linha_dict_raw, mapeamento_colunas_usuario)
            if produto_padronizado:
                produtos_extraidos.append(produto_padronizado)
        return produtos_extraidos
    except Exception as e:
        print(f"Erro ao processar arquivo CSV: {e}")
        return [{"erro_processamento_csv": f"Falha ao ler arquivo CSV: {str(e)}"}]

async def processar_arquivo_pdf(conteudo_arquivo: bytes, mapeamento_colunas_usuario: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
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

            if not produtos_extraidos and len(pdf.pages) > 0: # Fallback se nenhuma tabela extraiu dados
                log_pdf.append("Nenhum produto extraído de tabelas. Tentando extrair texto completo da primeira página como fallback.")
                page_text = pdf.pages[0].extract_text(x_tolerance=2, y_tolerance=2) # Ajustar tolerâncias pode ajudar
                if page_text and page_text.strip():
                     # Aqui, a IA seria necessária para estruturar este texto.
                     # Por agora, apenas salvamos o texto bruto.
                     produtos_extraidos.append({
                         "nome_base": f"Conteúdo Bruto da Página 1 do PDF (Requer Análise IA)", 
                         "dados_brutos_adicionais": {"texto_completo_pagina_1": page_text.strip()[:20000]} # Limita tamanho
                    })
                     log_pdf.append("Texto da primeira página extraído como fallback.")
                else:
                    log_pdf.append("Nenhum texto extraível encontrado na primeira página.")
            
            if not produtos_extraidos: # Se ainda vazio
                 return [{"erro_processamento_pdf": "Nenhum dado de produto pôde ser extraído do PDF.", "log_pdf": log_pdf}]

        return produtos_extraidos
    except Exception as e:
        import traceback
        log_pdf.append(f"Erro crítico ao processar arquivo PDF: {str(e)}")
        print(f"Erro ao processar arquivo PDF: {traceback.format_exc()}")
        return [{"erro_processamento_pdf": f"Falha crítica ao ler arquivo PDF: {str(e)}", "log_pdf": log_pdf}]