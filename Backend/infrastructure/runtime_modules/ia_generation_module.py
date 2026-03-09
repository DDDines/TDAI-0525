# Backend/infrastructure/runtime_modules/ia_generation_module.py
"""Document ia generation module module responsibilities and runtime integration points."""


import httpx # Para chamadas HTTP assÃ­ncronas
import json
import re
import unicodedata
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
import logging # Adicionado para logging
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from fastapi import HTTPException, status

from Backend import models  # models completo para acesso a TipoAcaoEnum
from Backend import schemas
from Backend.core.api_key_validation import looks_like_openai_api_key, normalize_optional_secret
from Backend.core.config import settings
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.prompt_template_repository import (
    DEFAULT_PROMPT_TEMPLATES,
    PromptTemplateName,
    PromptTemplateRepository,
)
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)

# ConfiguraÃ§Ã£o do logger
logger = logging.getLogger(__name__)

# --- Constantes para OpenAI (Exemplo, idealmente viriam de settings) ---
OPENAI_API_URL_COMPLETIONS = "https://api.openai.com/v1/chat/completions"
OPENAI_API_URL_MODELS = "https://api.openai.com/v1/models"
OPENAI_DEFAULT_MODEL = "gpt-3.5-turbo" # Ou o modelo que vocÃª preferir/tiver acesso

# --- Constantes para Gemini (Exemplo, idealmente viriam de settings) ---
# AtenÃ§Ã£o: Verifique a URL correta e o modelo exato para a sua necessidade.
# Modelos "flash" sÃ£o mais rÃ¡pidos e baratos, "pro" sÃ£o mais capazes.
# gemini-1.5-flash-latest ou gemini-1.5-pro-latest ou um especÃ­fico como gemini-1.0-pro
GEMINI_API_URL_GENERATE_CONTENT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

COMPANY_TIMELINE_HINTS = (
    "iniciou suas atividades",
    "iniciou as atividades",
    "fundada em",
    "fundado em",
    "anos de mercado",
    "no mercado desde",
    "atuando desde",
    "historia da empresa",
)
COMPANY_TIMELINE_PATTERN = re.compile(
    r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades(?:\s+no?\s+ano\s+de\s+(?:19|20)\d{2})?)\b",
    re.IGNORECASE,
)
COMPANY_ENTITY_HINT_PATTERN = re.compile(
    r"\b(?:empresa|marca|fabricante|industria|loja|grupo|nos|nossa|historia|tradicao|mercado)\b",
    re.IGNORECASE,
)
TITLE_CONTACT_MARKER_PATTERN = re.compile(
    r"\b(?:comercio|com[eÃ©]rcio|eletronico|eletr[oÃ´]nico|loja|empresa|atendimento|contato|telefone|fone|whatsapp|sac|site)\b",
    re.IGNORECASE,
)
PHONE_OR_ID_BLOCK_PATTERN = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")
EMAIL_PATTERN = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    re.IGNORECASE,
)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
TITLE_META_LINE_PATTERN = re.compile(
    r"^(?:"
    r"com\s+certeza!?|"
    r"aqui\s+est[aã]o|"
    r"op[cç][oõ]es?\s+de|"
    r"observa[cç][oõ]es?|"
    r"por\s+que\s+funciona|"
    r"foco|"
    r"manter\s+foco|"
    r"seo|"
    r"atra[cç][aã]o|"
    r"formato\s+de\s+resposta|"
    r"resposta\s+final"
    r")\b",
    re.IGNORECASE,
)
TITLE_BOLD_SEGMENT_PATTERN = re.compile(r"\*\*(.+?)\*\*")
TRAILING_EXPLANATION_PATTERN = re.compile(r"\s+\((?:[^()]|\([^()]*\)){8,}\)\s*$")
DESCRIPTION_META_PREFIX_PATTERN = re.compile(
    r"^\s*(?:descri[cç][aã]o(?:\s+do\s+produto)?|texto\s+final|resposta\s+final)\s*:\s*",
    re.IGNORECASE,
)
DESCRIPTION_PROMOTIONAL_PATTERN = re.compile(
    r"\b(?:adquira|compre|garanta|aproveite|invista|descubra|impulsione?|transforme|"
    r"renove|eleve|leve\s+agora)\b",
    re.IGNORECASE,
)
TITLE_IDENTITY_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "para",
    "com",
    "sem",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "a",
    "o",
    "as",
    "os",
}
TITLE_PROMOTIONAL_TOKEN_PATTERN = re.compile(
    r"\b(?:exiba|exibir|descubra|transforme|aproveite|garanta|ideal|perfeito|perfeita|"
    r"seu|sua|seus|suas|compre|leve|tenha|melhore|renove|encante|celebre)\b",
    re.IGNORECASE,
)
TITLE_GENERIC_SUFFIX_PATTERN = re.compile(
    r"\b(?:decor|decoracao|decorativo|decorativa|colecao|colecao|produto|item)\b",
    re.IGNORECASE,
)


class AiProviderWorkflow:
    """Workflow OO para operaÃ§Ãµes de provedor IA (chaves e chamadas HTTP)."""

    def __init__(self, runtime: Optional["AiProviderRuntime"] = None) -> None:
        """Initialize injected dependencies and runtime configuration for Ai Provider Workflow."""
        self._runtime = runtime or AiProviderRuntime()

    async def get_openai_api_key(self, db: Session, user: models.User) -> Optional[str]:
        """Retrieve openai api key using the current service dependencies."""
        return await self._runtime.get_openai_api_key(db=db, user=user)

    async def get_gemini_api_key(self, db: Session, user: models.User) -> Optional[str]:
        """Retrieve gemini api key using the current service dependencies."""
        return await self._runtime.get_gemini_api_key(db=db, user=user)

    async def call_openai_api(
        self,
        prompt_messages: List[Dict[str, str]],
        api_key: str,
        model: str = OPENAI_DEFAULT_MODEL,
        temperature: float = 0.7,
        max_tokens: int = 500,
    ) -> str:
        """Execute call openai api as part of this module workflow."""
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
        """Call gemini api for suggestions."""
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
        """Execute call gemini api as part of this module workflow."""
        return await self._runtime.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
        )


class AiProviderRuntime:
    """Runtime OO para integracoes com provedores IA."""

    RETRYABLE_STATUS_CODES = {429, 503}

    def __init__(self) -> None:
        """Initialize injected dependencies and runtime configuration for Ai Provider Runtime."""
        self._lm_studio_model_cache = normalize_optional_secret(settings.LM_STUDIO_MODEL)

    @staticmethod
    def _normalize_provider_name(provider_name: Optional[str]) -> str:
        """Normalize provider selection to the supported OpenAI-compatible modes."""
        normalized = normalize_optional_secret(provider_name) or "openai"
        return normalized.lower()

    def get_openai_provider_name(self) -> str:
        """Return the active OpenAI-compatible provider label."""
        provider_name = self._normalize_provider_name(settings.AI_PROVIDER)
        return "lm_studio" if provider_name == "lm_studio" else "openai"

    def _is_lm_studio_enabled(self) -> bool:
        """Check whether OpenAI-compatible traffic should be routed to LM Studio."""
        return self.get_openai_provider_name() == "lm_studio"

    def _get_openai_compatible_base_url(self) -> str:
        """Resolve the OpenAI-compatible base URL for the active provider."""
        if self._is_lm_studio_enabled():
            return str(settings.LM_STUDIO_BASE_URL or "http://127.0.0.1:1234/v1").rstrip("/")
        return "https://api.openai.com/v1"

    def _build_openai_compatible_url(self, path: str) -> str:
        """Build a provider-specific OpenAI-compatible endpoint URL."""
        normalized_path = path if path.startswith("/") else f"/{path}"
        return f"{self._get_openai_compatible_base_url()}{normalized_path}"

    @classmethod
    def _is_retryable_exception(cls, exc: Exception) -> bool:
        """Classify upstream exceptions that should trigger exponential backoff."""
        if isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError, httpx.ReadError)):
            return True
        if isinstance(exc, httpx.HTTPStatusError):
            return exc.response.status_code in cls.RETRYABLE_STATUS_CODES
        return False

    async def _request_with_retry(
        self,
        *,
        method: str,
        url: str,
        headers: Dict[str, str],
        timeout_seconds: float,
        json_payload: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """Execute an outbound HTTP request with retry/backoff for transient failures."""
        async with httpx.AsyncClient(timeout=timeout_seconds) as client:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(3),
                wait=wait_exponential(multiplier=2, min=2, max=8),
                retry=retry_if_exception(self._is_retryable_exception),
                reraise=True,
            ):
                with attempt:
                    response = await client.request(
                        method,
                        url,
                        json=json_payload,
                        headers=headers,
                    )
                    response.raise_for_status()
                    return response

    async def _resolve_lm_studio_model(self, *, api_key: str) -> str:
        """Resolve the LM Studio model from env override or the local /models endpoint."""
        explicit_model = normalize_optional_secret(settings.LM_STUDIO_MODEL)
        if explicit_model:
            self._lm_studio_model_cache = explicit_model
            return explicit_model

        if self._lm_studio_model_cache:
            return self._lm_studio_model_cache

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = await self._request_with_retry(
            method="GET",
            url=self._build_openai_compatible_url("/models"),
            headers=headers,
            timeout_seconds=30.0,
        )
        response_json = response.json()
        models_payload = response_json.get("data") if isinstance(response_json, dict) else None
        if isinstance(models_payload, list):
            for model_entry in models_payload:
                model_id = normalize_optional_secret((model_entry or {}).get("id"))
                if model_id:
                    self._lm_studio_model_cache = model_id
                    logger.info("Modelo LM Studio resolvido automaticamente: %s", model_id)
                    return model_id

        logger.error("Nao foi possivel resolver um modelo valido no endpoint /models do LM Studio: %s", response_json)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Nenhum modelo carregado foi encontrado no LM Studio.",
        )

    async def resolve_openai_model(
        self,
        *,
        api_key: str,
        requested_model: Optional[str] = None,
    ) -> str:
        """Resolve the effective model name for the active OpenAI-compatible provider."""
        normalized_requested_model = normalize_optional_secret(requested_model)
        if self._is_lm_studio_enabled():
            if normalized_requested_model and normalized_requested_model != OPENAI_DEFAULT_MODEL:
                return normalized_requested_model
            return await self._resolve_lm_studio_model(api_key=api_key)
        return normalized_requested_model or OPENAI_DEFAULT_MODEL

    async def get_openai_api_key(
        self, db: Session, user: models.User
    ) -> Optional[str]:
        """Retrieve openai api key using the current service dependencies."""
        if self._is_lm_studio_enabled():
            lm_studio_key = normalize_optional_secret(settings.LM_STUDIO_API_KEY) or "lm-studio"
            logger.info(
                "Usando provider LM Studio OpenAI-compatible em %s.",
                self._get_openai_compatible_base_url(),
            )
            return lm_studio_key

        user_key = normalize_optional_secret(getattr(user, "chave_openai_pessoal", None))
        system_key = normalize_optional_secret(settings.OPENAI_API_KEY)

        if looks_like_openai_api_key(user_key):
            logger.info(f"Usando chave OpenAI pessoal para usuÃ¡rio ID: {user.id}")
            return user_key
        if user_key:
            logger.warning(
                "Chave OpenAI pessoal ignorada para usuÃ¡rio ID %s: formato invalido.",
                user.id,
            )

        if looks_like_openai_api_key(system_key):
            logger.info("Usando chave OpenAI global do sistema.")
            return system_key
        if system_key:
            logger.warning("Chave OpenAI global ignorada: formato invalido.")

        logger.warning("Nenhuma chave OpenAI encontrada (nem pessoal, nem global).")
        return None

    async def get_gemini_api_key(
        self, db: Session, user: models.User
    ) -> Optional[str]:
        """Retrieve gemini api key using the current service dependencies."""
        if user.chave_google_gemini_pessoal:
            logger.info(f"Usando chave Gemini pessoal para usuÃ¡rio ID: {user.id}")
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
        """Execute call openai api as part of this module workflow."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API OpenAI nÃ£o configurada.",
            )

        resolved_model = await self.resolve_openai_model(
            api_key=api_key,
            requested_model=model,
        )
        provider_name = self.get_openai_provider_name()
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": resolved_model,
            "messages": prompt_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        try:
            logger.info(
                "Chamando provider OpenAI-compatible '%s'. Modelo: %s, Tokens Max: %s, Temp: %s",
                provider_name,
                resolved_model,
                max_tokens,
                temperature,
            )
            response = await self._request_with_retry(
                method="POST",
                url=self._build_openai_compatible_url("/chat/completions"),
                json_payload=payload,
                headers=headers,
                timeout_seconds=60.0,
            )
            api_response_data = response.json()

            if api_response_data.get("choices") and len(api_response_data["choices"]) > 0:
                content = api_response_data["choices"][0].get("message", {}).get("content", "")
                return content.strip()

            logger.error(
                "Resposta do provider OpenAI-compatible nao contem 'choices' valido: %s",
                api_response_data,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Resposta inesperada da API OpenAI-compatible.",
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Erro no provider OpenAI-compatible '%s': %s - %s",
                provider_name,
                e.response.status_code,
                e.response.text,
                exc_info=True,
            )
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Erro na API OpenAI-compatible: {e.response.text}",
            )
        except httpx.RequestError as e:
            logger.error("Erro de rede ao chamar provider OpenAI-compatible: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha de rede ao comunicar com o provider OpenAI-compatible.",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("Erro inesperado ao chamar provider OpenAI-compatible: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro inesperado ao comunicar com OpenAI-compatible.",
            )

    async def call_gemini_api_for_suggestions(
        self,
        prompt_text: str,
        api_key: str,
        response_schema: Dict[str, Any],
        model_name: str = "gemini-1.5-flash-latest",
    ) -> Dict[str, Any]:
        """Call gemini api for suggestions."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API Gemini nÃ£o configurada.",
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

        try:
            response = await self._request_with_retry(
                method="POST",
                url=url_com_chave,
                json_payload=payload,
                headers=headers,
                timeout_seconds=90.0,
            )
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
                        detail="Resposta da API Gemini nÃ£o Ã© um JSON vÃ¡lido.",
                    )

            error_detail = "Resposta da API Gemini nÃ£o contÃ©m o conteÃºdo esperado."
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
        except httpx.RequestError as e:
            logger.error("Erro de rede ao chamar API Gemini: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha de rede ao comunicar com Gemini.",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar API Gemini: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro inesperado ao comunicar com Gemini.",
            )

    async def call_gemini_api(
        self,
        prompt_text: str,
        api_key: str,
        model_name: str = "gemini-1.5-flash-latest",
        temperature: float = 0.6,
        max_tokens: int = 1024,
    ) -> str:
        """Execute call gemini api as part of this module workflow."""
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Chave da API Gemini nÃ£o configurada.",
            )

        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_tokens},
        }
        url = f"{endpoint}?key={api_key}"
        headers = {"Content-Type": "application/json"}
        try:
            response = await self._request_with_retry(
                method="POST",
                url=url,
                json_payload=payload,
                headers=headers,
                timeout_seconds=90.0,
            )
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
        except httpx.RequestError as e:
            logger.error("Erro de rede ao chamar API Gemini: %s", str(e), exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Falha de rede ao comunicar com Gemini.",
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Erro inesperado ao chamar API Gemini: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro inesperado ao comunicar com Gemini.",
            )


# --- NOVA FUNÃ‡ÃƒO PARA SUGESTÃ•ES GEMINI ---
class IAGenerationWorkflow:
    """Workflow OO para operaÃ§Ãµes de geraÃ§Ã£o de conteÃºdo IA."""

    def __init__(self, runtime: Optional["IAGenerationRuntime"] = None) -> None:
        """Initialize injected dependencies and runtime configuration for IAGeneration Workflow."""
        self._runtime = runtime or IAGenerationRuntime()

    async def gerar_titulos_com_openai(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        """Execute gerar titulos com openai as part of this module workflow."""
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
        """Execute gerar descricao com openai as part of this module workflow."""
        return await self._runtime.gerar_descricao_com_openai(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        """Execute gerar titulos com gemini as part of this module workflow."""
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
        """Execute gerar descricao com gemini as part of this module workflow."""
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
        """Sugerir valores atributos com gemini."""
        return await self._runtime.sugerir_valores_atributos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=user,
        )


class IAGenerationRuntime:
    """Runtime OO para operacoes de geracao de conteudo IA."""

    async def gerar_titulos_com_openai(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        """Execute gerar titulos com openai as part of this module workflow."""
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
        """Execute gerar descricao com openai as part of this module workflow."""
        return await self._gerar_descricao_com_openai_impl(
            db=db,
            produto_id=produto_id,
            user=user,
            tamanho_palavras=tamanho_palavras,
        )

    async def gerar_titulos_com_gemini(
        self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3
    ) -> List[str]:
        """Execute gerar titulos com gemini as part of this module workflow."""
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
        """Execute gerar descricao com gemini as part of this module workflow."""
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
        """Sugerir valores atributos com gemini."""
        return await self._sugerir_valores_atributos_com_gemini_impl(
            db=db,
            produto_id=produto_id,
            user=user,
        )

    @staticmethod
    def _get_ai_provider_workflow() -> AiProviderWorkflow:
        """Retrieve ai provider workflow using the current service dependencies."""
        return AiProviderWorkflow(runtime=AiProviderRuntime())

    @staticmethod
    def _render_prompt(
        *,
        db: Session,
        nome: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Render a versioned prompt template with the current business context."""
        try:
            return PromptTemplateRepository(db).render_prompt(
                nome=nome,
                context=context or {},
            ).conteudo
        except Exception:
            class _SafePromptContext(dict):
                def __missing__(self, key):
                    """Return an empty string for missing inline fallback placeholders."""
                    return ""

            safe_context = _SafePromptContext(
                {key: ("" if value is None else value) for key, value in dict(context or {}).items()}
            )
            return DEFAULT_PROMPT_TEMPLATES[nome].format_map(
                safe_context
            )

    @staticmethod
    def _looks_like_company_timeline_claim(text: str) -> bool:
        """Detect unsupported company timeline/history claims that tend to be hallucinated."""
        compact = " ".join(str(text or "").strip().split())
        if not compact:
            return False

        lowered = compact.lower()
        if any(hint in lowered for hint in COMPANY_TIMELINE_HINTS):
            return True

        if not COMPANY_TIMELINE_PATTERN.search(compact):
            return False

        return bool(COMPANY_ENTITY_HINT_PATTERN.search(compact))

    @staticmethod
    def _sanitize_generated_description(raw_text: Any) -> str:
        """Remove unsupported company-history claims from generated descriptions."""
        text = " ".join(str(raw_text or "").strip().split())
        if not text:
            return ""

        text = DESCRIPTION_META_PREFIX_PATTERN.sub("", text)
        text = re.sub(r"^\s*[-*•]+\s*", "", text).strip()

        chunks = re.split(r"(?<=[.!?])\s+|[\r\n]+", text)
        filtered_chunks: List[str] = []
        for chunk in chunks:
            normalized_chunk = " ".join(str(chunk or "").strip().split())
            if IAGenerationRuntime._looks_like_company_timeline_claim(normalized_chunk):
                continue
            if DESCRIPTION_PROMOTIONAL_PATTERN.search(normalized_chunk):
                continue
            filtered_chunks.append(normalized_chunk)

        if filtered_chunks:
            return " ".join(filtered_chunks).strip()
        return text

    @staticmethod
    def _clean_single_title_candidate(raw_line: Any) -> str:
        """Normalize a single raw title line without applying product-specific identity rules."""
        cleaned = str(raw_line or "").strip()
        if not cleaned:
            return ""
        bold_match = TITLE_BOLD_SEGMENT_PATTERN.search(cleaned)
        if bold_match:
            cleaned = bold_match.group(1).strip()
        cleaned = re.sub(r"^\s*(?:[-*•]+|\d+[)\].:-])\s*", "", cleaned).strip()
        cleaned = re.sub(r"^(?:titulo|t[ií]tulo)\s*:\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip(' "\'`')
        if TITLE_META_LINE_PATTERN.search(cleaned):
            return ""
        cleaned = TRAILING_EXPLANATION_PATTERN.sub("", cleaned).strip()
        cleaned = re.split(
            r"\s+(?:[-–—]\s+)?(?:por que funciona|foco|seo|atra[cç][aã]o)\s*:\s*",
            cleaned,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        cleaned = URL_PATTERN.sub(" ", cleaned)
        cleaned = EMAIL_PATTERN.sub(" ", cleaned)
        cleaned = PHONE_OR_ID_BLOCK_PATTERN.sub(" ", cleaned)
        marker_match = TITLE_CONTACT_MARKER_PATTERN.search(cleaned)
        if marker_match:
            cleaned = cleaned[: marker_match.start()]
        cleaned = TITLE_CONTACT_MARKER_PATTERN.sub(" ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|,;:/")
        if len(cleaned) < 4:
            return ""
        if IAGenerationRuntime._looks_like_company_timeline_claim(cleaned):
            return ""
        if URL_PATTERN.search(cleaned) or EMAIL_PATTERN.search(cleaned) or PHONE_OR_ID_BLOCK_PATTERN.search(cleaned):
            return ""
        return cleaned

    @staticmethod
    def _fold_identity_text(value: Any) -> str:
        """Fold unicode accents and case for robust identity comparisons."""
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(char for char in normalized if not unicodedata.combining(char)).lower()

    @classmethod
    def _tokenize_title_identity(cls, value: Any) -> List[str]:
        """Tokenize a title into comparable identity tokens, skipping low-signal stopwords."""
        cleaned = cls._clean_single_title_candidate(value)
        if not cleaned:
            return []
        folded = cls._fold_identity_text(cleaned)
        tokens = re.findall(r"[a-z0-9][a-z0-9./-]{1,}", folded)
        return [token for token in tokens if len(token) >= 3 and token not in TITLE_IDENTITY_STOPWORDS]

    @classmethod
    def _build_source_title_variants(
        cls,
        *,
        source_title: Any = None,
        source_aliases: Optional[List[Any]] = None,
    ) -> List[str]:
        """Build a normalized list of source titles that define the product identity."""
        variants: List[str] = []
        seen: set[str] = set()
        for raw_value in [source_title, *(source_aliases or [])]:
            cleaned = cls._clean_single_title_candidate(raw_value)
            if not cleaned:
                continue
            normalized = cls._fold_identity_text(cleaned)
            if normalized in seen:
                continue
            seen.add(normalized)
            variants.append(cleaned)
        return variants

    @classmethod
    def _candidate_preserves_source_identity(cls, candidate: str, *, source_variants: List[str]) -> bool:
        """Reject candidates that drift too far from the original product name identity."""
        if not source_variants:
            return True
        candidate_tokens = set(cls._tokenize_title_identity(candidate))
        if not candidate_tokens:
            return False

        for source_variant in source_variants:
            source_tokens = set(cls._tokenize_title_identity(source_variant))
            if not source_tokens:
                continue
            overlap = len(candidate_tokens & source_tokens)
            source_size = len(source_tokens)
            if source_size >= 3 and overlap >= 2:
                return True
            if source_size == 2 and overlap >= 1:
                return True
            if source_size == 1 and overlap >= 1:
                return True
        return False

    @classmethod
    def _candidate_is_promotional_or_generic(cls, candidate: str, *, source_variants: List[str]) -> bool:
        """Reject title candidates that sound like CTA, sales copy, or generic suffix padding."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        if not cleaned_candidate:
            return True

        source_text = " ".join(source_variants)
        folded_source = cls._fold_identity_text(source_text)
        folded_candidate = cls._fold_identity_text(cleaned_candidate)

        if TITLE_PROMOTIONAL_TOKEN_PATTERN.search(folded_candidate):
            return True

        generic_match = TITLE_GENERIC_SUFFIX_PATTERN.search(folded_candidate)
        if generic_match and generic_match.group(0).strip() not in folded_source:
            return True
        return False

    @classmethod
    def _build_deterministic_title_fallbacks(
        cls,
        *,
        source_variants: List[str],
        desired_count: int,
    ) -> List[str]:
        """Build safe, source-preserving title variations when LLM output is weak."""
        if not source_variants or desired_count <= 0:
            return []

        primary_source = source_variants[0]
        clean_primary = cls._clean_single_title_candidate(primary_source)
        if not clean_primary:
            return []

        words = clean_primary.split()
        fallbacks: List[str] = [clean_primary]

        rotations: List[List[str]] = []
        if len(words) >= 3:
            rotations.append(words[-1:] + words[:-1])
        if len(words) >= 4:
            rotations.append(words[-2:] + words[:-2])

        for rotated_words in rotations:
            rotated = " ".join(rotated_words).strip()
            fallbacks.append(rotated)

        for alias in source_variants[1:]:
            cleaned_alias = cls._clean_single_title_candidate(alias)
            if cleaned_alias:
                fallbacks.append(cleaned_alias)

        unique: List[str] = []
        seen: set[str] = set()
        for candidate in fallbacks:
            normalized = cls._fold_identity_text(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(candidate)
            if len(unique) >= desired_count:
                break
        return unique

    @classmethod
    def _reconcile_title_candidates_with_source(
        cls,
        candidates: List[str],
        *,
        source_title: Any = None,
        source_aliases: Optional[List[Any]] = None,
        desired_count: Optional[int] = None,
    ) -> List[str]:
        """Force at least one strong source-preserving title and drop severe identity drift."""
        source_variants = cls._build_source_title_variants(
            source_title=source_title,
            source_aliases=source_aliases,
        )
        filtered_candidates = [
            candidate
            for candidate in candidates
            if cls._candidate_preserves_source_identity(candidate, source_variants=source_variants)
            and not cls._candidate_is_promotional_or_generic(candidate, source_variants=source_variants)
        ]

        unique: List[str] = []
        seen: set[str] = set()
        if source_variants:
            primary_source = source_variants[0]
            unique.append(primary_source)
            seen.add(cls._fold_identity_text(primary_source))

        for candidate in filtered_candidates:
            normalized = cls._fold_identity_text(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique.append(candidate)

        requested_count = max(1, int(desired_count or 0))
        if requested_count and len(unique) < requested_count:
            for fallback in cls._build_deterministic_title_fallbacks(
                source_variants=source_variants,
                desired_count=requested_count,
            ):
                normalized = cls._fold_identity_text(fallback)
                if normalized in seen:
                    continue
                seen.add(normalized)
                unique.append(fallback)
                if len(unique) >= requested_count:
                    break
        return unique

    @classmethod
    def _sanitize_title_candidates(
        cls,
        raw_text: str,
        *,
        source_title: Any = None,
        source_aliases: Optional[List[Any]] = None,
        desired_count: Optional[int] = None,
    ) -> List[str]:
        """Normalize raw LLM output into clean title candidates."""
        if not raw_text:
            return cls._reconcile_title_candidates_with_source(
                [],
                source_title=source_title,
                source_aliases=source_aliases,
                desired_count=desired_count,
            )
        candidates: List[str] = []
        seen_normalized: set[str] = set()
        for line in str(raw_text).splitlines():
            cleaned = cls._clean_single_title_candidate(line)
            if not cleaned:
                continue
            normalized = cls._fold_identity_text(cleaned)
            if normalized not in seen_normalized:
                seen_normalized.add(normalized)
                candidates.append(cleaned)
        return cls._reconcile_title_candidates_with_source(
            candidates,
            source_title=source_title,
            source_aliases=source_aliases,
            desired_count=desired_count,
        )

    @staticmethod
    def _build_local_title_candidates(db_produto: Any, *, num_titulos: int) -> List[str]:
        """Build deterministic fallback titles when no IA key is configured."""
        base_name = (
            (getattr(db_produto, "nome_base", None) or getattr(db_produto, "nome_chat_api", None) or "Produto")
            .strip()
        )
        marca = str(getattr(db_produto, "marca", "") or "").strip()
        modelo = str(getattr(db_produto, "modelo", "") or "").strip()
        sku = str(getattr(db_produto, "sku", "") or "").strip()
        categoria = str(getattr(db_produto, "categoria_original", "") or "").strip()

        def _clean_title_part(value: str) -> str:
            """Strip contact/institutional artifacts from local fallback title fragments."""
            cleaned = URL_PATTERN.sub(" ", value)
            cleaned = EMAIL_PATTERN.sub(" ", cleaned)
            cleaned = PHONE_OR_ID_BLOCK_PATTERN.sub(" ", cleaned)
            marker_match = TITLE_CONTACT_MARKER_PATTERN.search(cleaned)
            if marker_match:
                cleaned = cleaned[: marker_match.start()]
            cleaned = TITLE_CONTACT_MARKER_PATTERN.sub(" ", cleaned)
            return re.sub(r"\s+", " ", cleaned).strip(" -|,;:/")

        base_name = _clean_title_part(base_name) or "Produto"
        marca = _clean_title_part(marca)
        modelo = _clean_title_part(modelo)
        categoria = _clean_title_part(categoria)

        seeds = [
            base_name,
            f"{base_name} {marca}".strip(),
            f"{base_name} {modelo}".strip(),
            f"{base_name} {categoria}".strip(),
            f"{base_name} {sku}".strip(),
            f"{base_name} Alta Durabilidade".strip(),
        ]
        unique: List[str] = []
        for seed in seeds:
            cleaned = re.sub(r"\s+", " ", seed).strip(" -")
            if len(cleaned) < 4:
                continue
            if cleaned not in unique:
                unique.append(cleaned)
            if len(unique) >= max(1, num_titulos):
                break
        return unique[: max(1, num_titulos)]

    @staticmethod
    def _build_local_description(db_produto: Any, *, tamanho_palavras: int) -> str:
        """Build deterministic fallback description when no IA key is configured."""
        nome = str(getattr(db_produto, "nome_base", "") or "").strip() or "Produto automotivo"
        marca = str(getattr(db_produto, "marca", "") or "").strip()
        modelo = str(getattr(db_produto, "modelo", "") or "").strip()
        sku = str(getattr(db_produto, "sku", "") or "").strip()
        ean = str(getattr(db_produto, "ean", "") or "").strip()
        categoria = str(getattr(db_produto, "categoria_original", "") or "").strip()
        descricao_origem = str(
            getattr(db_produto, "descricao_original", "") or getattr(db_produto, "descricao_chat_api", "") or ""
        ).strip()

        parts: List[str] = [f"{nome} e uma peca voltada para aplicacao automotiva com foco em reposicao confiavel."]
        if marca:
            parts.append(f"Fabricado por {marca}, mantendo padrao de compatibilidade para uso profissional.")
        if modelo:
            parts.append(f"Compativel com aplicacoes relacionadas ao modelo {modelo}.")
        if categoria:
            parts.append(f"Categoria de referencia: {categoria}.")
        if sku:
            parts.append(f"Codigo de identificacao (SKU): {sku}.")
        if ean:
            parts.append(f"Codigo EAN: {ean}.")
        if descricao_origem:
            parts.append(f"Informacoes adicionais do catalogo: {descricao_origem}.")
        parts.append("Antes da venda, confirme medidas, posicao de montagem e compatibilidade com o veiculo de destino.")

        text = " ".join(parts).strip()
        target_words = max(40, int(tamanho_palavras))
        words = [token for token in text.split() if token]
        if len(words) >= target_words:
            return " ".join(words[:target_words])
        return text

    @staticmethod
    def _registrar_uso_fallback(
        *,
        db: Session,
        user_id: int,
        produto_id: int,
        tipo_acao: Any,
        provider_name: str,
        details: str,
    ) -> None:
        """Persist fallback usage entry without blocking request flow."""
        try:
            RegistroUsoIARepository(db).create_registro_uso_ia(
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user_id,
                    produto_id=produto_id,
                    tipo_acao=tipo_acao,
                    provedor_ia=provider_name,
                    modelo_ia="template-fallback",
                    creditos_consumidos=0,
                    status="FALLBACK",
                    detalhes_erro=details,
                )
            )
        except Exception:
            logger.warning("Falha ao registrar uso de fallback local para produto %s.", produto_id)
    async def _gerar_titulos_com_openai_impl(self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
        """Gerar titulos com OpenAI; aplica fallback local quando chave nao existe."""
        logger.info(
            "Iniciando geracao de titulos OpenAI para produto ID %s pelo usuario ID %s",
            produto_id,
            user.id,
        )
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_openai_api_key(db=db, user=user)
        if not api_key:
            logger.warning("OpenAI indisponivel para produto %s; aplicando fallback local.", produto_id)
            self._registrar_uso_fallback(
                db=db,
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
                provider_name="openai",
                details="Chave OpenAI ausente; fallback local aplicado.",
            )
            return self._build_local_title_candidates(
                db_produto,
                num_titulos=max(1, int(num_titulos or 1)),
            )

        prompt_messages = [
            {
                "role": "system",
                "content": self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_TITLE_SYSTEM,
                    context={"num_titulos": num_titulos},
                ),
            },
            {
                "role": "user",
                "content": self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_TITLE_USER,
                    context={
                        "nome_base": db_produto.nome_base,
                        "descricao": db_produto.descricao_original or db_produto.descricao_chat_api or "",
                        "marca": db_produto.marca or "",
                    },
                ),
            },
        ]

        titulos_str = await ai_provider_workflow.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key,
            max_tokens=150 * max(1, int(num_titulos or 1)),
        )
        titulos_list = self._sanitize_title_candidates(
            titulos_str,
            source_title=db_produto.nome_base or db_produto.nome_chat_api or "",
            source_aliases=[db_produto.nome_chat_api or ""],
            desired_count=max(1, int(num_titulos or 1)),
        )
        if not titulos_list:
            titulos_list = self._build_local_title_candidates(
                db_produto,
                num_titulos=max(1, int(num_titulos or 1)),
            )

        provider_runtime = getattr(ai_provider_workflow, "_runtime", None)
        if provider_runtime is not None:
            modelo_utilizado = await provider_runtime.resolve_openai_model(
                api_key=api_key,
                requested_model=OPENAI_DEFAULT_MODEL,
            )
            provider_name = provider_runtime.get_openai_provider_name()
        else:
            modelo_utilizado = OPENAI_DEFAULT_MODEL
            provider_name = "openai"
        RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
                provedor_ia=provider_name,
                modelo_ia=modelo_utilizado,
                creditos_consumidos=1,
            )
        )
        return titulos_list[: max(1, int(num_titulos or 1))]

    async def _gerar_descricao_com_openai_impl(self, db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
        """Gerar descricao com OpenAI; aplica fallback local quando chave nao existe."""
        logger.info(
            "Iniciando geracao de descricao OpenAI para produto ID %s pelo usuario ID %s",
            produto_id,
            user.id,
        )
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_openai_api_key(db=db, user=user)
        if not api_key:
            logger.warning("OpenAI indisponivel para produto %s; aplicando fallback local.", produto_id)
            self._registrar_uso_fallback(
                db=db,
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
                provider_name="openai",
                details="Chave OpenAI ausente; fallback local aplicado.",
            )
            return self._build_local_description(
                db_produto,
                tamanho_palavras=max(40, int(tamanho_palavras or 40)),
            )

        prompt_messages = [
            {
                "role": "system",
                "content": self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM,
                    context={"tamanho_palavras": tamanho_palavras},
                ),
            },
            {
                "role": "user",
                "content": self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_USER,
                    context={
                        "nome_base": db_produto.nome_base,
                        "descricao": db_produto.descricao_original or "",
                        "marca": db_produto.marca or "",
                        "modelo": db_produto.modelo or "",
                    },
                ),
            },
        ]

        descricao = await ai_provider_workflow.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key,
            max_tokens=max(60, int(tamanho_palavras or 60)) + 100,
        )
        descricao = self._sanitize_generated_description(descricao)
        if not isinstance(descricao, str) or not descricao.strip():
            descricao = self._build_local_description(
                db_produto,
                tamanho_palavras=max(40, int(tamanho_palavras or 40)),
            )

        provider_runtime = getattr(ai_provider_workflow, "_runtime", None)
        if provider_runtime is not None:
            modelo_utilizado = await provider_runtime.resolve_openai_model(
                api_key=api_key,
                requested_model=OPENAI_DEFAULT_MODEL,
            )
            provider_name = provider_runtime.get_openai_provider_name()
        else:
            modelo_utilizado = OPENAI_DEFAULT_MODEL
            provider_name = "openai"
        RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
                provedor_ia=provider_name,
                modelo_ia=modelo_utilizado,
                creditos_consumidos=1,
            )
        )
        return descricao

    async def _gerar_titulos_com_gemini_impl(self, db: Session, produto_id: int, user: models.User, num_titulos: int = 3) -> List[str]:
        """Gerar titulos com Gemini; aplica fallback local quando chave nao existe."""
        logger.info(
            "Iniciando geracao de titulos Gemini para produto ID %s pelo usuario ID %s",
            produto_id,
            user.id,
        )
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_gemini_api_key(db=db, user=user)
        if not api_key:
            logger.warning("Gemini indisponivel para produto %s; aplicando fallback local.", produto_id)
            self._registrar_uso_fallback(
                db=db,
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
                provider_name="gemini",
                details="Chave Gemini ausente; fallback local aplicado.",
            )
            return self._build_local_title_candidates(
                db_produto,
                num_titulos=max(1, int(num_titulos or 1)),
            )

        prompt_text = self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_TITLE_USER,
            context={
                "num_titulos": num_titulos,
                "nome_base": db_produto.nome_base,
                "descricao": db_produto.descricao_original or db_produto.descricao_chat_api or "",
                "marca": db_produto.marca or "",
            },
        )
        resultado = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=150 * max(1, int(num_titulos or 1)),
        )
        titulos_list = self._sanitize_title_candidates(
            resultado,
            source_title=db_produto.nome_base or db_produto.nome_chat_api or "",
            source_aliases=[db_produto.nome_chat_api or ""],
            desired_count=max(1, int(num_titulos or 1)),
        )
        if not titulos_list:
            titulos_list = self._build_local_title_candidates(
                db_produto,
                num_titulos=max(1, int(num_titulos or 1)),
            )

        RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
                provedor_ia="gemini",
                modelo_ia="gemini-1.5-flash-latest",
                creditos_consumidos=1,
            )
        )
        return titulos_list[: max(1, int(num_titulos or 1))]

    async def _gerar_descricao_com_gemini_impl(self, db: Session, produto_id: int, user: models.User, tamanho_palavras: int = 150) -> str:
        """Gerar descricao com Gemini; aplica fallback local quando chave nao existe."""
        logger.info(
            "Iniciando geracao de descricao Gemini para produto ID %s pelo usuario ID %s",
            produto_id,
            user.id,
        )
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")

        ai_provider_workflow = self._get_ai_provider_workflow()
        api_key = await ai_provider_workflow.get_gemini_api_key(db=db, user=user)
        if not api_key:
            logger.warning("Gemini indisponivel para produto %s; aplicando fallback local.", produto_id)
            self._registrar_uso_fallback(
                db=db,
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
                provider_name="gemini",
                details="Chave Gemini ausente; fallback local aplicado.",
            )
            return self._build_local_description(
                db_produto,
                tamanho_palavras=max(40, int(tamanho_palavras or 40)),
            )

        prompt_text = self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER,
            context={
                "tamanho_palavras": tamanho_palavras,
                "nome_base": db_produto.nome_base,
                "descricao": db_produto.descricao_original or "",
                "marca": db_produto.marca or "",
                "modelo": db_produto.modelo or "",
            },
        )
        descricao = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=max(60, int(tamanho_palavras or 60)) + 100,
        )
        descricao = self._sanitize_generated_description(descricao)
        if not isinstance(descricao, str) or not descricao.strip():
            descricao = self._build_local_description(
                db_produto,
                tamanho_palavras=max(40, int(tamanho_palavras or 40)),
            )

        RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id,
                produto_id=produto_id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
                provedor_ia="gemini",
                modelo_ia="gemini-1.5-flash-latest",
                creditos_consumidos=1,
            )
        )
        return descricao

    async def _sugerir_valores_atributos_com_gemini_impl(self, 
        db: Session,
        produto_id: int,
        user: models.User
    ) -> schemas.SugestoesAtributosResponse:
        """
        Gera sugestÃµes de valores para os atributos de um produto usando a API Gemini,
        baseado nos AttributeTemplates do ProductType do produto.
        """
        logger.info(f"Iniciando sugestÃ£o de atributos com Gemini para produto ID {produto_id} por usuÃ¡rio ID {user.id}")
        
        # 1. Verificar crÃ©ditos do usuÃ¡rio
        creditos_necessarios = settings.CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI if hasattr(settings, 'CREDITOS_CUSTO_SUGESTAO_ATRIBUTOS_GEMINI') else 1 # Custo padrÃ£o de 1 crÃ©dito
        # A verificaÃ§Ã£o de crÃ©dito foi movida para o router para uma resposta mais imediata ao usuÃ¡rio.
        # No entanto, pode ser mantida aqui como uma segunda camada de seguranÃ§a.
        # if not await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, creditos_necessarios):
        #     logger.warning(f"UsuÃ¡rio ID {user.id} com crÃ©ditos insuficientes para sugestÃ£o de atributos (necessÃ¡rio: {creditos_necessarios}).")
        #     raise HTTPException(...)
    
        # 2. Buscar Produto e seus AttributeTemplates
        db_produto = ProductRepository(db).get_produto(produto_id=produto_id)
        if not db_produto:
            logger.error(f"Produto ID {produto_id} nÃ£o encontrado para sugestÃ£o de atributos.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto nÃ£o encontrado")
        if db_produto.user_id != user.id and not user.is_superuser:
            logger.warning(f"UsuÃ¡rio ID {user.id} nÃ£o autorizado a acessar produto ID {produto_id} para sugestÃ£o.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="NÃ£o autorizado a acessar este produto")
    
        chaves_para_sugerir = []
        if db_produto.product_type and db_produto.product_type.attribute_templates:
            chaves_para_sugerir = [attr.attribute_key for attr in db_produto.product_type.attribute_templates if attr.attribute_key]
        
        if not chaves_para_sugerir:
            logger.info(f"Nenhum atributo definido no Tipo de Produto para produto ID {produto_id}. Retornando sugestÃµes vazias.")
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", creditos_consumidos=0, status="INFO", # NÃ£o consumiu crÃ©ditos se nÃ£o houve chamada
                detalhes_erro="Nenhum atributo definido no Tipo de Produto para gerar sugestÃµes."
            ))
            return schemas.SugestoesAtributosResponse(sugestoes_atributos=[], produto_id=produto_id, modelo_ia_utilizado="gemini (nÃ£o chamado)")
    
        # 3. Coletar Contexto do Produto
        contexto = f"Nome do Produto: {db_produto.nome_base or db_produto.nome_chat_api or 'N/A'}\n"
        contexto += f"DescriÃ§Ã£o: {db_produto.descricao_chat_api or db_produto.descricao_original or 'N/A'}\n"
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
                contexto += f"\nInformaÃ§Ãµes adicionais da web (primeiros 1000 caracteres):\n{str(web_text)[:1000]}...\n"
    
        # 4. Construir Prompt para Gemini
        lista_chaves_str = "\n".join([f"- '{chave}'" for chave in chaves_para_sugerir])
        prompt_final = self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_ATTRIBUTE_SUGGESTION_USER,
            context={
                "contexto": contexto,
                "lista_chaves_str": lista_chaves_str,
                "lista_chaves_inline": lista_chaves_str,
            },
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
            
            # Validar se a resposta da Gemini estÃ¡ no formato esperado (mesmo que ela tenha usado o schema)
            if not isinstance(sugestoes_dict, dict) or "sugestoes_atributos" not in sugestoes_dict:
                raise HTTPException(status_code=500, detail="Resposta da API Gemini em formato invÃ¡lido (esperava 'sugestoes_atributos').")
            if not isinstance(sugestoes_dict["sugestoes_atributos"], list):
                 raise HTTPException(status_code=500, detail="Campo 'sugestoes_atributos' da API Gemini nÃ£o Ã© uma lista.")
    
            # Filtrar sugestÃµes para incluir apenas chaves solicitadas e com valor nÃ£o vazio (opcional)
            sugestoes_finais = []
            for item_sugerido_dict in sugestoes_dict["sugestoes_atributos"]:
                if not isinstance(item_sugerido_dict, dict) or "chave_atributo" not in item_sugerido_dict or "valor_sugerido" not in item_sugerido_dict:
                    logger.warning(f"Aviso: Item de sugestÃ£o malformado da Gemini: {item_sugerido_dict}")
                    continue
    
                chave = item_sugerido_dict["chave_atributo"]
                valor = item_sugerido_dict["valor_sugerido"]
                if chave in chaves_para_sugerir and valor: # Garante que a chave Ã© uma das solicitadas
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
    
        except HTTPException as e: # Repassa HTTPExceptions de call_gemini_api_for_suggestions ou de verificaÃ§Ãµes
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=creditos_necessarios,
                status="FALHA", detalhes_erro=str(e.detail)
            ))
            raise e
        except Exception as e:
            logger.error(f"Erro geral no serviÃ§o de sugestÃ£o Gemini: {str(e)}", exc_info=True)
            RegistroUsoIARepository(db).create_registro_uso_ia(registro_uso=schemas.RegistroUsoIACreate(
                user_id=user.id, produto_id=produto_id, tipo_acao=models.TipoAcaoEnum.SUGESTAO_ATRIBUTOS_GEMINI,
                provedor_ia="gemini", modelo_ia=modelo_utilizado, creditos_consumidos=creditos_necessarios,
                status="FALHA", detalhes_erro=f"Erro inesperado no serviÃ§o de sugestÃ£o: {str(e)}"
            ))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro inesperado ao gerar sugestoes de atributos.",
            )




