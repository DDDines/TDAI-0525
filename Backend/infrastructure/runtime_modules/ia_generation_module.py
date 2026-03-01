# Backend/infrastructure/runtime_modules/ia_generation_module.py

import httpx # Para chamadas HTTP assÃƒÂ­ncronas
import json
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging # Adicionado para logging

from fastapi import HTTPException, status

from Backend import models  # models completo para acesso a TipoAcaoEnum
from Backend import schemas
from Backend.core.config import settings
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)

# ConfiguraÃƒÂ§ÃƒÂ£o do logger
logger = logging.getLogger(__name__)

# --- Constantes para OpenAI (Exemplo, idealmente viriam de settings) ---
OPENAI_API_URL_COMPLETIONS = "https://api.openai.com/v1/chat/completions"
OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo" # Ou o modelo que vocÃƒÂª preferir/tiver acesso

# --- Constantes para Gemini (Exemplo, idealmente viriam de settings) ---
# AtenÃƒÂ§ÃƒÂ£o: Verifique a URL correta e o modelo exato para a sua necessidade.
# Modelos "flash" sÃƒÂ£o mais rÃƒÂ¡pidos e baratos, "pro" sÃƒÂ£o mais capazes.
# gemini-1.5-flash-latest ou gemini-1.5-pro-latest ou um especÃƒÂ­fico como gemini-1.0-pro
GEMINI_API_URL_GENERATE_CONTENT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"


class _AiProviderWorkflow:
    """Workflow OO para operaÃƒÂ§ÃƒÂµes de provedor IA (chaves e chamadas HTTP)."""

    def __init__(self, runtime: Optional["_AiProviderRuntime"] = None) -> None:
        self._runtime = runtime or _AiProviderRuntime()

    async def get_openai_api_key(self, db: Session, user: models.User) -> Optional[str]:
        return await self._runtime.get_openai_api_key(db=db, user=user)

    async def get_gemini_api_key(self, db: Session, user: models.User) -> Optional[str]:
        return await self._runtime.get_gemini_api_key(db=db, user=user)

    async def call_openai_api(
        self,
        prompt_messages: List[Dict[str, str]],
        api_key: str,
        model: str = OPENAI_DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        return await self._runtime.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def call_gemini_api_for_suggestions(
        self,
        prompt_text: str,
        api_key: str,
        response_schema: Dict[str, Any],
        model_name: str = "gemini-1.5-flash-latest",
    ) -> Dict[str, Any]:
        return await self._runtime.call_gemini_api_for_suggestions(
            prompt_text=prompt_text,
            api_key=api_key,
            response_schema=response_schema,
            model_name=model_name,
        )

    async def call_gemini_api(
        self,
        prompt_text: str,
        api_key: str,
        model_name: str = "gemini-1.5-flash-latest",
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> str:
        return await self._runtime.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class _AiProviderRuntime:
    """Runtime OO para integracoes com provedores IA."""

    async def get_openai_api_key(
        self, db: Session, user: models.User
    ) -> Optional[str]:
        if user.chave_openai_pessoal:
            logger.info(f"Usando chave OpenAI pessoal para usuÃƒÆ’Ã‚Â¡rio ID: {user.id}")
            return user.chave_openai_pessoal
        if settings.OPENAI_API_KEY:
            logger.info("Usando chave OpenAI global do sistema.")
            return settings.OPENAI_API_KEY
        logger.warning("Nenhuma chave OpenAI encontrada (nem pessoal, nem global).")
        return None

    async def get_gemini_api_key(
        self, db: Session, user: models.User
    ) -> Optional[str]:
        if user.chave_google_gemini_pessoal:
            logger.info(f"Usando chave Gemini pessoal para usuÃƒÆ’Ã‚Â¡rio ID: {user.id}")
            return user.chave_google_gemini_pessoal

        if settings.GOOGLE_GEMINI_API_KEY:
            logger.info("Usando chave Gemini global do sistema.")
            return settings.GOOGLE_GEMINI_API_KEY

        logger.warning("Nenhuma chave Gemini encontrada (nem pessoal, nem global).")
        return None

    async def call_openai_api(
        self,
        prompt_messages: List[Dict[str, str]],
        api_key: str,
        model: str = OPENAI_DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API OpenAI nÃƒÆ’Ã‚Â£o configurada.",
            )

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": prompt_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                logger.info(
                    f"Chamando OpenAI API. Modelo: {model}, Tokens MÃƒÆ’Ã‚Â¡x: {max_tokens}, Temp: {temperature}"
                )
                response = await client.post(
                    OPENAI_API_URL_COMPLETIONS,
                    json=payload,
                    headers=headers,
                )
                response.raise_for_status()
                api_response_data = response.json()

                if api_response_data.get("choices") and len(api_response_data["choices"]) > 0:
                    content = api_response_data["choices"][0].get("message", {}).get("content", "")
                    return content.strip()

                logger.error(
                    "Resposta da API OpenAI nÃƒÆ’Ã‚Â£o contÃƒÆ’Ã‚Â©m 'choices' ou 'choices' estÃƒÆ’Ã‚Â¡ vazio: %s",
                    api_response_data,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Resposta inesperada da API OpenAI.",
                )
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Erro na API OpenAI: {e.response.status_code} - {e.response.text}",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Erro na API OpenAI: {e.response.text}",
                )
            except Exception as e:
                logger.error(f"Erro inesperado ao chamar API OpenAI: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro inesperado ao comunicar com OpenAI: {str(e)}",
                )

    async def call_gemini_api_for_suggestions(
        self,
        prompt_text: str,
        api_key: str,
        response_schema: Dict[str, Any],
        model_name: str = "gemini-1.5-flash-latest",
    ) -> Dict[str, Any]:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API Gemini nÃƒÆ’Ã‚Â£o configurada.",
            )

        gemini_api_endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        )
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": response_schema,
                "temperature": 0.6,
            },
        }

        url_com_chave = f"{gemini_api_endpoint}?key={api_key}"
        logger.info(f"Chamando Gemini API: {url_com_chave} com schema e prompt.")

        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url_com_chave, json=payload, headers=headers)
                response.raise_for_status()
                api_response_data = response.json()

                if (
                    api_response_data.get("candidates")
                    and len(api_response_data["candidates"]) > 0
                    and api_response_data["candidates"][0].get("content")
                    and api_response_data["candidates"][0]["content"].get("parts")
                    and len(api_response_data["candidates"][0]["content"]["parts"]) > 0
                    and api_response_data["candidates"][0]["content"]["parts"][0].get("text")
                ):
                    json_text_response = api_response_data["candidates"][0]["content"]["parts"][0]["text"]
                    try:
                        return json.loads(json_text_response)
                    except json.JSONDecodeError as jde:
                        logger.error(
                            f"Erro ao decodificar JSON da resposta da Gemini: {jde}. Resposta: {json_text_response}",
                            exc_info=True,
                        )
                        raise HTTPException(
                            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Resposta da API Gemini nÃƒÆ’Ã‚Â£o ÃƒÆ’Ã‚Â© um JSON vÃƒÆ’Ã‚Â¡lido.",
                        )

                error_detail = "Resposta da API Gemini nÃƒÆ’Ã‚Â£o contÃƒÆ’Ã‚Â©m o conteÃƒÆ’Ã‚Âºdo esperado."
                if api_response_data.get("promptFeedback"):
                    error_detail += f" Feedback do prompt: {api_response_data['promptFeedback']}"
                logger.error(
                    "Estrutura inesperada da resposta da Gemini: %s. Resposta completa: %s",
                    error_detail,
                    api_response_data,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=error_detail,
                )

            except httpx.HTTPStatusError as e:
                error_text = e.response.text
                logger.error(
                    f"Erro na API Gemini (HTTPStatusError): {e.response.status_code} - {error_text}",
                    exc_info=True,
                )
                error_detail = f"Erro na API Gemini: {e.response.status_code}"
                try:
                    error_data = e.response.json()
                    if error_data and "error" in error_data and "message" in error_data["error"]:
                        error_detail = f"Erro na API Gemini: {error_data['error']['message']}"
                except Exception:
                    error_detail += f" - {error_text}"
                raise HTTPException(status_code=e.response.status_code, detail=error_detail)
            except Exception as e:
                logger.error(f"Erro inesperado ao chamar API Gemini: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro inesperado ao comunicar com Gemini: {str(e)}",
                )

    async def call_gemini_api(
        self,
        prompt_text: str,
        api_key: str,
        model_name: str = "gemini-1.5-flash-latest",
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> str:
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API Gemini nÃƒÆ’Ã‚Â£o configurada.",
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        url = f"{endpoint}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=90.0) as client:
            try:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
                if (
                    data.get("candidates")
                    and data["candidates"]
                    and data["candidates"][0].get("content")
                    and data["candidates"][0]["content"].get("parts")
                    and data["candidates"][0]["content"]["parts"]
                ):
                    return data["candidates"][0]["content"]["parts"][0].get("text", "").strip()
                logger.error(f"Estrutura inesperada na resposta Gemini: {data}")
                raise HTTPException(
                    status_code=500,
                    detail="Resposta inesperada da API Gemini",
                )
            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Erro na API Gemini: {e.response.status_code} - {e.response.text}",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=e.response.status_code,
                    detail=f"Erro na API Gemini: {e.response.text}",
                )
            except Exception as e:
                logger.error(f"Erro inesperado ao chamar API Gemini: {str(e)}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro inesperado ao comunicar com Gemini: {str(e)}",
                )


AiProviderWorkflow = _AiProviderWorkflow


# --- NOVA FUNÃƒâ€¡ÃƒÆ’O PARA SUGESTÃƒâ€¢ES GEMINI ---
class _IAGenerationWorkflow:
    """Workflow OO para operaÃƒÂ§ÃƒÂµes de geraÃƒÂ§ÃƒÂ£o de conteÃƒÂºdo IA."""

    def __init__(self, runtime: Optional["_IAGenerationRuntime"] = None) -> None:
        self._runtime = runtime or _IAGenerationRuntime()

    async def gerar_titulos_com_openai(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        return await self._runtime.gerar_titulos_com_openai(
            db=db,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_openai(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        return await self._runtime.gerar_descricao_com_openai(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        return await self._runtime.gerar_titulos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_gemini(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        return await self._runtime.gerar_descricao_com_gemini(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def sugerir_valores_atributos_com_gemini(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        return await self._runtime.sugerir_valores_atributos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=user,
        )


class _IAGenerationRuntime:
    """Runtime OO para operacoes de geracao de conteudo IA."""

    async def gerar_titulos_com_openai(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        return await self._gerar_titulos_com_openai_impl(
            db=db,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_openai(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        return await self._gerar_descricao_com_openai_impl(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        return await self._gerar_titulos_com_gemini_impl(
            db=db,
            produto_id=produto_id,
            user=user,
            num_titulos=num_titulos,
        )

    async def gerar_descricao_com_gemini(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
        tamanho_palavras: int = 150,
    ) -> str:
        return await self._gerar_descricao_com_gemini_impl(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def sugerir_valores_atributos_com_gemini(
        self,
        db: Session,
        produto_id: int,
        user: models.User,
    ) -> schemas.SugestoesAtributosResponse:
        return await self._sugerir_valores_atributos_com_gemini_impl(
            db=db,
            produto_id=produto_id,
            user=user,
        )

    @staticmethod
    def _get_ai_provider_workflow() -> _AiProviderWorkflow:
        return _AiProviderWorkflow(runtime=_AiProviderRuntime())

    async def _gerar_titulos_com_openai_impl(self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
        # ... (cÃƒÂ³digo existente para gerar tÃƒÂ­tulos com OpenAI - manter como estÃƒÂ¡)
        # Apenas garanta que ele use get_openai_api_key e registre o uso corretamente
        logger.info(f"Iniciando geraÃƒÂ§ÃƒÂ£o de tÃƒÂ­tulos para produto ID {produto_id} pelo usuÃƒÂ¡rio ID {user.id}")
        # ... (restante da lÃƒÂ³gica existente) ...
        # Exemplo de adaptaÃƒÂ§ÃƒÂ£o mÃƒÂ­nima:
        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_openai_api_key(db=db, user=user)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chave da API OpenAI nÃƒÂ£o disponÃƒÂ­vel.")
    
        # ... (construÃƒÂ§ÃƒÂ£o do prompt e chamada ÃƒÂ  API OpenAI) ...
        # ... (registro do uso com crud.create_registro_uso_ia) ...
        # Este cÃƒÂ³digo ÃƒÂ© apenas um placeholder, o seu cÃƒÂ³digo original para esta funÃƒÂ§ÃƒÂ£o deve ser mantido e adaptado.
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nÃƒÂ£o encontrado")
    
        prompt_messages = [
            {"role": "system", "content": f"VocÃƒÂª ÃƒÂ© um especialista em copywriting para e-commerce. Gere {num_titulos} opÃƒÂ§ÃƒÂµes de tÃƒÂ­tulos curtos, atraentes e otimizados para SEO para o produto a seguir."},
            {"role": "user", "content": f"Produto: {db_produto.nome_base}. DescriÃƒÂ§ÃƒÂ£o: {db_produto.descricao_original or db_produto.descricao_chat_api or ''}. Marca: {db_produto.marca or ''}."}
        ]
        
        titulos_str = await ai_provider_workflow.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key,
            max_tokens=150 * num_titulos,
        )
        titulos_list = [t.strip() for t in titulos_str.split('\n') if t.strip()]
    
        RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            provedor_ia="openai", modelo_ia=OPENAI_DEFAULT_MODEL, creditos_consumidos=1 # Ajustar crÃƒÂ©ditos
        ))
        return titulos_list[:num_titulos]

    async def _gerar_descricao_com_openai_impl(self, db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
        # ... (cÃƒÂ³digo existente para gerar descriÃƒÂ§ÃƒÂ£o com OpenAI - manter como estÃƒÂ¡)
        # Apenas garanta que ele use get_openai_api_key e registre o uso corretamente
        logger.info(f"Iniciando geraÃƒÂ§ÃƒÂ£o de descriÃƒÂ§ÃƒÂ£o para produto ID {produto_id} pelo usuÃƒÂ¡rio ID {user.id}")
        # ... (restante da lÃƒÂ³gica existente) ...
        # Exemplo de adaptaÃƒÂ§ÃƒÂ£o mÃƒÂ­nima:
        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_openai_api_key(db=db, user=user)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chave da API OpenAI nÃƒÂ£o disponÃƒÂ­vel.")
            
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nÃƒÂ£o encontrado")
    
        prompt_messages = [
            {"role": "system", "content": f"VocÃƒÂª ÃƒÂ© um copywriter especialista em e-commerce. Crie uma descriÃƒÂ§ÃƒÂ£o de produto persuasiva e detalhada, com aproximadamente {tamanho_palavras} palavras, para o item a seguir. Destaque benefÃƒÂ­cios e caracterÃƒÂ­sticas chave."},
            {"role": "user", "content": f"Produto: {db_produto.nome_base}. InformaÃƒÂ§ÃƒÂµes adicionais: {db_produto.descricao_original or ''}. Marca: {db_produto.marca or ''}. Modelo: {db_produto.modelo or ''}."}
        ]
        
        descricao = await ai_provider_workflow.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key,
            max_tokens=tamanho_palavras + 100,
        )
    
        RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
            provedor_ia="openai", modelo_ia=OPENAI_DEFAULT_MODEL, creditos_consumidos=1 # Ajustar crÃƒÂ©ditos
        ))
        return descricao

    async def _gerar_titulos_com_gemini_impl(self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
        """Gera tÃƒÂ­tulos usando a API Gemini."""
        logger.info(f"Iniciando geraÃƒÂ§ÃƒÂ£o de tÃƒÂ­tulos Gemini para produto ID {produto_id} pelo usuÃƒÂ¡rio ID {user.id}")
        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_gemini_api_key(db=db, user=user)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chave da API Gemini nÃƒÂ£o disponÃƒÂ­vel.")
    
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nÃƒÂ£o encontrado")
    
        prompt_text = (
            f"Crie {num_titulos} sugestÃƒÂµes de tÃƒÂ­tulos curtos e atrativos para o seguinte produto:\n"
            f"Nome: {db_produto.nome_base}\n"
            f"DescriÃƒÂ§ÃƒÂ£o: {db_produto.descricao_original or db_produto.descricao_chat_api or ''}\n"
            f"Marca: {db_produto.marca or ''}"
        )
    
        resultado = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=150 * num_titulos,
        )
        titulos_list = [t.strip() for t in resultado.split('\n') if t.strip()]
    
        RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id,
            produto_id=produto_id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            provedor_ia="gemini",
            modelo_ia="gemini-1.5-flash-latest",
            creditos_consumidos=1,
        ))
        return titulos_list[:num_titulos]

    async def _gerar_descricao_com_gemini_impl(self, db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
        """Gera descriÃƒÂ§ÃƒÂ£o usando a API Gemini."""
        logger.info(f"Iniciando geraÃƒÂ§ÃƒÂ£o de descriÃƒÂ§ÃƒÂ£o Gemini para produto ID {produto_id} pelo usuÃƒÂ¡rio ID {user.id}")
        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_gemini_api_key(db=db, user=user)
        if not api_key:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Chave da API Gemini nÃƒÂ£o disponÃƒÂ­vel.")
    
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nÃƒÂ£o encontrado")
    
        prompt_text = (
            f"Escreva uma descriÃƒÂ§ÃƒÂ£o de aproximadamente {tamanho_palavras} palavras para o seguinte produto:\n"
            f"Nome: {db_produto.nome_base}\n"
            f"InformaÃƒÂ§ÃƒÂµes adicionais: {db_produto.descricao_original or ''}\n"
            f"Marca: {db_produto.marca or ''}\n"
            f"Modelo: {db_produto.modelo or ''}"
        )
    
        descricao = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=tamanho_palavras + 100,
        )
    
        RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
            user_id=user.id,
            produto_id=produto_id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
            provedor_ia="gemini",
            modelo_ia="gemini-1.5-flash-latest",
            creditos_consumidos=1,
        ))
        return descricao

    async def _sugerir_valores_atributos_com_gemini_impl(self, 
        db: Session,
        produto_id: int,
        user: models.User
    ) -> schemas.SugestoesAtributosResponse:
        """
        Gera sugestÃƒÂµes de valores para os atributos de um produto usando a API Gemini,
        baseado nos AttributeTemplates do ProductType do produto.
        """
        logger.info(f"Iniciando sugestÃƒÂ£o de atributos com Gemini para produto ID {produto_id} por usuÃƒÂ¡rio ID {user.id}")
        
        # 1. Verificar crÃƒÂ©ditos do usuÃƒÂ¡rio
        creditos_necessarios = settings.CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI if hasattr(settings, 'CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI') else 1 # Custo padrÃƒÂ£o de 1 crÃƒÂ©dito
        # A verificaÃƒÂ§ÃƒÂ£o de crÃƒÂ©dito foi movida para o router para uma resposta mais imediata ao usuÃƒÂ¡rio.
        # No entanto, pode ser mantida aqui como uma segunda camada de seguranÃƒÂ§a.
        # if not await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, creditos_necessarios):
        #     logger.warning(f"UsuÃƒÂ¡rio ID {user.id} com crÃƒÂ©ditos insuficientes para sugestÃƒÂ£o de atributos (necessÃƒÂ¡rio: {creditos_necessarios}).")
        #     raise HTTPException(...)
    
        # 2. Buscar Produto e seus AttributeTemplates
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            logger.error(f"Produto ID {produto_id} nÃƒÂ£o encontrado para sugestÃƒÂ£o de atributos.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃƒÂ£o encontrado")
        if db_produto.user_id != user.id and not user.is_superuser:
            logger.warning(f"UsuÃƒÂ¡rio ID {user.id} nÃƒÂ£o autorizado a acessar produto ID {produto_id} para sugestÃƒÂ£o.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NÃƒÂ£o autorizado a acessar este produto")
    
        chaves_para_sugerir = []
        if db_produto.product_type and db_produto.product_type.attribute_templates:
            chaves_para_sugerir = [attr.attribute_key for attr in db_produto.product_type.attribute_templates if attr.attribute_key]
        
        if not chaves_para_sugerir:
            logger.info(f"Nenhum atributo definido no Tipo de Produto para produto ID {produto_id}. Retornando sugestÃƒÂµes vazias.")
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", creditos_consumidos=0, status="INFO", # NÃƒÂ£o consumiu crÃƒÂ©ditos se nÃƒÂ£o houve chamada
                detalhes_erro="Nenhum atributo definido no Tipo de Produto para gerar sugestÃƒÂµes."
            ))
            return schemas.SugestoesAtributosResponse(sugestoes_atributos=[], produto_id=produto_id, modelo_ia_utilizado="gemini (nÃƒÂ£o chamado)")
    
        # 3. Coletar Contexto do Produto
        contexto = f"Nome do Produto: {db_produto.nome_base or db_produto.nome_chat_api or 'N/A'}\n"
        contexto += f"DescriÃƒÂ§ÃƒÂ£o: {db_produto.descricao_chat_api or db_produto.descricao_original or 'N/A'}\n"
        if db_produto.marca: contexto += f"Marca: {db_produto.marca}\n"
        if db_produto.modelo: contexto += f"Modelo: {db_produto.modelo}\n"
        if db_produto.sku: contexto += f"SKU: {db_produto.sku}\n"
        if db_produto.ean: contexto += f"EAN: {db_produto.ean}\n"
        if db_produto.categoria_original: contexto += f"Categoria: {db_produto.categoria_original}\n"
        
        if db_produto.dynamic_attributes and isinstance(db_produto.dynamic_attributes, dict):
            contexto += "Atributos atuais:\n"
            for key, value in db_produto.dynamic_attributes.items():
                contexto += f"- {key}: {value}\n"
    
        if db_produto.dados_brutos_web and isinstance(db_produto.dados_brutos_web, dict):
            web_text = db_produto.dados_brutos_web.get("extracted_text_content", "") # Assumindo essa chave
            if web_text:
                contexto += f"\nInformaÃƒÂ§ÃƒÂµes adicionais da web (primeiros 1000 caracteres):\n{str(web_text)[:1000]}...\n"
    
        # 4. Construir Prompt para Gemini
        lista_chaves_str = "\n".join([f"- '{chave}'" for chave in chaves_para_sugerir])
        prompt_final = (
            f"Analise as seguintes informaÃƒÂ§ÃƒÂµes sobre um produto:\n---\n{contexto}\n---\n\n"
            f"Com base nesta anÃƒÂ¡lise, sugira valores apropriados para os seguintes atributos definidos (use as chaves exatamente como listadas):\n{lista_chaves_str}\n\n"
            "Seu objetivo ÃƒÂ© preencher esses atributos com informaÃƒÂ§ÃƒÂµes relevantes e concisas inferidas do contexto fornecido.\n"
            "Sua resposta DEVE ser um objeto JSON contendo uma ÃƒÂºnica chave 'sugestoes_atributos'.\n"
            "O valor de 'sugestoes_atributos' deve ser uma lista de objetos.\n"
            "Cada objeto na lista deve ter duas chaves: 'chave_atributo' (que deve ser uma das chaves da lista que forneci: "
            f"{lista_chaves_str}) e 'valor_sugerido' (a sua sugestÃƒÂ£o de valor para esse atributo).\n"
            "Se vocÃƒÂª nÃƒÂ£o puder sugerir um valor para um atributo especÃƒÂ­fico com base nas informaÃƒÂ§ÃƒÂµes, pode omiti-lo da lista ou fornecer um valor como 'NÃƒÂ£o encontrado'.\n"
            "NÃƒÂ£o inclua atributos na sua resposta que nÃƒÂ£o foram listados explicitamente."
        )
    
        # 5. Definir o responseSchema esperado da Gemini
        gemini_response_schema = {
            "type": "OBJECT",
            "properties": {
                "sugestoes_atributos": {
                    "type": "ARRAY",
                    "items": {
                        "type": "OBJECT",
                        "properties": {
                            "chave_atributo": {"type": "STRING"},
                            "valor_sugerido": {"type": "STRING"}
                        },
                        "required": ["chave_atributo", "valor_sugerido"]
                    }
                }
            },
            "required": ["sugestoes_atributos"]
        }
    
        # 6. Obter chave da API e Chamar Gemini
        ai_provider_workflow = self._get_ai_provider_workflow()
        gemini_api_key = await ai_provider_workflow.get_gemini_api_key(db=db, user=user)
        modelo_utilizado = "gemini-1.5-flash-latest" # Ou outro modelo configurado
        
        try:
            sugestoes_dict = await ai_provider_workflow.call_gemini_api_for_suggestions(
                prompt_text=prompt_final,
                api_key=gemini_api_key,
                response_schema=gemini_response_schema,
                model_name=modelo_utilizado
            )
            
            # Validar se a resposta da Gemini estÃƒÂ¡ no formato esperado (mesmo que ela tenha usado o schema)
            if not isinstance(sugestoes_dict, dict) or "sugestoes_atributos" not in sugestoes_dict:
                raise HTTPException(status_code=500, detail="Resposta da API Gemini em formato invÃƒÂ¡lido (esperava 'sugestoes_atributos').")
            if not isinstance(sugestoes_dict["sugestoes_atributos"], list):
                 raise HTTPException(status_code=500, detail="Campo 'sugestoes_atributos' da API Gemini nÃƒÂ£o ÃƒÂ© uma lista.")
    
            # Filtrar sugestÃƒÂµes para incluir apenas chaves solicitadas e com valor nÃƒÂ£o vazio (opcional)
            sugestoes_finais = []
            for item_sugerido_dict in sugestoes_dict["sugestoes_atributos"]:
                if not isinstance(item_sugerido_dict, dict) or "chave_atributo" not in item_sugerido_dict or "valor_sugerido" not in item_sugerido_dict:
                    logger.warning(f"Aviso: Item de sugestÃƒÂ£o malformado da Gemini: {item_sugerido_dict}")
                    continue
    
                chave = item_sugerido_dict["chave_atributo"]
                valor = item_sugerido_dict["valor_sugerido"]
                if chave in chaves_para_sugerir and valor: # Garante que a chave ÃƒÂ© uma das solicitadas
                    sugestoes_finais.append(schemas.SugestaoAtributoItem(chave_atributo=chave, valor_sugerido=valor))
            
            # 7. Registrar Uso
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=creditos_necessarios, status="SUCESSO",
                prompt_utilizado=prompt_final # Para auditoria
                # resposta_ia=json.dumps(sugestoes_dict) # Pode ser muito grande, opcional
            ))
            
            return schemas.SugestoesAtributosResponse(
                sugestoes_atributos=sugestoes_finais,
                produto_id=produto_id,
                modelo_ia_utilizado=modelo_utilizado
            )
    
        except HTTPException as e: # Repassa HTTPExceptions de call_gemini_api_for_suggestions ou de verificaÃƒÂ§ÃƒÂµes
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=creditos_necessarios,
                status="FALHA", detalhes_erro=str(e.detail)
            ))
            raise e
        except Exception as e:
            logger.error(f"Erro geral no serviÃƒÂ§o de sugestÃƒÂ£o Gemini: {str(e)}", exc_info=True)
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=creditos_necessarios,
                status="FALHA", detalhes_erro=f"Erro inesperado no serviÃƒÂ§o de sugestÃƒÂ£o: {str(e)}"
            ))
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Erro inesperado ao gerar sugestÃƒÂµes: {str(e)}")



IAGenerationWorkflow = _IAGenerationWorkflow



