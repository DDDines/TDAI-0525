# tdai_project/Backend/services/ia_generation_service.py
import openai
from openai import OpenAIError, APIError, RateLimitError, AuthenticationError, APIConnectionError
from typing import List, Dict, Optional, Any

# CORREÇÃO PRINCIPAL AQUI:
# 'ia_generation_service.py' está em 'Backend/services/'.
# 'core' é uma subpasta de 'Backend/'. Como o CWD é 'Backend/'
# e 'Backend/' está no sys.path, podemos importar 'core.config' diretamente.
from core.config import settings #

# Se 'models.User' fosse necessário aqui (foi removido da assinatura de _call_openai_api)
# e 'models.py' está em 'Backend/', o import seria:
# import models


# Helper para chamadas à API da OpenAI
async def _call_openai_api(
    prompt: str,
    api_key: str,
    model: str = "gpt-3.5-turbo-0125",
    max_tokens: int = 1500,
    temperature: float = 0.7,
    n_choices: int = 1,
    system_message: str = "Você é um assistente de e-commerce especialista em criar textos persuasivos, otimizados para SEO e focados na conversão."
) -> Any:
    if not api_key:
        print("ERRO INTERNO: _call_openai_api chamada sem api_key.")
        raise ValueError("Chave API da OpenAI não fornecida para a chamada.")

    client = openai.AsyncOpenAI(api_key=api_key)

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            n=n_choices,
            stop=None
        )
        
        if n_choices == 1:
            if response.choices and len(response.choices) > 0 and response.choices[0].message.content is not None:
                return response.choices[0].message.content.strip()
            else:
                print("AVISO OpenAI: Nenhuma escolha ou conteúdo vazio retornado pela API.")
                return "Não foi possível obter uma resposta da IA."
        else: 
            if response.choices and len(response.choices) > 0:
                return [choice.message.content.strip() for choice in response.choices if choice.message.content and choice.message.content.strip()]
            else:
                print("AVISO OpenAI: Nenhuma escolha retornada pela API para múltiples N.")
                return []
            
    except AuthenticationError as e:
        print(f"Erro de Autenticação OpenAI: {e}")
        raise ValueError(f"Chave API da OpenAI inválida ou não autorizada. Verifique a chave fornecida.")
    except RateLimitError as e:
        print(f"Erro de Limite de Taxa OpenAI: {e}")
        raise ValueError(f"Limite de taxa da API OpenAI atingido. Tente novamente mais tarde.")
    except APIConnectionError as e:
        print(f"Erro de Conexão OpenAI: {e}")
        raise ValueError(f"Não foi possível conectar à API da OpenAI. Verifique sua conexão.")
    except APIError as e: 
        error_message = e.message if hasattr(e, 'message') and e.message else str(e)
        print(f"Erro da API OpenAI: {e.status_code} - {error_message}")
        raise ValueError(f"Erro ao comunicar com a API da OpenAI ({e.status_code}): {error_message}")
    except OpenAIError as e: 
        print(f"Erro Genérico OpenAI: {e}")
        raise ValueError(f"Erro ao comunicar com a API da OpenAI: {str(e)}")
    except Exception as e:
        import traceback
        print(f"Erro inesperado durante chamada à API OpenAI: {traceback.format_exc()}")
        raise ValueError(f"Erro inesperado ao comunicar com a API da OpenAI.")


async def gerar_titulos_produto_openai(
    dados_produto: Dict[str, Any],
    user_api_key: str,
    idioma: str = "pt-BR",
    quantidade: int = 5
) -> List[str]:
    prompt_parts = [
        f"Produto Principal: {dados_produto.get('nome_base', 'Nome não especificado')}",
    ]
    if dados_produto.get('marca'): prompt_parts.append(f"Marca: {dados_produto.get('marca')}")
    if dados_produto.get('categoria_original'): prompt_parts.append(f"Categoria: {dados_produto.get('categoria_original')}")
    
    dados_brutos = dados_produto.get('dados_brutos', {})
    caracteristicas_prompt = []
    if isinstance(dados_brutos, dict):
        web_data_keys = [k for k in dados_brutos if k.startswith("web_") or k.startswith("meta_") or k.startswith("llm_")]
        if web_data_keys:
            caracteristicas_prompt.append("\nInformações chave extraídas da web:")
            for key in web_data_keys[:5]:
                caracteristicas_prompt.append(f"- {key.replace('web_', '').replace('meta_', '').replace('llm_', '').replace('_', ' ')}: {str(dados_brutos[key])[:100]}")

        elif dados_brutos.get("dados_brutos_originais"):
            caracteristicas_prompt.append("\nCaracterísticas principais (dados originais):")
            original_data = dados_brutos.get("dados_brutos_originais",{})
            count = 0
            for k, v in original_data.items():
                if isinstance(v, str) and len(v) < 100: 
                     caracteristicas_prompt.append(f"- {k}: {v}")
                     count += 1
                if count >= 3: break 
    
    if caracteristicas_prompt:
        prompt_parts.extend(caracteristicas_prompt)

    prompt_parts.append(
        f"\nCom base nas informações acima, gere {quantidade} títulos de produto únicos, curtos (idealmente entre 50-70 caracteres, máximo 80), atraentes e otimizados para SEO em {idioma}. "
        "Os títulos devem destacar os benefícios mais importantes ou características únicas. "
        "Evite repetição excessiva de palavras-chave. Varie a estrutura dos títulos. "
        f"Retorne APENAS os {quantidade} títulos, cada um em uma nova linha, sem numeração, marcadores ou qualquer texto adicional."
    )
    prompt_completo = "\n".join(prompt_parts)
    
    respostas_brutas = await _call_openai_api(
        prompt=prompt_completo,
        api_key=user_api_key,
        n_choices=quantidade,
        max_tokens=quantidade * 40, 
        temperature=0.75
    )
    
    titulos_finais = []
    if isinstance(respostas_brutas, list):
        titulos_validos = [titulo.strip() for titulo in respostas_brutas if titulo and titulo.strip() and len(titulo.strip()) <= 80]
        titulos_finais = titulos_validos[:quantidade]
    elif isinstance(respostas_brutas, str) and quantidade == 1: 
        if respostas_brutas.strip() and len(respostas_brutas.strip()) <= 80:
            titulos_finais = [respostas_brutas.strip()]
    elif isinstance(respostas_brutas, str): 
         titulos_finais = [titulo.strip() for titulo in respostas_brutas.split('\n') if titulo.strip() and len(titulo.strip()) <= 80][:quantidade]
    
    return titulos_finais


async def gerar_descricao_produto_openai(
    dados_produto: Dict[str, Any],
    user_api_key: str,
    idioma: str = "pt-BR"
) -> str:
    prompt_parts = [
        f"Crie uma descrição de produto extremamente detalhada, rica em informações, persuasiva e otimizada para SEO em {idioma}. A descrição deve ser adequada para uma página de produto de e-commerce.",
        f"\nProduto Principal: {dados_produto.get('nome_base', 'Nome não especificado')}",
    ]
    if dados_produto.get('marca'): prompt_parts.append(f"Marca: {dados_produto.get('marca')}")
    if dados_produto.get('categoria_original'): prompt_parts.append(f"Categoria Inicial: {dados_produto.get('categoria_original')}")

    dados_brutos = dados_produto.get('dados_brutos', {})
    if isinstance(dados_brutos, dict) and dados_brutos:
        prompt_parts.append("\nContexto Adicional (use estas informações para criar a descrição):")
        for chave, valor in dados_brutos.items():
            valor_str = str(valor)
            if len(valor_str) > 300: 
                valor_str = valor_str[:300] + "..."
            prompt_parts.append(f"- {chave.replace('_', ' ').capitalize()}: {valor_str}")
    
    prompt_parts.append(
        f"\nInstruções para a Descrição (em {idioma}):"
        "\n- Comprimento: Entre 1500 e 3000 caracteres."
        "\n- Estrutura: Use parágrafos bem formados. Comece com uma introdução cativante. Detalhe as principais características e benefícios. Se houver especificações técnicas importantes, liste-as de forma clara (pode usar marcadores se apropriado)."
        "\n- Tom de Voz: Profissional, informativo e vendedor."
        "\n- SEO: Incorpore palavras-chave relevantes naturalmente (baseadas no nome, marca, categoria e características)."
        "\n- Não inclua o preço ou informações de disponibilidade, a menos que explicitamente pedido."
        "\n- Evite frases genéricas. Seja específico sobre o produto."
        "\n- Conclua com um parágrafo que reforce o valor do produto."
        "\nRetorne APENAS a descrição completa, sem qualquer texto introdutório ou de fechamento seu (como 'Aqui está a descrição:' ou similar)."
    )
    prompt_completo = "\n".join(prompt_parts)

    max_tokens_descricao = 1000 
    if idioma != "en": 
        max_tokens_descricao = int(max_tokens_descricao * 1.5) 

    result = await _call_openai_api(
        prompt=prompt_completo,
        api_key=user_api_key,
        max_tokens=max_tokens_descricao,
        temperature=0.65
    )
    return str(result) if result is not None else "Não foi possível gerar a descrição."