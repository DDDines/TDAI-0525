# tdai_project/Backend/services/web_data_extractor_service.py
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import trafilatura # type: ignore
import extruct # type: ignore
import json
import re
from typing import List, Dict, Optional, Any
from urllib.parse import urlparse
from sqlalchemy.orm import Session # Importar Session para type hinting, se necessário
from datetime import datetime, timezone


try:
    from googleapiclient.discovery import build # type: ignore
    GOOGLE_API_CLIENT_INSTALLED = True
except ImportError:
    GOOGLE_API_CLIENT_INSTALLED = False
    print("AVISO: Biblioteca google-api-python-client não instalada ou com problemas. Busca no Google pode não funcionar.")

# Ajustando as importações para serem absolutas a partir da raiz do projeto (Backend)
# Assumindo que 'Backend' está no sys.path ou é o diretório de trabalho.
from core.config import settings 
import models 
from services import ia_generation_service # Importação absoluta para o módulo irmão

# --- Google Search Service ---
async def buscar_urls_google(query: str, num_results: int = 3) -> List[str]:
    urls_encontradas: List[str] = []
    if not GOOGLE_API_CLIENT_INSTALLED:
        print("ERRO: google-api-python-client não está instalada. Busca no Google desabilitada.")
        return urls_encontradas
        
    if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_ID:
        print("AVISO: GOOGLE_CSE_API_KEY ou GOOGLE_CSE_ID não configurados. Busca no Google desabilitada.")
        return urls_encontradas

    try:
        def _executar_busca_google_interna_valida():
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_CSE_API_KEY, cache_discovery=False)
            res = service.cse().list(q=query, cx=settings.GOOGLE_CSE_ID, num=num_results).execute()
            return [item['link'] for item in res.get('items', []) if 'link' in item]

        urls_encontradas = await asyncio.to_thread(_executar_busca_google_interna_valida)
        
    except Exception as e:
        print(f"Erro ao buscar no Google (query: '{query}'): {e}")
    return urls_encontradas

# --- Playwright Content Fetching Service ---
async def coletar_conteudo_pagina_playwright(url: str) -> Optional[str]:
    async with async_playwright() as p_instance:
        browser = None
        try:
            browser = await p_instance.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36',
                java_script_enabled=True,
                ignore_https_errors=True
            )
            page = await context.new_page()
            await page.goto(url, timeout=30000, wait_until="networkidle")
            html_content = await page.content()
            return html_content
        except PlaywrightTimeoutError:
            print(f"Timeout ao carregar URL com Playwright: {url}")
            return None
        except Exception as e:
            import traceback
            print(f"Erro ao coletar conteúdo com Playwright para {url}: {e}\n{traceback.format_exc()}")
            return None
        finally:
            if browser:
                await browser.close()

# --- Text Extraction Service ---
def extrair_texto_principal_com_trafilatura(html_content: str) -> Optional[str]:
    if not html_content: return None
    texto_principal = trafilatura.extract(
        html_content,
        include_comments=False,
        include_tables=True,
        output_format='text',
        favor_precision=False,
        include_formatting=False
    )
    return texto_principal

# --- Metadata Extraction Service ---
def _limpar_valor_metadado(valor: Any) -> Optional[Any]:
    if valor is None: return None
    if isinstance(valor, str):
        texto = valor.strip()
        texto = re.sub(r'\s+', ' ', texto)
        return texto if texto else None
    if isinstance(valor, list):
        lista_limpa = [_limpar_valor_metadado(item) for item in valor]
        return [item for item in lista_limpa if item is not None] or None
    return valor

def extrair_metadados_estruturados(html_content: str, url: str) -> Dict[str, Any]:
    if not html_content: return {}
    metadata_extraida = {}
    try:
        data = extruct.extract(html_content, base_url=url, syntaxes=['json-ld', 'microdata', 'opengraph'], uniform=True)
        for syntax_type, items_list in data.items():
            if not items_list: continue
            if syntax_type == 'json-ld' or syntax_type == 'microdata':
                for item_data in items_list:
                    if isinstance(item_data, dict) and ('Product' in str(item_data.get('@type', '') or item_data.get('type', '')) or syntax_type == 'microdata'):
                        data_to_store = item_data.get('properties', item_data) if syntax_type == 'microdata' else item_data
                        metadata_extraida[f"{syntax_type}_product_candidate"] = data_to_store
                        break 
            elif syntax_type == 'opengraph':
                 metadata_extraida['opengraph'] = items_list[0] if items_list else None
    except Exception as e:
        print(f"Erro ao extrair metadados estruturados de {url} com extruct: {e}")
    return metadata_extraida

def _normalizar_dados_de_metadados(metadata_bruta: Dict[str, Any]) -> Dict[str, Any]:
    dados_norm: Dict[str, Any] = {}
    produto_json_ld = metadata_bruta.get('json-ld_product_candidate')
    produto_microdata = metadata_bruta.get('microdata_product_candidate')
    opengraph_props_list = metadata_bruta.get('opengraph')
    opengraph = opengraph_props_list[0] if isinstance(opengraph_props_list, list) and opengraph_props_list else (opengraph_props_list if isinstance(opengraph_props_list, dict) else {})


    def get_first_string(value: Any) -> Optional[str]:
        if isinstance(value, list):
            for item_val in value:
                cleaned = _limpar_valor_metadado(item_val)
                if cleaned and isinstance(cleaned, str): return cleaned
            return None
        cleaned_val = _limpar_valor_metadado(value)
        return cleaned_val if isinstance(cleaned_val, str) else None

    if produto_json_ld and isinstance(produto_json_ld, dict):
        dados_norm['nome'] = get_first_string(produto_json_ld.get('name'))
        dados_norm['descricao_curta'] = get_first_string(produto_json_ld.get('description'))
        img = produto_json_ld.get('image')
        if isinstance(img, dict): img = img.get('url') or img.get('@id')
        elif isinstance(img, list): img = get_first_string([i.get('url') if isinstance(i, dict) else i for i in img])
        dados_norm['imagem_url'] = get_first_string(img)
        
        marca_info = produto_json_ld.get('brand')
        if isinstance(marca_info, dict): dados_norm['marca'] = get_first_string(marca_info.get('name'))
        else: dados_norm['marca'] = get_first_string(marca_info)
            
        dados_norm['sku'] = get_first_string(produto_json_ld.get('sku') or produto_json_ld.get('mpn'))
        
        offers = produto_json_ld.get('offers')
        if isinstance(offers, list): offers = offers[0] if offers else {}
        if isinstance(offers, dict):
            dados_norm['preco'] = get_first_string(offers.get('price') or offers.get('lowPrice') or offers.get('highPrice'))
            dados_norm['moeda_preco'] = get_first_string(offers.get('priceCurrency'))
            disponibilidade = get_first_string(offers.get('availability'))
            if disponibilidade and 'schema.org' in disponibilidade:
                dados_norm['disponibilidade'] = disponibilidade.split('/')[-1]
            else:
                dados_norm['disponibilidade'] = disponibilidade

    if produto_microdata and isinstance(produto_microdata, dict):
        if not dados_norm.get('nome'): dados_norm['nome'] = get_first_string(produto_microdata.get('name'))
        if not dados_norm.get('descricao_curta'): dados_norm['descricao_curta'] = get_first_string(produto_microdata.get('description'))
        if not dados_norm.get('imagem_url'): dados_norm['imagem_url'] = get_first_string(produto_microdata.get('image'))
        if not dados_norm.get('marca'): dados_norm['marca'] = get_first_string(produto_microdata.get('brand'))
        if not dados_norm.get('sku'): dados_norm['sku'] = get_first_string(produto_microdata.get('sku') or produto_microdata.get('mpn'))

    if opengraph and isinstance(opengraph, dict):
        if not dados_norm.get('nome'): dados_norm['nome'] = get_first_string(opengraph.get('og:title'))
        if not dados_norm.get('descricao_curta'): dados_norm['descricao_curta'] = get_first_string(opengraph.get('og:description'))
        if not dados_norm.get('imagem_url'): dados_norm['imagem_url'] = get_first_string(opengraph.get('og:image'))
        if not dados_norm.get('marca') and opengraph.get('og:type') == 'product':
            dados_norm['marca'] = get_first_string(opengraph.get('product:brand') or opengraph.get('og:site_name'))
        elif not dados_norm.get('marca'):
            dados_norm['marca'] = get_first_string(opengraph.get('og:site_name'))
             
    return {k: v for k, v in dados_norm.items() if v is not None and v != ""}

# --- LLM-based Data Extraction from Text ---
async def extrair_dados_produto_com_llm(
    texto_pagina: Optional[str],
    metadados_normalizados: Optional[Dict[str, Any]],
    campos_desejados: List[str],
    produto_nome_base: str,
    user: models.User 
    ) -> Optional[Dict[str, Any]]:
    
    if not texto_pagina and not metadados_normalizados:
        print("Nenhum texto de página nem metadados fornecidos para extração LLM.")
        return {"erro_llm": "Nenhum conteúdo para processar"}

    prompt_contexto_inicial = [
        f"Você é um assistente especialista em extrair informações detalhadas de produtos de e-commerce para o produto '{produto_nome_base}'.",
        "Seu objetivo é preencher um JSON com os campos solicitados da forma mais precisa possível, com base no contexto fornecido."
    ]
    contexto_para_llm = ""
    if metadados_normalizados and isinstance(metadados_normalizados, dict) and any(metadados_normalizados.values()):
        contexto_para_llm += "Contexto de Metadados Estruturados (use como base, valide e complemente com o texto principal):\n"
        for k, v_item in metadados_normalizados.items():
            contexto_para_llm += f"- {k.replace('_', ' ')}: {str(v_item)[:200]}\n" # Limita o tamanho da string de valor
    if texto_pagina:
        contexto_para_llm += f"\nTexto Principal da Página (use para encontrar informações e complementar/corrigir metadados):\n\"\"\"\n{texto_pagina[:10000]}\n\"\"\"" # Limita o tamanho do texto

    if not contexto_para_llm.strip():
        print("Contexto insuficiente para LLM (metadados e texto da página vazios ou muito curtos).")
        return {"erro_llm": "Contexto insuficiente para processar"}
        
    campos_formatados_prompt = ",\n".join([f'    "{campo}": "..."' for campo in campos_desejados])
    
    prompt = (
        "\n".join(prompt_contexto_inicial) +
        f"\n\nA partir do contexto e do texto da página fornecidos, extraia RIGOROSAMENTE os seguintes campos e retorne APENAS um objeto JSON válido com esta estrutura:\n"
        f"{{\n{campos_formatados_prompt}\n}}\n"
        f"Se uma informação para um campo específico não for encontrada de forma clara e inequívoca, retorne null para esse campo. Não invente informações.\n"
        f"Para campos do tipo lista (ex: 'lista_caracteristicas_beneficios_bullets', 'palavras_chave_seo_relevantes_lista'), retorne uma lista de strings.\n"
        f"Para campos do tipo dicionário (ex: 'especificacoes_tecnicas_dict'), retorne um dicionário chave-valor.\n"
        f"\nContexto e Texto para Análise:\n{contexto_para_llm}"
    )
    
    api_key_para_usar = user.chave_openai_pessoal or settings.OPENAI_API_KEY
    if not api_key_para_usar:
        print("AVISO: Nenhuma chave API OpenAI disponível para extração de dados com LLM.")
        return {"erro_llm": "Chave API OpenAI não configurada"}

    try:
        # A função _call_openai_api está em ia_generation_service
        json_str_resposta = await ia_generation_service._call_openai_api( 
            prompt=prompt,
            api_key=api_key_para_usar,
            model="gpt-3.5-turbo-0125", # Exemplo de modelo, pode ser configurável
            max_tokens=2048, # Ajustar conforme necessidade
            temperature=0.0, # Baixa temperatura para extração factual
            system_message="Sua tarefa é extrair informações de um texto e retorná-las em formato JSON conforme o schema solicitado. Seja preciso e não adicione campos extras."
        )
        
        # Tentativa de limpar a resposta da LLM para pegar apenas o JSON
        match = re.search(r"\{.*\}", json_str_resposta, re.DOTALL)
        if match:
            json_str_limpo = match.group(0)
        else:
            json_str_limpo = json_str_resposta # Se não encontrar JSON delimitado, usa a resposta como está

        dados_extraidos_llm = json.loads(json_str_limpo)
        
        # Merge inteligente: prioriza dados da LLM, mas mantém metadados se LLM não fornecer
        final_data = metadados_normalizados.copy() if metadados_normalizados and isinstance(metadados_normalizados, dict) else {}
        if isinstance(dados_extraidos_llm, dict):
            for key_llm, val_llm in dados_extraidos_llm.items():
                # Sobrescreve ou adiciona apenas se o valor da LLM não for None,
                # ou se a chave não existia nos metadados (para adicionar novos campos extraídos)
                if val_llm is not None or key_llm not in final_data:
                    final_data[key_llm] = val_llm
        return final_data
    except json.JSONDecodeError as json_e:
        print(f"Erro ao decodificar JSON da resposta da LLM: {json_e}. Resposta bruta: {json_str_resposta}")
        return {"extracao_bruta_llm_com_erro_json": json_str_resposta, **(metadados_normalizados or {})}
    except ValueError as ve: # Ex: erro de API key na chamada da OpenAI
        print(f"Erro na chamada da LLM para extração: {ve}")
        return {"erro_llm": str(ve), **(metadados_normalizados or {})}
    except Exception as e:
        import traceback
        print(f"Erro inesperado na extração com LLM: {traceback.format_exc()}")
        return {"erro_llm_inesperado": str(e), **(metadados_normalizados or {})}

# Função principal do serviço de extração, combinando as etapas
async def extract_relevant_data_from_url( # <--- NOME CORRETO DA FUNÇÃO PRINCIPAL DO SERVIÇO
    db: Session, 
    url: str, 
    produto: models.Produto
    ) -> models.Produto:
    """
    Serviço completo para buscar dados de uma URL, extrair conteúdo, 
    e atualizar o objeto Produto no banco de dados.
    """
    log_enriquecimento: List[Dict[str, Any]] = []
    
    def add_log(level: str, message: str, details: Optional[Dict] = None):
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": level, "message": message} # Necessário importar datetime, timezone
        if details: entry["details"] = details
        log_enriquecimento.append(entry)

    add_log("INFO", f"Iniciando enriquecimento web para produto ID {produto.id} com URL: {url}")
    produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.EM_PROGRESSO
    db.add(produto)
    db.commit()

    html_content = await coletar_conteudo_pagina_playwright(url)

    if not html_content:
        add_log("ERROR", "Falha ao coletar HTML da página.")
        produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.FALHOU
        produto.log_enriquecimento_web = log_enriquecimento # Salva o log acumulado
        db.add(produto)
        db.commit()
        db.refresh(produto)
        return produto # Retorna o produto com status de falha

    add_log("INFO", "Conteúdo HTML coletado com sucesso.")
    
    texto_principal = extrair_texto_principal_com_trafilatura(html_content)
    if texto_principal: add_log("INFO", "Texto principal extraído com Trafilatura.")
    else: add_log("WARNING", "Não foi possível extrair texto principal com Trafilatura.")

    metadados_estruturados = extrair_metadados_estruturados(html_content, url)
    if metadados_estruturados: add_log("INFO", "Metadados estruturados extraídos.", {"metadata_keys": list(metadados_estruturados.keys())})
    else: add_log("INFO", "Nenhum metadado estruturado (JSON-LD, Microdata, Opengraph) encontrado.")

    dados_normalizados_de_meta = _normalizar_dados_de_metadados(metadados_estruturados)
    if dados_normalizados_de_meta: add_log("INFO", "Metadados normalizados.", {"normalized_keys": list(dados_normalizados_de_meta.keys())})

    # Atualizar dados_brutos do produto com o que foi encontrado até agora
    if produto.dados_brutos is None: produto.dados_brutos = {}
    
    # Merge inteligente dos dados normalizados em dados_brutos
    # Prioriza novos valores, mas não sobrescreve com None se já existir algo
    for key, value in dados_normalizados_de_meta.items():
        if value is not None or key not in produto.dados_brutos:
            produto.dados_brutos[key] = value
    
    # Se houver texto principal, tentar usar LLM para refinar/extrair mais campos
    # Esta é uma decisão de design - quais campos a LLM deve tentar preencher?
    # Exemplo: campos que não foram bem preenchidos por metadados ou campos mais subjetivos.
    # campos_para_llm = ["descricao_detalhada_longa", "lista_caracteristicas_beneficios_bullets", "publico_alvo_sugestoes", "palavras_chave_seo_relevantes_lista"]
    
    # Por enquanto, vamos focar em apenas usar os metadados e o texto extraído pelo trafilatura
    # A integração com LLM para extração pode ser um passo futuro ou condicional
    # Se você quiser habilitar a extração LLM aqui, descomente e ajuste a lógica abaixo.
    
    # if texto_principal or dados_normalizados_de_meta:
    #     add_log("INFO", "Tentando extração adicional com LLM.")
    #     # Pegar usuário do produto para chave API
    #     user_owner = produto.owner # Assumindo que produto.owner é o objeto User
    #     dados_llm = await extrair_dados_produto_com_llm(
    #         texto_pagina=texto_principal,
    #         metadados_normalizados=dados_normalizados_de_meta,
    #         campos_desejados=campos_para_llm, 
    #         produto_nome_base=produto.nome_base,
    #         user=user_owner 
    #     )
    #     if dados_llm:
    #         if "erro_llm" in dados_llm or "erro_llm_inesperado" in dados_llm:
    #             add_log("WARNING", "Extração com LLM encontrou um problema.", {"llm_error_details": dados_llm})
    #         else:
    #             add_log("INFO", "Dados extraídos/refinados com LLM.", {"llm_extracted_keys": list(dados_llm.keys())})
    #             for key, value in dados_llm.items():
    #                 # Merge mais uma vez, priorizando LLM se não for erro
    #                 if value is not None or key not in produto.dados_brutos:
    #                     produto.dados_brutos[key] = value
    #     else:
    #         add_log("INFO", "Nenhum dado adicional retornado pela LLM ou LLM desabilitada.")


    # Salva o texto principal se extraído, para referência ou uso posterior
    if texto_principal and isinstance(produto.dados_brutos, dict):
         produto.dados_brutos['texto_pagina_extraido'] = texto_principal[:15000] # Limita o tamanho

    produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
    if not dados_normalizados_de_meta and not texto_principal : # Se nada útil foi extraído
        produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
        add_log("WARNING", "Nenhuma informação útil (metadados ou texto principal) foi extraída da URL.")
    elif not dados_normalizados_de_meta and texto_principal:
         produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS # Apenas texto, sem metadados estruturados
         add_log("INFO", "Enriquecimento concluído com dados parciais (apenas texto da página).")
    else:
        add_log("INFO", "Enriquecimento web concluído com sucesso.")


    produto.log_enriquecimento_web = log_enriquecimento
    db.add(produto)
    db.commit()
    db.refresh(produto)
    db.refresh(produto, attribute_names=['fornecedor']) # Garante que o fornecedor seja carregado se o schema de resposta o incluir
    
    return produto
