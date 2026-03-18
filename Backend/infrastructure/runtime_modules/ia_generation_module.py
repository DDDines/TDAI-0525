# Backend/infrastructure/runtime_modules/ia_generation_module.py
"""Document ia generation module module responsibilities and runtime integration points."""


import asyncio
import httpx # Para chamadas HTTP assÃ­ncronas
import json
import re
import threading
import time
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
from Backend.application.services.basic_content_generation_service import BasicContentGenerationService
from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.core.api_key_validation import looks_like_openai_api_key, normalize_optional_secret
from Backend.core.config import settings
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.prompt_template_repository import (
    DEFAULT_PROMPT_TEMPLATES,
    PromptTemplateName,
    PromptTemplateRepository,
)
from Backend.infrastructure.repositories.external_credential_repository import (
    ExternalCredentialRepository,
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
    r"\b(?:comercio|com[eÃ©]rcio|eletronico|eletr[oÃ´]nico|loja|empresa|atendimento|contato|telefone|whatsapp|sac|site|ligue|chame|fale)\b",
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
    r"seu|sua|seus|suas|compre|tenha|melhore|renove|encante|celebre|leve\s+agora)\b",
    re.IGNORECASE,
)
TITLE_GENERIC_SUFFIX_PATTERN = re.compile(
    r"\b(?:decor|decoracao|decorativo|decorativa|colecao|colecao|produto|item|original|display)\b",
    re.IGNORECASE,
)
LOW_VALUE_SUMMARY_PATTERN = re.compile(
    r"(?:depende\s+do\s+contexto|elementos?\s+decorativos?\s+ou\s+funcionais|"
    r"aplicacoes?\s+diversas|protecao\s+e\s+acabamento\s+visual|"
    r"oferecer\s+suporte\s+e\s+revestimento)",
    re.IGNORECASE,
)
GENERIC_MATERIAL_VARIANT_TOKENS = {
    "aco",
    "abs",
    "aluminio",
    "borracha",
    "algodao",
    "composto",
    "eva",
    "friccao",
    "liga",
    "metal",
    "mesh",
    "plastico",
    "policarbonato",
    "poliester",
    "tactel",
    "vidro",
}
GENERIC_OBJECT_TITLE_HINTS = {
    "frame": "Moldura",
    "displayer": "Expositor",
    "display": "Expositor",
    "basket": "Cesta",
    "book": "Livro",
}
DESCRIPTION_SECTION_PATTERN = re.compile(
    r"\s+(Resumo tecnico:|Aplicacao:|Referencia:|Material:|Conteudo da embalagem:|Especificacoes tecnicas:|Destaques tecnicos:)",
    re.IGNORECASE,
)
DESCRIPTION_SECTION_TITLES = (
    "Resumo tecnico:",
    "Aplicacao:",
    "Referencia:",
    "Material:",
    "Conteudo da embalagem:",
    "Especificacoes tecnicas:",
    "Destaques tecnicos:",
)
SELLER_BRAND_PATTERN = re.compile(
    r"\b(?:loja|comercio|pecas?\s+para|auto\s*pecas|caminh(?:ao|oes)?|suporte|atendimento|oficial)\b",
    re.IGNORECASE,
)
ENGLISH_GENERATED_MARKERS = {
    "a",
    "an",
    "and",
    "at",
    "by",
    "for",
    "from",
    "home",
    "in",
    "including",
    "into",
    "item",
    "its",
    "landscapes",
    "nature",
    "of",
    "palette",
    "playful",
    "represents",
    "scene",
    "soft",
    "sprinkled",
    "the",
    "this",
    "with",
    "winter",
}
PORTUGUESE_GENERATED_MARKERS = {
    "acabamento",
    "aplicacao",
    "apresentacao",
    "com",
    "conteudo",
    "decorativo",
    "descricao",
    "embalagem",
    "especificacoes",
    "item",
    "linha",
    "para",
    "produto",
    "resumo",
    "tecnico",
    "uso",
}


class _OpenAICompatibleConcurrencyRegistry:
    """Keep shared concurrency gates stable across request-scoped runtimes."""

    _lock = threading.Lock()
    _lm_studio_semaphore: Optional[threading.BoundedSemaphore] = None
    _lm_studio_limit: Optional[int] = None

    @classmethod
    def get_lm_studio_semaphore(
        cls,
        *,
        limit: int,
    ) -> threading.BoundedSemaphore:
        """Return a shared LM Studio semaphore, rebuilding it when the limit changes."""
        safe_limit = max(1, int(limit))
        with cls._lock:
            if cls._lm_studio_semaphore is None or cls._lm_studio_limit != safe_limit:
                cls._lm_studio_semaphore = threading.BoundedSemaphore(safe_limit)
                cls._lm_studio_limit = safe_limit
            return cls._lm_studio_semaphore


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
        prompt_messages: List[Dict[str, Any]],
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

    def get_openai_provider_name(self) -> str:
        """Expose the active OpenAI-compatible provider to higher-level workflows."""
        return self._runtime.get_openai_provider_name()

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

    @staticmethod
    def _normalize_positive_int(raw_value: Any, *, default: int) -> int:
        """Normalize positive integer settings while tolerating malformed env values."""
        try:
            parsed_value = int(raw_value)
        except (TypeError, ValueError):
            parsed_value = default
        return max(1, parsed_value)

    def get_openai_compatible_max_concurrency(self) -> int:
        """Return the max number of concurrent OpenAI-compatible requests allowed."""
        if not self._is_lm_studio_enabled():
            return 0
        return self._normalize_positive_int(
            getattr(settings, "LM_STUDIO_MAX_CONCURRENCY", 1),
            default=1,
        )

    def get_openai_compatible_request_timeout_seconds(self) -> float:
        """Return the outbound request timeout for the active OpenAI-compatible provider."""
        if not self._is_lm_studio_enabled():
            return 60.0
        return float(
            self._normalize_positive_int(
                getattr(settings, "LM_STUDIO_REQUEST_TIMEOUT_SECONDS", 120),
                default=120,
            )
        )

    def get_lm_studio_description_word_target(self, requested_words: int) -> int:
        """Clamp local description targets so the loaded LM Studio model stays responsive."""
        normalized_requested = self._normalize_positive_int(requested_words, default=50)
        configured_target = self._normalize_positive_int(
            getattr(settings, "LM_STUDIO_DESCRIPTION_WORD_TARGET", 50),
            default=50,
        )
        return min(normalized_requested, configured_target)

    def get_lm_studio_description_max_tokens(self, requested_words: int) -> int:
        """Limit LM Studio description token budgets to avoid long-running local generations."""
        normalized_requested = self._normalize_positive_int(requested_words, default=50)
        configured_cap = self._normalize_positive_int(
            getattr(settings, "LM_STUDIO_DESCRIPTION_MAX_TOKENS", 150),
            default=150,
        )
        requested_cap = max(80, normalized_requested + 100)
        return min(configured_cap, requested_cap)

    def _get_openai_compatible_semaphore(self) -> Optional[threading.BoundedSemaphore]:
        """Return the shared semaphore used to protect the local LM Studio provider."""
        if not self._is_lm_studio_enabled():
            return None
        return _OpenAICompatibleConcurrencyRegistry.get_lm_studio_semaphore(
            limit=self.get_openai_compatible_max_concurrency(),
        )

    async def _acquire_openai_compatible_slot(
        self,
    ) -> tuple[Optional[threading.BoundedSemaphore], float]:
        """Acquire a provider slot before performing a heavy local generation call."""
        semaphore = self._get_openai_compatible_semaphore()
        if semaphore is None:
            return None, 0.0

        wait_started_at = time.perf_counter()
        await asyncio.to_thread(semaphore.acquire)
        waited_seconds = time.perf_counter() - wait_started_at
        return semaphore, waited_seconds

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

        if not hasattr(db, "query"):
            personal_key = normalize_optional_secret(getattr(user, "chave_openai_pessoal", None))
            if looks_like_openai_api_key(personal_key):
                return personal_key
            system_key = normalize_optional_secret(settings.OPENAI_API_KEY)
            return system_key if looks_like_openai_api_key(system_key) else None

        credential_repo = ExternalCredentialRepository(db)
        resolved = credential_repo.resolve_effective_source(
            provider=models.ExternalCredentialProviderEnum.OPENAI,
            current_user=user,
            settings=settings,
        )
        resolved_key = normalize_optional_secret(resolved.get("secret_value"))
        if looks_like_openai_api_key(resolved_key):
            logger.info("Usando chave OpenAI com origem efetiva: %s.", resolved.get("source"))
            return resolved_key
        if resolved_key:
            logger.warning(
                "Chave OpenAI ignorada para usuario ID %s: formato invalido (origem: %s).",
                user.id,
                resolved.get("source"),
            )

        logger.warning("Nenhuma chave OpenAI encontrada (nem pessoal, nem global).")
        return None

    async def get_gemini_api_key(
        self, db: Session, user: models.User
    ) -> Optional[str]:
        """Retrieve gemini api key using the current service dependencies."""
        if not hasattr(db, "query"):
            return (
                normalize_optional_secret(getattr(user, "chave_google_gemini_pessoal", None))
                or normalize_optional_secret(settings.GOOGLE_GEMINI_API_KEY)
            )

        credential_repo = ExternalCredentialRepository(db)
        resolved = credential_repo.resolve_effective_source(
            provider=models.ExternalCredentialProviderEnum.GOOGLE_GEMINI,
            current_user=user,
            settings=settings,
        )
        resolved_key = normalize_optional_secret(resolved.get("secret_value"))
        if resolved_key:
            logger.info("Usando chave Gemini com origem efetiva: %s.", resolved.get("source"))
            return resolved_key

        logger.warning("Nenhuma chave Gemini encontrada (nem pessoal, nem global).")
        return None

    async def call_openai_api(
        self,
        prompt_messages: List[Dict[str, Any]],
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

        provider_name = self.get_openai_provider_name()
        concurrency_semaphore: Optional[threading.BoundedSemaphore] = None
        try:
            concurrency_semaphore, waited_seconds = await self._acquire_openai_compatible_slot()
            if concurrency_semaphore is not None and waited_seconds >= 0.05:
                logger.info(
                    "LM Studio aguardou %.2fs por um slot livre de geracao (limite=%s).",
                    waited_seconds,
                    self.get_openai_compatible_max_concurrency(),
                )
            resolved_model = await self.resolve_openai_model(
                api_key=api_key,
                requested_model=model,
            )
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
                timeout_seconds=self.get_openai_compatible_request_timeout_seconds(),
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
        finally:
            if concurrency_semaphore is not None:
                concurrency_semaphore.release()

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

    _HUMAN_TEXT_NORMALIZER = WebEnrichmentNormalizationService()

    @classmethod
    def _normalize_multiline_human_text(cls, raw_text: Any) -> str:
        """Decode human text while preserving meaningful line breaks used by structured descriptions."""
        raw = str(raw_text or "").replace("\r\n", "\n").replace("\r", "\n")
        normalized_lines: List[str] = []
        for raw_line in raw.split("\n"):
            normalized_line = cls._HUMAN_TEXT_NORMALIZER.normalize_human_text(raw_line)
            normalized_lines.extend(
                segment for segment in str(normalized_line or "").replace("\r", "\n").split("\n")
            )
        return "\n".join(normalized_lines).strip()

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
    def _get_basic_content_service() -> BasicContentGenerationService:
        """Build the structured local content helper used as prompt context and fallback."""
        return BasicContentGenerationService(product_repository_factory=ProductRepository)

    @staticmethod
    def _normalize_prompt_line(value: Any) -> str:
        """Normalize arbitrary prompt fragments into compact printable lines."""
        return " ".join(str(value or "").strip().split())

    @classmethod
    def _looks_like_reference_code(cls, value: Any) -> bool:
        """Detect compact technical codes that are useful as title reference variants."""
        cleaned = cls._normalize_prompt_line(value)
        if not cleaned:
            return False

        folded = cls._fold_identity_text(cleaned)
        if len(cleaned) > 40 or len(cleaned.split()) > 3:
            return False
        if re.search(r"\b(?:llm|smoke|test|teste|demo|sample|tmp|temp)\b", folded):
            return False
        return bool(re.search(r"\d", cleaned) and re.fullmatch(r"[A-Za-z0-9./_-]{4,40}", cleaned))

    @classmethod
    def _resolve_title_reference_signal(
        cls,
        *,
        referencia: Any = None,
        modelo: Any = None,
    ) -> str:
        """Prefer extracted reference, but fall back to model codes when they look technical."""
        explicit_reference = cls._normalize_prompt_line(referencia)
        if explicit_reference:
            return explicit_reference

        normalized_model = cls._normalize_prompt_line(modelo)
        if cls._looks_like_reference_code(normalized_model):
            return normalized_model
        return ""

    @classmethod
    def _looks_like_seller_brand(cls, value: Any) -> bool:
        """Detect seller/store names that should not be surfaced as manufacturer brand."""
        cleaned = cls._clean_single_title_candidate(value)
        if not cleaned:
            return False
        return bool(SELLER_BRAND_PATTERN.search(cleaned))

    @classmethod
    def _detect_product_segment(
        cls,
        *,
        db_produto: Any,
        technical_facts: Dict[str, Any],
        categoria: Any,
    ) -> str:
        """Classify whether the product context is automotive or generic."""
        automotive_signal_tokens = (
            "automot",
            "veicul",
            "montadora",
            "caminhao",
            "carro",
            "moto",
            "farol",
            "paralama",
            "embreagem",
            "combust",
            "freio",
            "suspens",
            "motor",
            "radiador",
            "scania",
            "volvo",
            "mercedes",
            "iveco",
            "ford cargo",
            "volkswagen",
            "toyota",
            "chevrolet",
            "fiat",
            "renault",
            "hyundai",
            "nissan",
            "linha pesada",
            "linha leve",
        )
        raw_fragments = [
            getattr(db_produto, "nome_base", ""),
            getattr(db_produto, "nome_chat_api", ""),
            getattr(db_produto, "descricao_original", ""),
            getattr(db_produto, "categoria_original", ""),
            getattr(db_produto, "categoria_mapeada", ""),
            categoria,
            technical_facts.get("application", ""),
            technical_facts.get("vehicle_make", ""),
            technical_facts.get("technical_summary", ""),
        ]
        folded_context = " ".join(
            fragment
            for fragment in (cls._fold_identity_text(item) for item in raw_fragments)
            if fragment
        )
        if not folded_context:
            return "geral"
        if any(signal in folded_context for signal in automotive_signal_tokens):
            return "automotivo"
        return "geral"

    @classmethod
    def _build_domain_guardrail_text(
        cls,
        *,
        prompt_context: Dict[str, Any],
        target: str,
    ) -> str:
        """Inject domain guidance so non-automotive items are not forced into vehicle language."""
        segmento = cls._fold_identity_text(prompt_context.get("segmento_produto"))
        if segmento == "automotivo":
            return ""
        if target == "description":
            return (
                "Contexto de dominio obrigatorio: este item nao pertence ao segmento automotivo. "
                "Nao trate o produto como peca veicular e nao mencione veiculo, montadora, painel, "
                "linha leve, linha pesada, motor, freio ou compatibilidade automotiva sem confirmacao explicita.\n"
            )
        return (
            "Contexto de dominio obrigatorio: este item nao pertence ao segmento automotivo. "
            "Preserve o nome original do item e nao introduza montadora, veiculo, aplicacao automotiva "
            "ou termos de peca veicular sem confirmacao explicita.\n"
        )

    @classmethod
    def _build_generic_object_title_alias(
        cls,
        *,
        source_title: Any,
        segmento_produto: Any,
    ) -> str:
        """Add a neutral object-type hint for short generic catalog names when context is sparse."""
        if cls._fold_identity_text(segmento_produto) == "automotivo":
            return ""
        clean_source = cls._clean_single_title_candidate(source_title)
        if not clean_source:
            return ""
        tokens = [token for token in re.findall(r"[A-Za-z0-9]+", clean_source) if token]
        if len(tokens) < 2 or len(tokens) > 4:
            return ""
        folded_source = cls._fold_identity_text(clean_source)
        hint = GENERIC_OBJECT_TITLE_HINTS.get(cls._fold_identity_text(tokens[-1]))
        if not hint or cls._fold_identity_text(hint) in folded_source:
            return ""
        return cls._normalize_prompt_line(f"{clean_source} {hint}")

    @classmethod
    def _build_generation_prompt_context(
        cls,
        *,
        db_produto: Any,
        tamanho_palavras: int = 150,
        minimum_tamanho_palavras: int = 120,
    ) -> Dict[str, Any]:
        """Build a richer, structured prompt context from web data and local technical extraction."""
        basic_service = cls._get_basic_content_service()
        web_context = basic_service._extract_web_context(produto=db_produto)
        technical_facts = basic_service._extract_technical_facts(
            produto=db_produto,
            web_context=web_context,
        )
        structured_titles = basic_service._build_title_candidates(
            produto=db_produto,
            web_context=web_context,
        )
        fallback_description_words = max(120, int(tamanho_palavras or 120))
        structured_description = basic_service._build_basic_description(
            produto=db_produto,
            tamanho_palavras=fallback_description_words,
            template_descricao=basic_service._DEFAULT_DESCRIPTION_TEMPLATE,
        )
        structured_description = cls._sanitize_generated_description(structured_description)
        structured_preamble, structured_sections = cls._parse_description_sections(structured_description)
        if structured_sections:
            structured_description = cls._render_description_sections(
                structured_preamble,
                structured_sections,
            )

        nome_base = cls._normalize_prompt_line(
            getattr(db_produto, "nome_base", None) or getattr(db_produto, "nome_chat_api", None)
        ) or "Produto"
        nome_secundario = cls._normalize_prompt_line(getattr(db_produto, "nome_chat_api", None))
        marca = cls._normalize_prompt_line(
            basic_service._resolve_generation_brand(produto=db_produto, web_context=web_context)
        )
        if cls._looks_like_seller_brand(marca):
            marca = ""
        modelo = cls._normalize_prompt_line(getattr(db_produto, "modelo", None))
        referencia_extraida = cls._normalize_prompt_line(technical_facts.get("reference"))
        referencia = cls._resolve_title_reference_signal(
            referencia=referencia_extraida,
            modelo=modelo,
        )
        aplicacao = cls._normalize_prompt_line(technical_facts.get("application"))
        material = cls._normalize_prompt_line(technical_facts.get("material"))
        conteudo = cls._normalize_prompt_line(technical_facts.get("content"))
        categoria = basic_service._sanitize_title_fragment(
            getattr(db_produto, "categoria_mapeada", "") or getattr(db_produto, "categoria_original", ""),
            cut_on_contact_marker=True,
            max_len=80,
        )
        segmento_produto = cls._detect_product_segment(
            db_produto=db_produto,
            technical_facts=technical_facts,
            categoria=categoria,
        )
        stable_fallback_description = cls._finalize_structured_description(
            structured_description,
            product_name=nome_base,
            fallback_text=structured_description,
        )

        specs = []
        for line in stable_fallback_description.splitlines():
            clean_line = cls._normalize_prompt_line(line)
            if clean_line.startswith("- "):
                specs.append(clean_line)
        specs_text = "\n".join(specs[:6])

        filtered_titles: List[str] = []
        for title in structured_titles:
            clean_title = cls._normalize_prompt_line(title)
            folded_title = cls._fold_identity_text(clean_title)
            if not clean_title:
                continue
            if re.search(r"\b(?:variante|opcao)\b", folded_title):
                continue
            if clean_title != nome_base and len(clean_title.split()) < 2 and not any(char.isdigit() for char in clean_title):
                continue
            filtered_titles.append(clean_title)
        if not filtered_titles:
            filtered_titles = [nome_base]

        aliases = [alias for alias in filtered_titles[1:5] if cls._normalize_prompt_line(alias)]
        if nome_secundario:
            aliases.append(nome_secundario)
        if referencia:
            aliases.append(cls._normalize_prompt_line(f"{nome_base} Ref {referencia}"))
        if aplicacao:
            aliases.append(cls._normalize_prompt_line(f"{nome_base} {aplicacao}"))
        if conteudo:
            aliases.append(cls._normalize_prompt_line(f"{nome_base} {conteudo}"))
        if categoria:
            aliases.append(cls._normalize_prompt_line(f"{nome_base} {categoria}"))
        generic_object_alias = cls._build_generic_object_title_alias(
            source_title=nome_base,
            segmento_produto=segmento_produto,
        )
        if generic_object_alias:
            aliases.append(generic_object_alias)
        aliases = cls._filter_prompt_source_aliases(
            primary_source=nome_base,
            aliases=aliases,
        )

        return {
            "nome_base": nome_base,
            "nome_secundario": nome_secundario,
            "marca": marca,
            "modelo": modelo,
            "descricao": stable_fallback_description,
            "referencia": referencia,
            "referencia_extraida": referencia_extraida,
            "aplicacao": aplicacao,
            "material": material,
            "conteudo": conteudo,
            "categoria": categoria,
            "segmento_produto": segmento_produto,
            "contexto_tecnico": stable_fallback_description,
            "specs": specs_text,
            "source_title": nome_base,
            "source_aliases": aliases,
            "fallback_titles": cls._select_final_title_candidates(
                prompt_context={
                    "source_title": nome_base,
                    "source_aliases": aliases,
                    "fallback_titles": filtered_titles,
                    "referencia": referencia,
                    "marca": marca,
                    "material": material,
                    "aplicacao": aplicacao,
                    "conteudo": conteudo,
                    "categoria": categoria,
                },
                llm_titles=[],
                desired_count=max(5, len(filtered_titles)),
            ),
            "fallback_description": stable_fallback_description,
        }

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
        text = IAGenerationRuntime._normalize_multiline_human_text(raw_text)
        if not text:
            return ""

        text = DESCRIPTION_META_PREFIX_PATTERN.sub("", text)
        text = DESCRIPTION_SECTION_PATTERN.sub(r"\n\1", text)
        text = re.sub(r"\s+-\s+", "\n- ", text)

        filtered_lines: List[str] = []
        last_non_empty = ""
        for raw_line in text.splitlines():
            normalized_line = " ".join(str(raw_line or "").strip().split())
            if not normalized_line:
                if filtered_lines and filtered_lines[-1] != "":
                    filtered_lines.append("")
                continue
            if normalized_line in {"-", "*", "•"}:
                continue
            bullet_prefix = ""
            if normalized_line.startswith(("- ", "* ", "• ")):
                bullet_prefix = "- "
                normalized_line = normalized_line[2:].strip()
            normalized_line = re.sub(r"\.{3,}", ".", normalized_line)
            normalized_line = " ".join(normalized_line.split())
            normalized_line = re.sub(r"\s+([,.;:!?])", r"\1", normalized_line)
            if not normalized_line:
                continue
            if normalized_line.endswith(":"):
                if normalized_line == last_non_empty:
                    continue
                filtered_lines.append(normalized_line)
                last_non_empty = normalized_line
                continue

            candidate_chunks = (
                [normalized_line]
                if bullet_prefix
                else [chunk for chunk in re.split(r"(?<=[.!?])\s+", normalized_line) if chunk]
            )
            for chunk in candidate_chunks:
                candidate = " ".join(chunk.strip().split())
                if not candidate:
                    continue
                if IAGenerationRuntime._looks_like_company_timeline_claim(candidate):
                    continue
                if DESCRIPTION_PROMOTIONAL_PATTERN.search(candidate):
                    continue
                if IAGenerationRuntime._looks_like_english_generated_fragment(candidate):
                    continue
                if re.search(r"\burl da fonte\b", candidate, re.IGNORECASE):
                    continue
                if bullet_prefix:
                    candidate = f"{bullet_prefix}{candidate}"
                if candidate == last_non_empty:
                    continue
                filtered_lines.append(candidate)
                last_non_empty = candidate

        while filtered_lines and filtered_lines[-1] == "":
            filtered_lines.pop()

        if not filtered_lines:
            return ""
        return "\n".join(filtered_lines).strip()

    @staticmethod
    def _looks_like_english_generated_fragment(text: Any) -> bool:
        """Reject long raw English scrape fragments before final visible output."""
        raw_text = str(text or "")
        compact = " ".join(str(raw_text or "").strip().split())
        if not compact:
            return False
        if re.search(r"%[0-9A-Fa-f]{2}", raw_text):
            return True
        folded = IAGenerationRuntime._fold_identity_text(compact)
        if any(
            phrase in folded
            for phrase in (
                "this collection",
                "including the",
                "represents winter",
                "soft palette",
                "playful details of nature",
            )
        ):
            return True
        tokens = re.findall(r"[a-z]+", folded)
        if len(tokens) < 6:
            return False
        english_hits = sum(token in ENGLISH_GENERATED_MARKERS for token in tokens)
        portuguese_hits = sum(token in PORTUGUESE_GENERATED_MARKERS for token in tokens)
        return english_hits >= 3 and english_hits > max(1, portuguese_hits * 2)

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
        cleaned = IAGenerationRuntime._strip_suspicious_contact_fragments_from_title(cleaned)
        marker_match = TITLE_CONTACT_MARKER_PATTERN.search(cleaned)
        if marker_match:
            cleaned = cleaned[: marker_match.start()]
        cleaned = TITLE_CONTACT_MARKER_PATTERN.sub(" ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" -|,;:/")
        if len(cleaned) < 4:
            return ""
        if IAGenerationRuntime._looks_like_company_timeline_claim(cleaned):
            return ""
        if (
            URL_PATTERN.search(cleaned)
            or EMAIL_PATTERN.search(cleaned)
            or IAGenerationRuntime._title_contains_suspicious_contact_number(cleaned)
        ):
            return ""
        return cleaned

    @classmethod
    def _numeric_fragment_looks_like_contact(
        cls,
        *,
        full_text: str,
        match: re.Match[str],
    ) -> bool:
        """Distinguish real contact numbers from technical product codes inside titles."""
        candidate = match.group(0)
        digits_only = re.sub(r"\D", "", candidate)
        if not digits_only:
            return False

        has_separator = bool(re.search(r"[\s()./-]", candidate))
        prefix_window = cls._fold_identity_text(full_text[max(0, match.start() - 24):match.start()])
        if any(keyword in prefix_window for keyword in ("modelo", "referencia", "ref", "codigo", "sku")):
            return False
        if not has_separator and len(digits_only) <= 12:
            return False
        if "+" in candidate:
            return True
        if len(digits_only) >= 10 and has_separator:
            return True
        return any(keyword in prefix_window for keyword in ("telefone", "celular", "whatsapp", "ligue", "fone", "contato"))

    @classmethod
    def _strip_suspicious_contact_fragments_from_title(cls, text: Any) -> str:
        """Remove contact-like numeric fragments while preserving technical references."""
        raw_text = str(text or "")
        result: List[str] = []
        last_index = 0
        finditer = getattr(PHONE_OR_ID_BLOCK_PATTERN, "finditer", None)
        matches = list(finditer(raw_text)) if callable(finditer) else []
        for match in matches:
            if not cls._numeric_fragment_looks_like_contact(full_text=raw_text, match=match):
                continue
            result.append(raw_text[last_index:match.start()])
            result.append(" ")
            last_index = match.end()
        result.append(raw_text[last_index:])
        return "".join(result)

    @classmethod
    def _title_contains_suspicious_contact_number(cls, text: Any) -> bool:
        """Return True when a title still contains a contact-like phone number fragment."""
        raw_text = str(text or "")
        finditer = getattr(PHONE_OR_ID_BLOCK_PATTERN, "finditer", None)
        if not callable(finditer):
            return False
        return any(
            cls._numeric_fragment_looks_like_contact(full_text=raw_text, match=match)
            for match in finditer(raw_text)
        )

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
    def _filter_prompt_source_aliases(
        cls,
        *,
        primary_source: Any,
        aliases: Optional[List[Any]] = None,
    ) -> List[str]:
        """Keep only aliases that still clearly preserve the primary source identity."""
        primary_clean = cls._clean_single_title_candidate(primary_source)
        if not primary_clean:
            return []

        selected: List[str] = []
        seen: set[str] = set()
        for alias in aliases or []:
            cleaned_alias = cls._clean_single_title_candidate(alias)
            if not cleaned_alias:
                continue
            normalized_alias = cls._fold_identity_text(cleaned_alias)
            if normalized_alias == cls._fold_identity_text(primary_clean):
                continue
            if normalized_alias in seen:
                continue
            if not cls._candidate_preserves_source_identity(
                cleaned_alias,
                source_variants=[primary_clean],
            ):
                continue
            seen.add(normalized_alias)
            selected.append(cleaned_alias)
        return selected

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
        source_signal_tokens = set(re.findall(r"[a-z0-9]+", folded_source))

        if TITLE_PROMOTIONAL_TOKEN_PATTERN.search(folded_candidate):
            return True

        generic_match = TITLE_GENERIC_SUFFIX_PATTERN.search(folded_candidate)
        if generic_match and source_signal_tokens and generic_match.group(0).strip() not in source_signal_tokens:
            return True
        if re.search(r"\b(?:g/r|serie\s+\d|ate\s+\d{4}|até\s+\d{4})\b", folded_candidate):
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
        if len(words) >= 2:
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
    def _score_title_candidate(
        cls,
        candidate: str,
        *,
        primary_source: str,
        prompt_context: Dict[str, Any],
    ) -> tuple[int, int, int]:
        """Score titles so the final list prefers identity-preserving technical variants."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        cleaned_source = cls._clean_single_title_candidate(primary_source)
        if not cleaned_candidate or not cleaned_source:
            return (-1000, 0, 0)

        folded_candidate = cls._fold_identity_text(cleaned_candidate)
        folded_source = cls._fold_identity_text(cleaned_source)
        candidate_tokens = set(cls._tokenize_title_identity(cleaned_candidate))
        source_tokens = set(cls._tokenize_title_identity(cleaned_source))
        overlap = len(candidate_tokens & source_tokens)

        score = 0
        if folded_candidate == folded_source:
            score += 100
        if folded_candidate.startswith(folded_source):
            score += 40
        score += overlap * 18

        reference = cls._fold_identity_text(prompt_context.get("referencia"))
        if reference:
            reference_in_primary = reference in folded_source
            if reference_in_primary:
                if reference in folded_candidate and re.search(r"\bref(?:erencia)?\b", folded_candidate):
                    score += 18
            elif reference in folded_candidate:
                score += 18

        brand = cls._fold_identity_text(prompt_context.get("marca"))
        if brand and brand in folded_candidate:
            score += 14

        material = cls._fold_identity_text(prompt_context.get("material"))
        if material and material in folded_candidate:
            score += 8

        application_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("aplicacao")))
            if len(token) >= 4
        ][:3]
        if application_tokens and any(token in folded_candidate for token in application_tokens):
            score += 10

        category_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("categoria")))
            if len(token) >= 4
        ][:3]
        if category_tokens and any(token in folded_candidate for token in category_tokens):
            score += 8

        if re.search(r"\b(?:1\s*peca|1\s*peça|unitario|unitária)\b", folded_candidate):
            score -= 20
        if re.search(r"\b(?:frontal|grade\s+superior|superior)\b", folded_candidate) and overlap < max(2, len(source_tokens)):
            score -= 8
        if re.search(r"\b(?:g/r|serie\s+\d|ate\s+\d{4}|até\s+\d{4})\b", folded_candidate):
            score -= 14
        if "/" in cleaned_candidate and "ref" not in folded_candidate:
            score -= 10

        return (score, -len(cleaned_candidate), -len(candidate_tokens))

    @classmethod
    def _title_has_incomplete_reference_token(cls, candidate: Any, *, reference: Any = None) -> bool:
        """Reject titles that mention a bare reference marker without the actual code/value."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        if not cleaned_candidate:
            return True

        folded_candidate = cls._fold_identity_text(cleaned_candidate)
        reference_text = cls._fold_identity_text(reference)
        if not re.search(r"\bref(?:erencia)?\b", folded_candidate):
            return False
        if reference_text and reference_text in folded_candidate:
            return False

        if re.search(r"\bref(?:erencia)?\b\s*$", folded_candidate):
            return True

        trailing_fragment = re.split(r"\bref(?:erencia)?\b", folded_candidate, maxsplit=1)[1].strip()
        if not trailing_fragment:
            return True
        if len(re.findall(r"[a-z0-9]+", trailing_fragment)) <= 1 and len(trailing_fragment) <= 4:
            return True
        return False

    @classmethod
    def _select_final_title_candidates(
        cls,
        *,
        prompt_context: Dict[str, Any],
        llm_titles: Optional[List[str]] = None,
        desired_count: int,
    ) -> List[str]:
        """Merge LLM output with deterministic fallbacks and keep only strong final variants."""
        primary_source = cls._clean_single_title_candidate(prompt_context.get("source_title")) or "Produto"
        source_aliases = cls._filter_prompt_source_aliases(
            primary_source=primary_source,
            aliases=prompt_context.get("source_aliases") or [],
        )

        pool: List[str] = []
        reference = prompt_context.get("referencia")
        for candidate in [
            *(llm_titles or []),
            *(prompt_context.get("fallback_titles") or []),
            *(prompt_context.get("source_aliases") or []),
        ]:
            cleaned = cls._clean_single_title_candidate(candidate)
            if (
                cleaned
                and not cls._title_has_incomplete_reference_token(cleaned, reference=reference)
                and not cls._candidate_has_no_semantic_gain(
                    cleaned,
                    primary_source=primary_source,
                    reference=reference,
                )
                and not cls._candidate_is_low_value_material_variant(
                    cleaned,
                    prompt_context=prompt_context,
                    primary_source=primary_source,
                )
            ):
                pool.append(cleaned)

        reconciled = cls._reconcile_title_candidates_with_source(
            pool,
            source_title=primary_source,
            source_aliases=source_aliases,
            desired_count=max(1, int(desired_count or 1)),
        )

        unique_candidates: List[str] = []
        seen: set[str] = set()
        for candidate in reconciled:
            normalized = cls._fold_identity_text(candidate)
            if normalized in seen:
                continue
            seen.add(normalized)
            unique_candidates.append(candidate)

        ranked = sorted(
            unique_candidates,
            key=lambda item: cls._score_title_candidate(
                item,
                primary_source=primary_source,
                prompt_context=prompt_context,
            ),
            reverse=True,
        )

        if primary_source:
            ranked = [primary_source, *[item for item in ranked if cls._fold_identity_text(item) != cls._fold_identity_text(primary_source)]]

        ranked = cls._promote_diverse_title_variants(
            ranked,
            prompt_context=prompt_context,
            desired_count=max(1, int(desired_count or 1)),
        )

        return ranked[: max(1, int(desired_count or 1))]

    @classmethod
    def _candidate_has_no_semantic_gain(
        cls,
        candidate: Any,
        *,
        primary_source: str,
        reference: Any,
    ) -> bool:
        """Reject variants that add no new technical signal beyond the base title."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        cleaned_source = cls._clean_single_title_candidate(primary_source)
        if not cleaned_candidate or not cleaned_source:
            return False
        if cls._fold_identity_text(cleaned_candidate) == cls._fold_identity_text(cleaned_source):
            return False

        if reference:
            folded_reference = cls._fold_identity_text(reference)
            if folded_reference and folded_reference in cls._fold_identity_text(cleaned_candidate):
                return False

        candidate_tokens = set(cls._tokenize_title_identity(cleaned_candidate))
        source_tokens = set(cls._tokenize_title_identity(cleaned_source))
        if not candidate_tokens or not source_tokens:
            return False
        return not (candidate_tokens - source_tokens)

    @classmethod
    def _candidate_is_low_value_material_variant(
        cls,
        candidate: Any,
        *,
        prompt_context: Dict[str, Any],
        primary_source: str,
    ) -> bool:
        """Reject variants that only append generic raw material tokens to the base title."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        if not cleaned_candidate:
            return False

        material_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("material")))
            if len(token) >= 3
        ]
        if not material_tokens or any(token not in GENERIC_MATERIAL_VARIANT_TOKENS for token in material_tokens):
            return False

        candidate_tokens = set(cls._tokenize_title_identity(cleaned_candidate))
        source_tokens = set(cls._tokenize_title_identity(primary_source))
        extra_tokens = candidate_tokens - source_tokens
        if not extra_tokens:
            return False
        return extra_tokens <= set(material_tokens)

    @classmethod
    def _title_variant_categories(cls, candidate: Any, *, prompt_context: Dict[str, Any]) -> set[str]:
        """Classify title candidates by the extra technical signal they add beyond the base identity."""
        cleaned_candidate = cls._clean_single_title_candidate(candidate)
        if not cleaned_candidate:
            return set()

        folded_candidate = cls._fold_identity_text(cleaned_candidate)
        categories: set[str] = set()
        primary_source = cls._fold_identity_text(prompt_context.get("source_title"))

        reference = cls._fold_identity_text(prompt_context.get("referencia"))
        if reference:
            reference_in_primary = reference in primary_source
            if reference_in_primary:
                if reference in folded_candidate and re.search(r"\bref(?:erencia)?\b", folded_candidate):
                    categories.add("reference")
            elif reference in folded_candidate:
                categories.add("reference")

        brand = cls._fold_identity_text(prompt_context.get("marca"))
        if brand and brand in folded_candidate and brand not in primary_source:
            categories.add("brand")

        material = cls._fold_identity_text(prompt_context.get("material"))
        if (
            material
            and material in folded_candidate
            and material not in primary_source
            and not cls._candidate_is_low_value_material_variant(
                cleaned_candidate,
                prompt_context=prompt_context,
                primary_source=prompt_context.get("source_title") or "",
            )
        ):
            categories.add("material")

        application_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("aplicacao")))
            if len(token) >= 4
        ][:3]
        if application_tokens and any(token in folded_candidate for token in application_tokens):
            categories.add("application")

        content_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("conteudo")))
            if len(token) >= 4
        ][:4]
        if content_tokens and any(token in folded_candidate for token in content_tokens):
            categories.add("content")

        category_tokens = [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_identity_text(prompt_context.get("categoria")))
            if len(token) >= 4
        ][:3]
        if category_tokens and any(token in folded_candidate for token in category_tokens):
            categories.add("category")

        return categories

    @classmethod
    def _promote_diverse_title_variants(
        cls,
        ranked_candidates: List[str],
        *,
        prompt_context: Dict[str, Any],
        desired_count: int,
    ) -> List[str]:
        """Prefer a compact set of title variants that adds useful technical diversity."""
        if not ranked_candidates or desired_count <= 1:
            return ranked_candidates

        selected: List[str] = []
        seen: set[str] = set()

        primary = ranked_candidates[0]
        primary_folded = cls._fold_identity_text(primary)
        selected.append(primary)
        seen.add(primary_folded)

        remaining = [candidate for candidate in ranked_candidates[1:] if cls._fold_identity_text(candidate) not in seen]
        for category in ("reference", "application", "content", "category", "material", "brand"):
            if len(selected) >= desired_count:
                break
            for candidate in remaining:
                if category in cls._title_variant_categories(candidate, prompt_context=prompt_context):
                    folded_candidate = cls._fold_identity_text(candidate)
                    if folded_candidate in seen:
                        continue
                    selected.append(candidate)
                    seen.add(folded_candidate)
                    break

        for candidate in ranked_candidates:
            folded_candidate = cls._fold_identity_text(candidate)
            if folded_candidate in seen:
                continue
            selected.append(candidate)
            seen.add(folded_candidate)
            if len(selected) >= desired_count:
                break

        return selected

    @classmethod
    def _finalize_structured_description(
        cls,
        raw_text: Any,
        *,
        product_name: Any,
        fallback_text: Any = "",
    ) -> str:
        """Return a structured description with a stable heading and required sections."""
        primary_name = cls._normalize_prompt_line(product_name) or "Produto"
        description = cls._sanitize_generated_description(raw_text)
        fallback_description = cls._sanitize_generated_description(fallback_text)
        if not description or description.count("\n") < 3:
            description = fallback_description

        if not description:
            return primary_name

        folded_name = cls._fold_identity_text(primary_name)
        description_lines = [line.rstrip() for line in description.splitlines()]
        first_non_empty = next((line.strip() for line in description_lines if line.strip()), "")
        first_non_empty_folded = cls._fold_identity_text(first_non_empty)
        if first_non_empty_folded != folded_name:
            description = f"{primary_name}\n\n{description}"

        description = cls._replace_invalid_summary_section(
            description,
            product_name=primary_name,
            fallback_text=fallback_description,
        )
        preamble, sections = cls._parse_description_sections(description)
        preamble = cls._stabilize_description_preamble(
            preamble,
            product_name=primary_name,
            has_sections=bool(sections),
        )
        normalized_sections: List[tuple[str, List[str]]] = []
        for heading, lines in sections:
            if heading == "Resumo tecnico:":
                lines = cls._strip_redundant_product_name_from_summary_lines(
                    list(lines),
                    product_name=primary_name,
                )
            normalized_sections.append((heading, lines))
        description = cls._render_description_sections(preamble, normalized_sections)
        description = re.sub(r"\n{3,}", "\n\n", description).strip()
        return description

    @classmethod
    def _stabilize_description_preamble(
        cls,
        preamble: List[str],
        *,
        product_name: str,
        has_sections: bool,
    ) -> List[str]:
        """Collapse repeated fragmented preambles into a single stable product heading."""
        normalized_product_name = cls._normalize_prompt_line(product_name)
        if not normalized_product_name:
            return preamble

        product_tokens = set(re.findall(r"[a-z0-9]+", cls._fold_identity_text(normalized_product_name)))
        cleaned_lines: List[str] = []
        saw_fragmented_identity = False
        seen: set[str] = set()

        for raw_line in preamble:
            clean_line = cls._normalize_prompt_line(raw_line)
            if not clean_line:
                continue
            folded_line = cls._fold_identity_text(clean_line)
            if folded_line in seen:
                saw_fragmented_identity = True
                continue
            seen.add(folded_line)
            if folded_line == cls._fold_identity_text(normalized_product_name):
                saw_fragmented_identity = True
                continue
            line_tokens = set(re.findall(r"[a-z0-9]+", folded_line))
            if has_sections and (
                clean_line.startswith("- ")
                or (
                    line_tokens
                    and product_tokens
                    and line_tokens.issubset(product_tokens)
                    and len(line_tokens) <= max(4, len(product_tokens))
                )
            ):
                saw_fragmented_identity = True
                continue
            cleaned_lines.append(clean_line)

        if has_sections and saw_fragmented_identity:
            return [normalized_product_name]
        if not cleaned_lines:
            return [normalized_product_name]
        if cls._fold_identity_text(cleaned_lines[0]) != cls._fold_identity_text(normalized_product_name):
            cleaned_lines.insert(0, normalized_product_name)
        return cleaned_lines

    @classmethod
    def _parse_description_sections(cls, text: Any) -> tuple[List[str], List[tuple[str, List[str]]]]:
        """Parse a structured description into preamble lines plus ordered titled sections."""
        preamble: List[str] = []
        sections: List[tuple[str, List[str]]] = []
        current_heading: Optional[str] = None

        for raw_line in str(text or "").splitlines():
            line = raw_line.rstrip()
            stripped = line.strip()
            matched_heading = next(
                (
                    heading
                    for heading in DESCRIPTION_SECTION_TITLES
                    if stripped.lower() == heading.lower() or stripped.lower().startswith(heading.lower())
                ),
                None,
            )
            if matched_heading is not None:
                current_heading = matched_heading
                sections.append((matched_heading, []))
                inline_content = stripped[len(matched_heading) :].strip()
                if inline_content:
                    sections[-1][1].append(inline_content)
                continue
            if current_heading and sections:
                sections[-1][1].append(line)
            else:
                preamble.append(line)
        return preamble, sections

    @classmethod
    def _render_description_sections(
        cls,
        preamble: List[str],
        sections: List[tuple[str, List[str]]],
    ) -> str:
        """Rebuild a structured description after section rewrites."""
        rendered: List[str] = [line for line in preamble]
        for heading, lines in sections:
            if rendered and rendered[-1].strip():
                rendered.append("")
            rendered.append(heading)
            rendered.extend(lines)
        return "\n".join(rendered).strip()

    @classmethod
    def _strip_redundant_product_name_from_summary_lines(
        cls,
        lines: List[str],
        *,
        product_name: str,
    ) -> List[str]:
        """Avoid repeating the full product name at the start of the summary body."""
        if not lines:
            return lines

        first_line = cls._normalize_prompt_line(lines[0])
        normalized_product_name = cls._normalize_prompt_line(product_name)
        if not first_line or not normalized_product_name:
            return lines

        folded_first_line = cls._fold_identity_text(first_line)
        folded_product_name = cls._fold_identity_text(normalized_product_name)
        if not re.match(
            rf"^{re.escape(folded_product_name)}(?:[\s\-:,.]+)",
            folded_first_line,
        ):
            return lines

        trimmed_line = first_line[len(normalized_product_name):].lstrip(" -:,.")
        if not trimmed_line or len(trimmed_line.split()) < 3:
            return lines
        if cls._fold_identity_text(trimmed_line) == folded_product_name:
            return lines
        if trimmed_line[:1].islower():
            return lines
        return [trimmed_line, *lines[1:]]

    @classmethod
    def _description_tail_looks_truncated(cls, description: str) -> bool:
        """Detect descriptions that were cut mid-section by a local max-token limit."""
        non_empty_lines = [line.strip() for line in str(description or "").splitlines() if line.strip()]
        if not non_empty_lines:
            return False

        last_line = non_empty_lines[-1]
        if last_line in DESCRIPTION_SECTION_TITLES or last_line.endswith(":"):
            return True

        if re.search(r"\b(?:resumo|aplicacao|referencia|material|conteudo|especificacoes|destaques)\b$", last_line, re.IGNORECASE):
            return True

        if last_line.startswith("- "):
            bullet_tokens = re.findall(r"[A-Za-z0-9À-ÿ]+", last_line)
            if len(bullet_tokens) < 3:
                return True
            if len(bullet_tokens) <= 8 and not re.search(r"[.!?)]$", last_line):
                return True
        return False

    @classmethod
    def _compose_summary_first_description(
        cls,
        description: str,
        *,
        product_name: str,
        fallback_text: str,
    ) -> str:
        """Use LLM output only for the summary section and keep the remaining sections deterministic."""
        description = cls._sanitize_generated_description(description)
        fallback_text = cls._sanitize_generated_description(fallback_text)
        generated_preamble, generated_sections = cls._parse_description_sections(description)
        fallback_preamble, fallback_sections = cls._parse_description_sections(fallback_text)
        fallback_map = {heading: list(lines) for heading, lines in fallback_sections}

        generated_summary = next(
            (
                [line for line in lines if line.strip()]
                for heading, lines in generated_sections
                if heading == "Resumo tecnico:" and any(line.strip() for line in lines)
            ),
            None,
        )
        if generated_summary is None:
            generated_summary = [
                line for line in generated_preamble
                if line.strip() and cls._fold_identity_text(line.strip()) != cls._fold_identity_text(product_name)
            ]

        if not generated_summary:
            return cls._finalize_structured_description(
                fallback_text,
                product_name=product_name,
                fallback_text=fallback_text,
            )

        summary_lines = [line.rstrip() for line in generated_summary if line.strip()]
        highlight_lines = cls._build_highlight_lines_from_summary(
            summary_lines,
            fallback_lines=fallback_map.get("Destaques tecnicos:", []),
        )
        repaired_sections: List[tuple[str, List[str]]] = []
        for heading in DESCRIPTION_SECTION_TITLES:
            if heading == "Resumo tecnico:":
                repaired_sections.append((heading, summary_lines))
                continue
            if heading == "Destaques tecnicos:" and highlight_lines:
                repaired_sections.append((heading, highlight_lines))
                continue
            if heading in fallback_map:
                repaired_sections.append((heading, fallback_map[heading]))

        repaired = cls._render_description_sections(
            fallback_preamble,
            repaired_sections,
        )
        return cls._finalize_structured_description(
            repaired,
            product_name=product_name,
            fallback_text=fallback_text,
        )

    @classmethod
    def _repair_truncated_description_with_fallback(
        cls,
        description: str,
        *,
        product_name: str,
        fallback_text: str,
    ) -> str:
        """Keep the generated summary when possible and restore missing structured sections from fallback."""
        description = cls._sanitize_generated_description(description)
        fallback_text = cls._sanitize_generated_description(fallback_text)
        if not cls._description_tail_looks_truncated(description):
            return description

        generated_preamble, generated_sections = cls._parse_description_sections(description)
        fallback_preamble, fallback_sections = cls._parse_description_sections(fallback_text)
        fallback_map = {heading: list(lines) for heading, lines in fallback_sections}
        generated_summary = next(
            (
                [line for line in lines if line.strip()]
                for heading, lines in generated_sections
                if heading == "Resumo tecnico:" and any(line.strip() for line in lines)
            ),
            None,
        )
        highlight_lines = cls._build_highlight_lines_from_summary(
            generated_summary or [],
            fallback_lines=fallback_map.get("Destaques tecnicos:", []),
        )

        repaired_sections: List[tuple[str, List[str]]] = []
        for heading in DESCRIPTION_SECTION_TITLES:
            if heading == "Resumo tecnico:" and generated_summary:
                repaired_sections.append((heading, generated_summary))
                continue
            if heading == "Destaques tecnicos:" and highlight_lines:
                repaired_sections.append((heading, highlight_lines))
                continue
            if heading in fallback_map:
                repaired_sections.append((heading, fallback_map[heading]))

        repaired = cls._render_description_sections(
            generated_preamble or fallback_preamble,
            repaired_sections,
        )
        return cls._finalize_structured_description(
            repaired,
            product_name=product_name,
            fallback_text=fallback_text,
        )

    @classmethod
    def _replace_invalid_summary_section(
        cls,
        description: str,
        *,
        product_name: str,
        fallback_text: str,
    ) -> str:
        """Replace the generated summary section when it drifts away from the product identity."""
        fallback_preamble, fallback_sections = cls._parse_description_sections(fallback_text)
        fallback_summary = next((lines for heading, lines in fallback_sections if heading == "Resumo tecnico:"), None)
        if not fallback_summary:
            return description

        preamble, sections = cls._parse_description_sections(description)
        basic_service = cls._get_basic_content_service()

        replaced = False
        for index, (heading, lines) in enumerate(sections):
            if heading != "Resumo tecnico:":
                continue
            summary_text = "\n".join(line.strip() for line in lines if line.strip())
            generated_summary_is_weak = cls._summary_text_is_low_value(summary_text, product_name=product_name)
            generated_summary_is_foreign = cls._looks_like_english_generated_fragment(summary_text)
            fallback_summary_text = "\n".join(line.strip() for line in fallback_summary if line.strip())
            fallback_summary_is_weak = cls._summary_text_is_low_value(
                fallback_summary_text,
                product_name=product_name,
            )
            if (
                basic_service._summary_preserves_primary_identity(summary_text, primary_title=product_name)
                and not generated_summary_is_weak
                and not generated_summary_is_foreign
            ):
                return description
            if (generated_summary_is_weak or generated_summary_is_foreign) and fallback_summary_is_weak:
                return description
            sections[index] = (heading, list(fallback_summary))
            replaced = True
            break

        if not replaced:
            if fallback_preamble and not preamble:
                preamble = list(fallback_preamble)
            sections.insert(0, ("Resumo tecnico:", list(fallback_summary)))

        return cls._render_description_sections(preamble, sections)

    @classmethod
    def _summary_text_is_low_value(
        cls,
        summary_text: Any,
        *,
        product_name: Any,
    ) -> bool:
        """Detect placeholder-like summaries that preserve identity but add little factual value."""
        normalized_summary = cls._normalize_prompt_line(summary_text)
        normalized_product_name = cls._normalize_prompt_line(product_name)
        if not normalized_summary:
            return True

        folded_summary = cls._fold_identity_text(normalized_summary)
        folded_product_name = cls._fold_identity_text(normalized_product_name)
        if folded_product_name and folded_summary == folded_product_name:
            return True
        return bool(LOW_VALUE_SUMMARY_PATTERN.search(folded_summary))

    @classmethod
    def _build_highlight_lines_from_summary(
        cls,
        summary_lines: List[str],
        *,
        fallback_lines: Optional[List[str]] = None,
    ) -> List[str]:
        """Derive concise technical highlight bullets from the generated summary when possible."""
        highlights: List[str] = []
        seen: set[str] = set()
        for raw_line in summary_lines:
            normalized_line = cls._normalize_prompt_line(raw_line)
            if not normalized_line:
                continue
            fragments = re.split(r"(?<=[.!?])\s+", normalized_line)
            for fragment in fragments:
                clean_fragment = cls._normalize_prompt_line(fragment).rstrip(".")
                if not clean_fragment or clean_fragment.endswith(":"):
                    continue
                bullet = f"- {clean_fragment}."
                folded_bullet = cls._fold_identity_text(bullet)
                if folded_bullet in seen:
                    continue
                seen.add(folded_bullet)
                highlights.append(bullet)
                if len(highlights) >= 2:
                    return highlights
        if highlights:
            return highlights
        return [line for line in (fallback_lines or []) if cls._normalize_prompt_line(line)]

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
        prompt_context = IAGenerationRuntime._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=120,
        )
        desired_count = max(1, int(num_titulos or 1))
        titles = IAGenerationRuntime._select_final_title_candidates(
            prompt_context=prompt_context,
            llm_titles=[],
            desired_count=desired_count,
        )
        if titles:
            return titles
        source_title = IAGenerationRuntime._normalize_prompt_line(prompt_context.get("source_title"))
        return [source_title or "Produto"]

    @staticmethod
    def _build_local_description(db_produto: Any, *, tamanho_palavras: int) -> str:
        """Build deterministic fallback description when no IA key is configured."""
        prompt_context = IAGenerationRuntime._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=max(120, int(tamanho_palavras or 120)),
        )
        return IAGenerationRuntime._finalize_structured_description(
            prompt_context.get("fallback_description", ""),
            product_name=prompt_context.get("source_title"),
            fallback_text=prompt_context.get("fallback_description", ""),
        )

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
        prompt_context = self._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=120,
        )

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
                "content": self._build_domain_guardrail_text(
                    prompt_context=prompt_context,
                    target="title",
                )
                + self._render_prompt(
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
                    context=prompt_context,
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
            source_title=prompt_context.get("source_title"),
            source_aliases=prompt_context.get("source_aliases"),
            desired_count=max(1, int(num_titulos or 1)),
        )
        titulos_list = self._select_final_title_candidates(
            prompt_context=prompt_context,
            llm_titles=titulos_list,
            desired_count=max(1, int(num_titulos or 1)),
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
        provider_runtime = getattr(ai_provider_workflow, "_runtime", None)
        provider_name = (
            provider_runtime.get_openai_provider_name()
            if provider_runtime is not None
            else "openai"
        )
        requested_word_target = max(40, int(tamanho_palavras or 40))
        effective_word_target = requested_word_target
        minimum_prompt_words = 120
        max_tokens = max(60, requested_word_target) + 100
        if provider_name == "lm_studio" and provider_runtime is not None:
            effective_word_target = provider_runtime.get_lm_studio_description_word_target(
                requested_word_target
            )
            minimum_prompt_words = 40
            max_tokens = provider_runtime.get_lm_studio_description_max_tokens(
                effective_word_target
            )
            logger.info(
                "Aplicando perfil compacto de descricao para LM Studio: palavras=%s, max_tokens=%s.",
                effective_word_target,
                max_tokens,
            )
        prompt_context = self._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=effective_word_target,
            minimum_tamanho_palavras=minimum_prompt_words,
        )
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
                "content": self._build_domain_guardrail_text(
                    prompt_context=prompt_context,
                    target="description",
                )
                + self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM,
                    context={"tamanho_palavras": effective_word_target},
                ),
            },
            {
                "role": "user",
                "content": self._render_prompt(
                    db=db,
                    nome=PromptTemplateName.IA_OPENAI_DESCRIPTION_USER,
                    context=prompt_context,
                ),
            },
        ]

        try:
            descricao = await ai_provider_workflow.call_openai_api(
                prompt_messages=prompt_messages,
                api_key=api_key,
                max_tokens=max_tokens,
            )
        except HTTPException as exc:
            if provider_name == "lm_studio" and exc.status_code == status.HTTP_503_SERVICE_UNAVAILABLE:
                logger.warning(
                    "LM Studio excedeu o tempo limite para descricao do produto %s; aplicando fallback local.",
                    produto_id,
                )
                self._registrar_uso_fallback(
                    db=db,
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.CRIACAO_DESCRICAO_PRODUTO,
                    provider_name="lm_studio",
                    details="Timeout/rede do LM Studio; fallback local aplicado para descricao.",
                )
                return self._build_local_description(
                    db_produto,
                    tamanho_palavras=effective_word_target,
                )
            raise
        descricao = self._finalize_structured_description(
            descricao,
            product_name=prompt_context.get("source_title"),
            fallback_text=prompt_context.get("fallback_description", ""),
        )
        if provider_name == "lm_studio":
            descricao = self._compose_summary_first_description(
                descricao,
                product_name=prompt_context.get("source_title"),
                fallback_text=prompt_context.get("fallback_description", ""),
            )
        descricao = self._repair_truncated_description_with_fallback(
            descricao,
            product_name=prompt_context.get("source_title"),
            fallback_text=prompt_context.get("fallback_description", ""),
        )
        if (
            not isinstance(descricao, str)
            or not descricao.strip()
            or descricao.count("\n") < 5
            or "..." in descricao
            or len(descricao.split()) < 35
        ):
            descricao = self._finalize_structured_description(
                prompt_context.get("fallback_description", ""),
                product_name=prompt_context.get("source_title"),
                fallback_text=prompt_context.get("fallback_description", ""),
            )

        if provider_runtime is not None:
            modelo_utilizado = await provider_runtime.resolve_openai_model(
                api_key=api_key,
                requested_model=OPENAI_DEFAULT_MODEL,
            )
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
        prompt_context = self._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=120,
        )

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

        prompt_text = self._build_domain_guardrail_text(
            prompt_context=prompt_context,
            target="title",
        ) + self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_TITLE_USER,
            context={
                **prompt_context,
                "num_titulos": num_titulos,
            },
        )
        resultado = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=150 * max(1, int(num_titulos or 1)),
        )
        titulos_list = self._sanitize_title_candidates(
            resultado,
            source_title=prompt_context.get("source_title"),
            source_aliases=prompt_context.get("source_aliases"),
            desired_count=max(1, int(num_titulos or 1)),
        )
        titulos_list = self._select_final_title_candidates(
            prompt_context=prompt_context,
            llm_titles=titulos_list,
            desired_count=max(1, int(num_titulos or 1)),
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
        prompt_context = self._build_generation_prompt_context(
            db_produto=db_produto,
            tamanho_palavras=max(120, int(tamanho_palavras or 120)),
        )

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

        prompt_text = self._build_domain_guardrail_text(
            prompt_context=prompt_context,
            target="description",
        ) + self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_DESCRIPTION_USER,
            context={
                **prompt_context,
                "tamanho_palavras": tamanho_palavras,
            },
        )
        descricao = await ai_provider_workflow.call_gemini_api(
            prompt_text=prompt_text,
            api_key=api_key,
            max_tokens=max(60, int(tamanho_palavras or 60)) + 100,
        )
        descricao = self._finalize_structured_description(
            descricao,
            product_name=prompt_context.get("source_title"),
            fallback_text=prompt_context.get("fallback_description", ""),
        )
        if (
            not isinstance(descricao, str)
            or not descricao.strip()
            or descricao.count("\n") < 5
            or "..." in descricao
            or len(descricao.split()) < 35
        ):
            descricao = self._finalize_structured_description(
                prompt_context.get("fallback_description", ""),
                product_name=prompt_context.get("source_title"),
                fallback_text=prompt_context.get("fallback_description", ""),
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
        atributos_relevantes: list[Any] = []
        if db_produto.product_type and db_produto.product_type.attribute_templates:
            atributos_relevantes = [
                attr
                for attr in db_produto.product_type.attribute_templates
                if getattr(attr, "attribute_key", None) and getattr(attr, "collect_in_ai", True) is not False
            ]
            chaves_para_sugerir = [attr.attribute_key for attr in atributos_relevantes]
        
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
        contexto_atributos = "\n".join(
            [
                f"- {attr.attribute_key}: {getattr(attr, 'description', None) or getattr(attr, 'label', None) or attr.attribute_key}"
                for attr in atributos_relevantes
            ]
        )
        prompt_final = self._render_prompt(
            db=db,
            nome=PromptTemplateName.IA_GEMINI_ATTRIBUTE_SUGGESTION_USER,
            context={
                "contexto": contexto,
                "contexto_atributos": contexto_atributos,
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




