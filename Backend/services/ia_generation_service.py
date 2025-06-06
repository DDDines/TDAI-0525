# Backend/services/ia_generation_service.py

import httpx
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging
import re

from jose import JWTError, jwt
from fastapi import HTTPException, status

import crud
import models
import schemas
from core.config import settings
from . import limit_service

# Configuração do logger
logger = logging.getLogger(__name__)

# --- Constantes para APIs ---
OPENAI_API_URL_COMPLETIONS = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo"
GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/"

# --- Funções de Chave de API ---

async def get_openai_api_key(db: Session, user: models.User) -> Optional[str]:
    """Obtém a chave da API OpenAI, priorizando a do usuário."""
    if user.chave_openai_pessoal:
        logger.info(f"Usando chave OpenAI pessoal para usuário ID: {user.id}")
        return user.chave_openai_pessoal
    if settings.OPENAI_API_KEY:
        logger.info("Usando chave OpenAI global do sistema.")
        return settings.OPENAI_API_KEY
    logger.warning("Nenhuma chave OpenAI encontrada (nem pessoal, nem global).")
    return None

async def get_gemini_api_key(db: Session, user: models.User) -> Optional[str]:
    """Obtém a chave da API Gemini, priorizando a do usuário."""
    if user.chave_google_gemini_pessoal:
        logger.info(f"Usando chave Gemini pessoal para usuário ID: {user.id}")
        return user.chave_google_gemini_pessoal
    if settings.GOOGLE_GEMINI_API_KEY:
        logger.info("Usando chave Gemini global do sistema.")
        return settings.GOOGLE_GEMINI_API_KEY
    logger.warning("Nenhuma chave Gemini encontrada (nem pessoal, nem global).")
    return None

# --- Funções Auxiliares de Chamada de API ---

async def _call_gemini_api(
    prompt_text: str,
    api_key: str,
    model_name: str = "gemini-1.5-flash-latest",
    response_schema: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7
) -> str:
    """
    Função genérica e robusta para chamar a API Gemini.
    Pode retornar JSON (se response_schema for fornecido) ou texto.
    """
    if not api_key:
        raise ValueError("Chave da API Gemini não fornecida.")

    gemini_api_endpoint = f"{GEMINI_API_BASE_URL}{model_name}:generateContent"
    headers = {"Content-Type": "application/json"}
    
    generation_config = {"temperature": temperature}
    if response_schema:
        generation_config["responseMimeType"] = "application/json"
        generation_config["responseSchema"] = response_schema

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
        "generationConfig": generation_config
    }
    
    url_com_chave = f"{gemini_api_endpoint}?key={api_key}"
    logger.info(f"Chamando Gemini API (Modelo: {model_name}) para gerar conteúdo.")

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            response = await client.post(url_com_chave, json=payload, headers=headers)
            response.raise_for_status()
            
            api_response_data = response.json()
            
            if (api_response_data.get("candidates") and
                api_response_data["candidates"][0].get("content", {}).get("parts")):
                
                return api_response_data["candidates"][0]["content"]["parts"][0].get("text", "")
            else:
                error_detail = "Resposta da API Gemini não contém o conteúdo esperado."
                if fb := api_response_data.get("promptFeedback"):
                    error_detail += f" Feedback do prompt: {fb}"
                logger.error(f"Estrutura inesperada da resposta da Gemini: {error_detail}")
                raise ValueError(error_detail)
        except httpx.HTTPStatusError as e:
            error_text = e.response.text
            logger.error(f"Erro na API Gemini (HTTPStatusError): {e.response.status_code} - {error_text}", exc_info=True)
            raise ValueError(f"Erro na API Gemini ({e.response.status_code}): {error_text}")
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar API Gemini: {str(e)}", exc_info=True)
            raise ValueError(f"Erro inesperado ao comunicar com Gemini: {str(e)}")


async def call_openai_api(
    prompt_messages: List[Dict[str, str]],
    api_key: str,
    model: str = OPENAI_DEFAULT_MODEL,
    temperature: float = 0.7,
    max_tokens: int = 500
) -> str:
    """Faz uma chamada para a API de Chat Completions da OpenAI."""
    # (código original mantido para compatibilidade, se necessário)
    if not api_key:
        raise ValueError("Chave da API OpenAI não configurada.")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": prompt_messages, "temperature": temperature, "max_tokens": max_tokens}
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(OPENAI_API_URL_COMPLETIONS, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
        except httpx.HTTPStatusError as e:
            raise ValueError(f"Erro na API OpenAI: {e.response.text}")
        except Exception as e:
            raise ValueError(f"Erro inesperado na OpenAI: {str(e)}")

# --- NOVAS Funções de Geração com Gemini ---

async def gerar_titulos_com_gemini(db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
    """Gera títulos de produto usando a API Gemini."""
    logger.info(f"Iniciando geração de TÍTULOS com Gemini para produto ID {produto_id}")
    api_key = await get_gemini_api_key(db, user)
    if not api_key:
        raise ValueError("Chave da API Gemini não configurada.")

    db_produto = crud.get_produto(db, produto_id=produto_id)
    if not db_produto:
        raise ValueError("Produto não encontrado")

    # Coleta de contexto
    contexto = (
        f"Nome Base: {db_produto.nome_base}\n"
        f"Marca: {db_produto.marca or 'Não especificada'}\n"
        f"Categoria: {db_produto.categoria_original or 'Não especificada'}\n"
        f"Descrição Curta: {db_produto.descricao_original or 'Sem descrição'}\n"
        f"Atributos: {json.dumps(db_produto.dynamic_attributes, ensure_ascii=False) if db_produto.dynamic_attributes else 'N/A'}"
    )

    prompt = (
        "Você é um especialista em SEO e copywriting para e-commerce. "
        f"Analise o seguinte produto:\n---\n{contexto}\n---\n"
        f"Crie {num_titulos} opções de títulos de produto otimizados para busca e conversão. "
        "Os títulos devem ser claros, atrativos e incluir palavras-chave relevantes. "
        "Sua resposta DEVE ser um objeto JSON com uma única chave 'titulos', que contém uma lista de strings, onde cada string é um título sugerido."
    )

    schema_resposta = {
        "type": "OBJECT",
        "properties": {
            "titulos": {"type": "ARRAY", "items": {"type": "STRING"}}
        },
        "required": ["titulos"]
    }
    
    try:
        resposta_str = await _call_gemini_api(prompt, api_key, response_schema=schema_resposta)
        resposta_json = json.loads(resposta_str)
        titulos_gerados = resposta_json.get("titulos", [])
        
        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_TITULO_PRODUTO,
            provedor_ia="gemini", modelo_ia="gemini-1.5-flash-latest", creditos_consumidos=1
        ))
        return titulos_gerados
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao gerar títulos com Gemini para produto {produto_id}: {e}")
        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_TITULO_PRODUTO,
            provedor_ia="gemini", status="FALHA", detalhes_erro=str(e)
        ))
        return []

async def gerar_descricao_com_gemini(db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
    """Gera descrição de produto usando a API Gemini."""
    logger.info(f"Iniciando geração de DESCRIÇÃO com Gemini para produto ID {produto_id}")
    api_key = await get_gemini_api_key(db, user)
    if not api_key:
        raise ValueError("Chave da API Gemini não configurada.")

    db_produto = crud.get_produto(db, produto_id=produto_id)
    if not db_produto:
        raise ValueError("Produto não encontrado")

    # Coleta de contexto
    contexto = (
        f"Produto: {db_produto.nome_base}\n"
        f"Marca: {db_produto.marca or 'Não especificada'}\n"
        f"Modelo: {db_produto.modelo or 'Não especificado'}\n"
        f"Informações Adicionais: {db_produto.descricao_original or ''}\n"
        f"Atributos Técnicos: {json.dumps(db_produto.dynamic_attributes, ensure_ascii=False) if db_produto.dynamic_attributes else 'N/A'}"
    )

    prompt = (
        "Você é um copywriter especialista em e-commerce. "
        f"Crie uma descrição de produto persuasiva e detalhada, com aproximadamente {tamanho_palavras} palavras, para o item a seguir. "
        "Destaque os principais benefícios, características técnicas e para quem o produto é ideal. "
        "Use parágrafos curtos e, se apropriado, listas de tópicos (bullet points) para facilitar a leitura. "
        f"NÃO inclua o nome do produto no início da descrição. Foque apenas no corpo do texto.\n---\n{contexto}\n---"
    )

    try:
        descricao_gerada = await _call_gemini_api(prompt, api_key, temperature=0.8) # Um pouco mais criativo
        
        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_DESCRICAO_PRODUTO,
            provedor_ia="gemini", modelo_ia="gemini-1.5-flash-latest", creditos_consumidos=1
        ))
        return descricao_gerada
    except ValueError as e:
        logger.error(f"Erro ao gerar descrição com Gemini para produto {produto_id}: {e}")
        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_DESCRICAO_PRODUTO,
            provedor_ia="gemini", status="FALHA", detalhes_erro=str(e)
        ))
        return ""


# --- Funções Legadas (OpenAI) - Manter para referência ou fallback ---

# @deprecated("Usar gerar_titulos_com_gemini")
async def gerar_titulos_com_openai(db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
    logger.warning("Função legada 'gerar_titulos_com_openai' foi chamada.")
    # (código original da função openai aqui, se desejar manter)
    return ["Título (OpenAI) 1", "Título (OpenAI) 2"]

# @deprecated("Usar gerar_descricao_com_gemini")
async def gerar_descricao_com_openai(db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
    logger.warning("Função legada 'gerar_descricao_com_openai' foi chamada.")
    # (código original da função openai aqui, se desejar manter)
    return "Descrição gerada pela API legada da OpenAI."

# --- Função de Sugestão de Atributos com Gemini (já implementada) ---

async def sugerir_valores_atributos_com_gemini(
    db: Session,
    produto_id: int,
    user: models.User
) -> schemas.SugestoesAtributosResponse:
    """Gera sugestões de valores para os atributos de um produto usando a API Gemini."""
    logger.info(f"Iniciando sugestão de atributos com Gemini para produto ID {produto_id}")
    
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if not db_produto:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto.user_id != user.id and not user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado")

    chaves_para_sugerir = []
    if db_produto.product_type and db_produto.product_type.attribute_templates:
        chaves_para_sugerir = [attr.attribute_key for attr in db_produto.product_type.attribute_templates if attr.attribute_key]
    
    if not chaves_para_sugerir:
        return schemas.SugestoesAtributosResponse(sugestoes_atributos=[], produto_id=produto_id, modelo_ia_utilizado="gemini (não chamado)")

    contexto = (
        f"Nome do Produto: {db_produto.nome_base}\n"
        f"Descrição: {db_produto.descricao_original or db_produto.descricao_chat_api or 'N/A'}\n"
        f"Marca: {db_produto.marca or 'N/A'}\n"
        f"SKU: {db_produto.sku or 'N/A'}"
    )
    
    lista_chaves_str = ", ".join([f"'{chave}'" for chave in chaves_para_sugerir])
    prompt_final = (
        f"Analise as informações sobre o seguinte produto:\n---\n{contexto}\n---\n"
        f"Sugira valores para os seguintes atributos: {lista_chaves_str}.\n"
        "Sua resposta DEVE ser um objeto JSON com uma única chave 'sugestoes_atributos', contendo uma lista de objetos. "
        "Cada objeto deve ter 'chave_atributo' e 'valor_sugerido'. Se não puder sugerir um valor, omita o atributo da lista."
    )
    
    gemini_response_schema = {
        "type": "OBJECT", "properties": {
            "sugestoes_atributos": { "type": "ARRAY", "items": {
                "type": "OBJECT", "properties": {
                    "chave_atributo": {"type": "STRING"},
                    "valor_sugerido": {"type": "STRING"}
                }, "required": ["chave_atributo", "valor_sugerido"]
            }}
        }, "required": ["sugestoes_atributos"]
    }

    gemini_api_key = await get_gemini_api_key(db, user)
    modelo_utilizado = "gemini-1.5-flash-latest"

    try:
        sugestoes_str = await _call_gemini_api(prompt_final, gemini_api_key, response_schema=gemini_response_schema, model_name=modelo_utilizado)
        sugestoes_dict = json.loads(sugestoes_str)
        
        sugestoes_finais = [schemas.SugestaoAtributoItem(**item) for item in sugestoes_dict.get("sugestoes_atributos", []) if item.get("chave_atributo") in chaves_para_sugerir]

        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.SUGESTAO_ATRIBUTOS_GEMINI,
            provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=1, status="SUCESSO"
        ))
        
        return schemas.SugestoesAtributosResponse(
            sugestoes_atributos=sugestoes_finais,
            produto_id=produto_id,
            modelo_ia_utilizado=modelo_utilizado
        )
    except Exception as e:
        logger.error(f"Erro no serviço de sugestão Gemini para produto {produto_id}: {e}", exc_info=True)
        crud.create_registro_uso_ia(db, registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoIAEnum.SUGESTAO_ATRIBUTOS_GEMINI,
            provedor_ia="gemini", modelo_ia=modelo_utilizado, status="FALHA", detalhes_erro=str(e)
        ))
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro ao gerar sugestões: {str(e)}")