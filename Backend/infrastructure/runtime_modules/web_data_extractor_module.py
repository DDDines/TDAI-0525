# Backend/infrastructure/runtime_modules/web_data_extractor_module.py
"""Document web data extractor module module responsibilities and runtime integration points."""

import asyncio
import sys
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import trafilatura # type: ignore
import extruct # type: ignore
import json
import re
from typing import List, Dict, Optional, Any, Tuple, Callable
from fastapi import HTTPException
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from sqlalchemy.orm import Session # Importar Session para type hinting, se necessário
from datetime import datetime, timezone
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)


try:
    from googleapiclient.discovery import build # type: ignore
    GOOGLE_API_CLIENT_INSTALLED = True
except ImportError:
    GOOGLE_API_CLIENT_INSTALLED = False
    logger.warning(
        "Biblioteca google-api-python-client não instalada ou com problemas. Busca no Google pode não funcionar."
    )

# Ajustando as importações para serem absolutas a partir da raiz do projeto (Backend)
# Assumindo que 'Backend' está no sys.path ou é o diretório de trabalho.
from Backend.core.config import settings
from Backend import models
from Backend.infrastructure.runtime_modules.ia_generation_module import (
    AiProviderWorkflow,
)
_TRACKING_QUERY_HINTS = (
    "ad_domain=",
    "ad_provider=",
    "click_metadata=",
    "msclkid=",
    "vqd=",
    "ig=",
    "cid=",
    "utm_",
)
_REDIRECT_QUERY_KEYS = (
    "uddg",
    "u",
    "u3",
    "url",
    "target",
    "redirect",
    "redirect_url",
    "dest",
    "destination",
)
_LOW_RELEVANCE_HOST_HINTS = (
    "duckduckgo.com",
    "bing.com",
    "google.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "linkedin.com",
    "pinterest.com",
    "whatsapp.com",
)
_PREFERRED_PRODUCT_HOST_HINTS = (
    "mercadolivre.",
    "amazon.",
    "shopee.",
    "magazineluiza.",
    "casasbahia.",
    "jocar.",
    "dipecarr.",
    "dana.",
    "jacto",
    "minner.",
    "mundodocaminhao.",
    "essentra",
)

# --- Google Search Service ---
class WebSearchEngineRuntime:
    """Runtime OO para buscas web (cache + scoring + fallback publico/CSE)."""

    def __init__(self) -> None:
        """Initialize injected dependencies and runtime configuration for Web Search Engine Runtime."""
        self._search_cache: Dict[str, Tuple[float, List[str]]] = {}
        self._search_cache_ttl_seconds = 600.0
        self._search_cache_max_entries = 300
        self._search_cache_lock: Optional[asyncio.Lock] = None
        self._search_semaphore: Optional[asyncio.Semaphore] = None

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return True

    def get_search_cache_lock(self) -> asyncio.Lock:
        """Retrieve search cache lock using the current service dependencies."""
        if self._search_cache_lock is None:
            self._search_cache_lock = asyncio.Lock()
        return self._search_cache_lock

    def get_search_semaphore(self) -> asyncio.Semaphore:
        """Retrieve search semaphore using the current service dependencies."""
        if self._search_semaphore is None:
            limit = int(getattr(settings, "WEB_SEARCH_CONCURRENCY", 3) or 3)
            self._search_semaphore = asyncio.Semaphore(max(1, limit))
        return self._search_semaphore

    async def search_cache_get(self, query_key: str) -> Optional[List[str]]:
        """Execute search cache get as part of this module workflow."""
        lock = self.get_search_cache_lock()
        now = time.monotonic()
        async with lock:
            cached = self._search_cache.get(query_key)
            if not cached:
                return None
            ts, urls = cached
            if (now - ts) > self._search_cache_ttl_seconds:
                self._search_cache.pop(query_key, None)
                return None
            return list(urls)

    async def search_cache_set(self, query_key: str, urls: List[str]) -> None:
        """Execute search cache set as part of this module workflow."""
        lock = self.get_search_cache_lock()
        now = time.monotonic()
        async with lock:
            if len(self._search_cache) >= self._search_cache_max_entries:
                oldest_key = min(self._search_cache.items(), key=lambda item: item[1][0])[0]
                self._search_cache.pop(oldest_key, None)
            self._search_cache[query_key] = (now, list(urls))

    def score_url_publica(self, url: str) -> int:
        """Execute score url publica as part of this module workflow."""
        parsed = urlparse(url)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        score = 0

        if any(hint in host for hint in _PREFERRED_PRODUCT_HOST_HINTS):
            score += 24
        if any(seg in path for seg in ("/produto", "/product", "/peca", "/autopeca", "/p/")):
            score += 10
        if path.endswith(".pdf"):
            score -= 8
        if any(h in host for h in _LOW_RELEVANCE_HOST_HINTS):
            score -= 12
        if any(hint in query for hint in _TRACKING_QUERY_HINTS):
            score -= 25
        if len(query) > 280:
            score -= 8
        return score

    def extract_redirect_destination(self, query: str) -> Optional[str]:
        """Execute extract redirect destination as part of this module workflow."""
        if not query:
            return None
        qs = parse_qs(query or "")
        for key in _REDIRECT_QUERY_KEYS:
            values = qs.get(key) or []
            for raw_value in values:
                candidate = unquote(str(raw_value or "").strip())
                if candidate.startswith(("http://", "https://")):
                    return candidate
        return None

    def unwrap_redirect_url(self, url: str, max_hops: int = 3) -> str:
        """Execute unwrap redirect url as part of this module workflow."""
        current = str(url or "").strip()
        for _ in range(max(1, max_hops)):
            parsed = urlparse(current)
            destination = self.extract_redirect_destination(parsed.query or "")
            if not destination or destination == current:
                break
            current = destination.strip()
        return current

    def url_deve_ser_ignorada_antes_da_coleta(self, url: str) -> bool:
        """Evita coletar links de tracking, redirecionamento e paginas de busca."""
        parsed = urlparse(str(url or "").strip())
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        host_no_www = host[4:] if host.startswith("www.") else host

        if parsed.scheme not in {"http", "https"}:
            return True
        if not host:
            return True

        if "duckduckgo.com" in host_no_www and (
            path.startswith("/y.js") or path.startswith("/redirect") or path.startswith("/l/")
        ):
            return True
        if "bing.com" in host_no_www and (path.startswith("/aclick") or path.startswith("/ck/")):
            return True
        if "bing.com" in host_no_www and (
            path.startswith("/search") or path.startswith("/images/search")
        ):
            return True
        if ("google.com" in host_no_www or host_no_www.endswith(".google")) and (
            path.startswith("/search") or path.startswith("/imgres") or path.startswith("/url")
        ):
            return True

        if any(hint in query for hint in _TRACKING_QUERY_HINTS):
            return True
        if len(query) > 500:
            return True
        if self.extract_redirect_destination(query) and any(
            hint in host_no_www for hint in _LOW_RELEVANCE_HOST_HINTS
        ):
            return True

        if path.endswith(".pdf"):
            return True

        return False

    def normalizar_url_busca(self, candidata: str, base_url: str) -> Optional[str]:
        """Execute normalizar url busca as part of this module workflow."""
        if not candidata:
            return None
        url_final = str(candidata).strip()
        if not url_final:
            return None
        if url_final.startswith("/"):
            url_final = urljoin(base_url, url_final)

        raw_parsed = urlparse(url_final)
        raw_host = (raw_parsed.netloc or "").lower()
        raw_host_no_www = raw_host[4:] if raw_host.startswith("www.") else raw_host
        raw_path = (raw_parsed.path or "").lower()
        raw_query = (raw_parsed.query or "").lower()

        if "duckduckgo.com" in raw_host_no_www and (
            raw_path.startswith("/y.js") or raw_path.startswith("/redirect")
        ):
            return None
        if "bing.com" in raw_host_no_www and raw_path.startswith("/aclick"):
            return None
        if ("google.com" in raw_host_no_www or raw_host_no_www.endswith(".google")) and (
            raw_path.startswith("/search")
            or raw_path.startswith("/imgres")
            or raw_path.startswith("/url")
        ):
            return None
        if any(hint in raw_query for hint in _TRACKING_QUERY_HINTS) and any(
            hint in raw_host_no_www for hint in _LOW_RELEVANCE_HOST_HINTS
        ):
            return None

        url_final = self.unwrap_redirect_url(url_final, max_hops=4)

        parsed = urlparse(url_final)
        host = (parsed.netloc or "").lower()
        path = (parsed.path or "").lower()
        query = (parsed.query or "").lower()
        host_no_www = host[4:] if host.startswith("www.") else host

        if "duckduckgo.com" in host_no_www:
            qs = parse_qs(parsed.query or "")
            destino = None
            for key in ("uddg", "u", "u3"):
                vals = qs.get(key) or []
                if vals:
                    destino = unquote(vals[0])
                    if destino:
                        break

            if destino:
                url_final = destino.strip()
                parsed = urlparse(url_final)
                host = (parsed.netloc or "").lower()
                host_no_www = host[4:] if host.startswith("www.") else host
            else:
                return None

            if "duckduckgo.com" in host_no_www:
                return None

        if "bing.com" in host_no_www and parsed.path.lower().startswith("/aclick"):
            return None
        if "bing.com" in host_no_www and (path.startswith("/search") or path.startswith("/images/search")):
            return None
        if ("google.com" in host_no_www or host_no_www.endswith(".google")) and (
            path.startswith("/search") or path.startswith("/imgres")
        ):
            return None
        if path in {"/y.js", "/redirect"}:
            return None
        if any(hint in query for hint in _TRACKING_QUERY_HINTS):
            return None
        if len(query) > 500:
            return None

        if parsed.scheme not in {"http", "https"}:
            return None
        if not parsed.netloc:
            return None
        if self.url_deve_ser_ignorada_antes_da_coleta(url_final):
            return None
        return url_final

    def buscar_urls_publicas_sync(self, query: str, num_results: int = 3) -> List[str]:
        """Execute buscar urls publicas sync as part of this module workflow."""
        if not query:
            return []

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        }
        endpoints = [
            f"https://duckduckgo.com/html/?q={quote_plus(query)}",
            f"https://html.duckduckgo.com/html/?q={quote_plus(query)}",
            f"https://www.bing.com/search?q={quote_plus(query)}",
        ]

        urls: List[str] = []
        vistos: set[str] = set()

        for endpoint in endpoints:
            try:
                req = Request(endpoint, headers=headers, method="GET")
                with urlopen(req, timeout=8) as resp:
                    content = resp.read().decode("utf-8", errors="ignore")
            except Exception as search_err:
                logger.warning(
                    "Busca publica falhou em %s (query='%s'): %s",
                    endpoint,
                    query,
                    search_err,
                )
                continue

            soup = BeautifulSoup(content, "html.parser")
            anchors = soup.select(
                "a.result__a, .result a[href], a[href*='uddg='], li.b_algo h2 a, h2 a[href]"
            )
            for anchor in anchors:
                href = anchor.get("href")
                url_norm = self.normalizar_url_busca(href or "", endpoint)
                if not url_norm or url_norm in vistos:
                    continue
                vistos.add(url_norm)
                urls.append(url_norm)
                if len(urls) >= max(1, num_results):
                    break
            if len(urls) >= max(1, num_results):
                break

        if len(urls) < max(1, num_results):
            proxy_endpoint = f"https://r.jina.ai/http://duckduckgo.com/html/?q={quote_plus(query)}"
            try:
                req = Request(proxy_endpoint, headers=headers, method="GET")
                with urlopen(req, timeout=10) as resp:
                    proxy_text = resp.read().decode("utf-8", errors="ignore")

                for href in re.findall(r"\((https?://[^)]+)\)", proxy_text):
                    url_norm = self.normalizar_url_busca(href, proxy_endpoint)
                    if not url_norm or url_norm in vistos:
                        continue
                    vistos.add(url_norm)
                    urls.append(url_norm)
                    if len(urls) >= max(1, num_results):
                        break
            except Exception as proxy_err:
                logger.warning(
                    "Fallback via r.jina.ai falhou (query='%s'): %s",
                    query,
                    proxy_err,
                )
        deduped_urls = list(dict.fromkeys(urls))
        scored_urls = sorted(deduped_urls, key=self.score_url_publica, reverse=True)
        filtered_urls = [u for u in scored_urls if self.score_url_publica(u) > -20]
        return (
            filtered_urls[: max(1, num_results)]
            if filtered_urls
            else scored_urls[: max(1, num_results)]
        )

    async def buscar_urls_publicas_async(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls publicas async as part of this module workflow."""
        return await asyncio.to_thread(self.buscar_urls_publicas_sync, query, num_results)

    def _executar_busca_google_cse(self, query_limpa: str, limite: int) -> List[str]:
        """Execute executar busca google cse as part of this module workflow."""
        service = build(
            "customsearch",
            "v1",
            developerKey=settings.GOOGLE_CSE_API_KEY,
            cache_discovery=False,
        )
        res = (
            service.cse()
            .list(q=query_limpa, cx=settings.GOOGLE_CSE_ID, num=limite)
            .execute()
        )
        return [item["link"] for item in res.get("items", []) if "link" in item]

    async def buscar_urls_google_async(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls google async as part of this module workflow."""
        query_limpa = str(query or "").strip()
        if not query_limpa:
            return []
        limite = max(1, num_results)
        cache_key = query_limpa.lower()

        cached_urls = await self.search_cache_get(cache_key)
        if cached_urls is not None:
            logger.info(
                "Busca web (cache) retornou %s URL(s) para query '%s'.",
                len(cached_urls),
                query_limpa,
            )
            return cached_urls[:limite]

        urls_encontradas: List[str] = []
        google_disponivel = (
            GOOGLE_API_CLIENT_INSTALLED
            and bool(settings.GOOGLE_CSE_API_KEY)
            and bool(settings.GOOGLE_CSE_ID)
        )

        async with self.get_search_semaphore():
            if google_disponivel:
                try:
                    urls_encontradas = await asyncio.to_thread(
                        self._executar_busca_google_cse,
                        query_limpa,
                        limite,
                    )
                    if urls_encontradas:
                        urls_encontradas = [
                            self.normalizar_url_busca(url, "https://www.google.com")
                            for url in urls_encontradas
                        ]
                        urls_encontradas = [url for url in urls_encontradas if url]
                        logger.info(
                            "Busca Google CSE retornou %s URL(s) para query '%s'.",
                            len(urls_encontradas),
                            query_limpa,
                        )
                        urls_unicas = list(dict.fromkeys(urls_encontradas))[:limite]
                        await self.search_cache_set(cache_key, urls_unicas)
                        return urls_unicas
                    logger.warning(
                        "Google CSE nao retornou URLs para query '%s'. Tentando fallback publico.",
                        query_limpa,
                    )
                except Exception as e:
                    logger.error("Erro ao buscar no Google (query: '%s'): %s", query_limpa, e)
                    logger.info("Tentando fallback de busca publica sem API key.")
            else:
                motivos_google_indisponivel: List[str] = []
                if not GOOGLE_API_CLIENT_INSTALLED:
                    motivos_google_indisponivel.append("biblioteca ausente")
                if not settings.GOOGLE_CSE_API_KEY:
                    motivos_google_indisponivel.append("GOOGLE_CSE_API_KEY ausente")
                if not settings.GOOGLE_CSE_ID:
                    motivos_google_indisponivel.append("GOOGLE_CSE_ID ausente")
                motivos_txt = (
                    ", ".join(motivos_google_indisponivel)
                    if motivos_google_indisponivel
                    else "configuracao ausente"
                )
                logger.warning(
                    "Google CSE indisponivel (%s). Usando fallback de busca publica.",
                    motivos_txt,
                )

            urls_encontradas = await self.buscar_urls_publicas_async(
                query=query_limpa,
                num_results=limite,
            )
            urls_unicas = list(dict.fromkeys(urls_encontradas))[:limite]
            if urls_unicas:
                logger.info(
                    "Fallback de busca publica retornou %s URL(s) para query '%s'.",
                    len(urls_unicas),
                    query_limpa,
                )
            else:
                logger.warning(
                    "Fallback de busca publica nao retornou URLs para query '%s'.",
                    query_limpa,
                )
            await self.search_cache_set(cache_key, urls_unicas)
            return urls_unicas


class WebContentFetchEngineRuntime:
    """Runtime OO para coleta de conte?do HTML (Playwright + fallback HTTP)."""

    def __init__(self, search_runtime: WebSearchEngineRuntime) -> None:
        """Initialize injected dependencies and runtime configuration for Web Content Fetch Engine Runtime."""
        self._search_runtime = search_runtime
        self._playwright_chromium_indisponivel = False

    def is_playwright_chromium_indisponivel(self) -> bool:
        """Execute is playwright chromium indisponivel as part of this module workflow."""
        return self._playwright_chromium_indisponivel

    def set_playwright_chromium_indisponivel(self, value: bool) -> None:
        """Execute set playwright chromium indisponivel as part of this module workflow."""
        self._playwright_chromium_indisponivel = bool(value)

    def coletar_conteudo_pagina_http_sync(
        self,
        url: str,
        timeout: int = 20,
    ) -> Optional[str]:
        """Coletar conteudo pagina http sync."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
            )
        }
        req = Request(url, headers=headers, method="GET")
        with urlopen(req, timeout=timeout) as resp:
            content_type = (resp.headers.get("Content-Type") or "").lower()
            raw = resp.read()

        if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
            return None
        return raw.decode("utf-8", errors="ignore")

    async def coletar_conteudo_pagina_http(
        self,
        url: str,
        timeout: int = 20,
    ) -> Optional[str]:
        """Execute coletar conteudo pagina http as part of this module workflow."""
        try:
            return await asyncio.to_thread(
                self.coletar_conteudo_pagina_http_sync,
                url,
                timeout,
            )
        except Exception as e:
            logger.warning("Falha ao coletar conte?do HTTP direto para %s: %s", url, e)
            return None

    async def coletar_conteudo_pagina_playwright_core(
        self,
        url: str,
    ) -> Optional[str]:
        """Coletar conteudo pagina playwright core."""
        browser = None
        async with async_playwright() as p_instance:
            try:
                browser = await p_instance.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
                    ),
                    java_script_enabled=True,
                    ignore_https_errors=True,
                )
                page = await context.new_page()
                await page.goto(url, timeout=30000, wait_until="networkidle")
                return await page.content()
            finally:
                if browser:
                    await browser.close()

    def coletar_conteudo_playwright_em_thread_sync(
        self,
        url: str,
    ) -> Optional[str]:
        """Coletar conteudo playwright em thread sync."""
        loop = None
        try:
            if sys.platform.startswith("win") and hasattr(
                asyncio,
                "WindowsProactorEventLoopPolicy",
            ):
                loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()  # type: ignore[attr-defined]
            else:
                loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop.run_until_complete(self.coletar_conteudo_pagina_playwright_core(url))
        finally:
            if loop is not None:
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass
                loop.close()
            asyncio.set_event_loop(None)

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        if self._search_runtime.url_deve_ser_ignorada_antes_da_coleta(url):
            logger.info(
                "URL ignorada antes da coleta por baixa relevancia/tracking: %s",
                url,
            )
            return None
        if self._playwright_chromium_indisponivel:
            return await self.coletar_conteudo_pagina_http(url)

        loop_name = asyncio.get_running_loop().__class__.__name__.lower()
        if sys.platform.startswith("win") and "selector" in loop_name:
            logger.warning(
                "Loop asyncio sem suporte a subprocesso detectado (%s). Tentando Playwright em thread dedicada.",
                loop_name,
            )
            try:
                html_from_thread = await asyncio.to_thread(
                    self.coletar_conteudo_playwright_em_thread_sync,
                    url,
                )
                if html_from_thread:
                    logger.info(
                        "Playwright executado com sucesso via thread dedicada para %s.",
                        url,
                    )
                    return html_from_thread
            except PlaywrightTimeoutError:
                logger.error(
                    "Timeout ao carregar URL com Playwright (thread dedicada): %s",
                    url,
                )
            except Exception as e:
                erro_str = str(e)
                erro_curto = erro_str.splitlines()[0] if erro_str else "erro_desconhecido"
                if "Executable doesn't exist" in erro_str:
                    if not self._playwright_chromium_indisponivel:
                        logger.warning(
                            "Playwright Chromium indisponivel no ambiente. Usando fallback HTTP direto para proximas coletas."
                        )
                    self.set_playwright_chromium_indisponivel(True)
                    logger.warning(
                        "Falha Playwright (thread dedicada) para %s: %s",
                        url,
                        erro_curto,
                    )
                else:
                    logger.warning(
                        "Falha Playwright via thread dedicada para %s: %s. Caindo para HTTP direto.",
                        url,
                        erro_curto,
                    )
            return await self.coletar_conteudo_pagina_http(url)

        try:
            return await self.coletar_conteudo_pagina_playwright_core(url)
        except PlaywrightTimeoutError:
            logger.error("Timeout ao carregar URL com Playwright: %s", url)
            html_content = await self.coletar_conteudo_pagina_http(url)
            if html_content:
                logger.info(
                    "Fallback HTTP direto usado ap?s timeout do Playwright para %s.",
                    url,
                )
            return html_content
        except Exception as e:
            erro_str = str(e)
            erro_curto = erro_str.splitlines()[0] if erro_str else "erro_desconhecido"
            if "Executable doesn't exist" in erro_str:
                if not self._playwright_chromium_indisponivel:
                    logger.warning(
                        "Playwright Chromium indisponivel no ambiente. Usando fallback HTTP direto para proximas coletas."
                    )
                self.set_playwright_chromium_indisponivel(True)
                logger.warning("Falha Playwright para %s: %s", url, erro_curto)
            else:
                import traceback

                logger.error(
                    "Erro ao coletar conte?do com Playwright para %s: %s\n%s",
                    url,
                    e,
                    traceback.format_exc(),
                )
            html_content = await self.coletar_conteudo_pagina_http(url)
            if html_content:
                logger.info(
                    "Fallback HTTP direto usado ap?s falha do Playwright para %s.",
                    url,
                )
            return html_content
        except NotImplementedError:
            logger.warning(
                "Playwright indisponivel neste loop asyncio. Usando fallback HTTP direto para %s.",
                url,
            )
            return await self.coletar_conteudo_pagina_http(url)


class WebSearchWorkflow:
    """Workflow OO para estrategias de busca web."""

    def __init__(self, runtime: Optional["WebSearchRuntime"] = None) -> None:
        """Initialize injected dependencies and runtime configuration for Web Search Workflow."""
        self._runtime = runtime or WebSearchRuntime()

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return self._runtime.busca_publica_disponivel()

    async def buscar_urls_publicas(self, query: str, num_results: int = 3) -> List[str]:
        """Execute buscar urls publicas as part of this module workflow."""
        return await self._runtime.buscar_urls_publicas_async(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(self, query: str, num_results: int = 3) -> List[str]:
        """Execute buscar urls google as part of this module workflow."""
        return await self._runtime.buscar_urls_google_async(
            query=query,
            num_results=num_results,
        )

    def url_deve_ser_ignorada_antes_da_coleta(self, url: str) -> bool:
        """Url deve ser ignorada antes da coleta."""
        return self._runtime.url_deve_ser_ignorada_antes_da_coleta(url)

    def normalizar_url_busca(self, candidata: str, base_url: str) -> Optional[str]:
        """Execute normalizar url busca as part of this module workflow."""
        return self._runtime.normalizar_url_busca(
            candidata=candidata,
            base_url=base_url,
        )


class WebContentCollectionWorkflow:
    """Workflow OO para coleta de conteudo de pagina."""

    def __init__(
        self, runtime: Optional["WebContentCollectionRuntime"] = None
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Content Collection Workflow."""
        self._runtime = runtime or WebContentCollectionRuntime()

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        return await self._runtime.coletar_conteudo_pagina_playwright(url)


class WebSearchRuntime:
    """Runtime OO para buscas web (Google CSE + fallback público)."""

    def __init__(
        self,
        engine_runtime: Optional[WebSearchEngineRuntime] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Search Runtime."""
        self._engine_runtime = engine_runtime or WebSearchEngineRuntime()

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return self._engine_runtime.busca_publica_disponivel()

    async def buscar_urls_publicas_async(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls publicas async as part of this module workflow."""
        return await self._engine_runtime.buscar_urls_publicas_async(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google_async(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls google async as part of this module workflow."""
        return await self._engine_runtime.buscar_urls_google_async(
            query=query,
            num_results=num_results,
        )

    def url_deve_ser_ignorada_antes_da_coleta(self, url: str) -> bool:
        """Url deve ser ignorada antes da coleta."""
        return self._engine_runtime.url_deve_ser_ignorada_antes_da_coleta(url)

    def normalizar_url_busca(self, candidata: str, base_url: str) -> Optional[str]:
        """Execute normalizar url busca as part of this module workflow."""
        return self._engine_runtime.normalizar_url_busca(
            candidata=candidata,
            base_url=base_url,
        )


class WebContentCollectionRuntime:
    """Runtime OO para coleta de conteúdo de página."""

    def __init__(
        self,
        engine_runtime: Optional[WebContentFetchEngineRuntime] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Content Collection Runtime."""
        self._engine_runtime = engine_runtime or WebContentFetchEngineRuntime(
            search_runtime=WebSearchEngineRuntime()
        )

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        return await self._engine_runtime.coletar_conteudo_pagina_playwright(
            url
        )


# --- Text Extraction Service ---
class MetadataExtractionRuntime:
    """Runtime OO para extracao de texto e metadados estruturados."""

    def extrair_texto_principal_com_trafilatura(self, html_content: str) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        if not html_content:
            return None
        return trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=True,
            output_format="text",
            favor_precision=False,
            include_formatting=False,
        )

    def limpar_valor_metadado(self, valor: Any) -> Optional[Any]:
        """Execute limpar valor metadado as part of this module workflow."""
        if valor is None:
            return None
        if isinstance(valor, str):
            texto = valor.strip()
            texto = re.sub(r"\s+", " ", texto)
            return texto if texto else None
        if isinstance(valor, list):
            lista_limpa = [self.limpar_valor_metadado(item) for item in valor]
            return [item for item in lista_limpa if item is not None] or None
        return valor

    def _get_first_string(self, value: Any) -> Optional[str]:
        """Retrieve first string using the current service dependencies."""
        if isinstance(value, list):
            for item_val in value:
                cleaned = self.limpar_valor_metadado(item_val)
                if cleaned and isinstance(cleaned, str):
                    return cleaned
            return None
        cleaned_val = self.limpar_valor_metadado(value)
        return cleaned_val if isinstance(cleaned_val, str) else None

    def extrair_metadados_estruturados(self, html_content: str, url: str) -> Dict[str, Any]:
        """Execute extrair metadados estruturados as part of this module workflow."""
        if not html_content:
            return {}
        metadata_extraida: Dict[str, Any] = {}
        try:
            data = extruct.extract(
                html_content,
                base_url=url,
                syntaxes=["json-ld", "microdata", "opengraph"],
                uniform=True,
            )
            for syntax_type, items_list in data.items():
                if not items_list:
                    continue
                if syntax_type in {"json-ld", "microdata"}:
                    for item_data in items_list:
                        is_product_candidate = isinstance(item_data, dict) and (
                            "Product" in str(
                                item_data.get("@type", "") or item_data.get("type", "")
                            )
                            or syntax_type == "microdata"
                        )
                        if not is_product_candidate:
                            continue
                        data_to_store = (
                            item_data.get("properties", item_data)
                            if syntax_type == "microdata"
                            else item_data
                        )
                        metadata_extraida[f"{syntax_type}_product_candidate"] = data_to_store
                        break
                elif syntax_type == "opengraph":
                    metadata_extraida["opengraph"] = items_list[0] if items_list else None
        except Exception as e:
            logger.error("Erro ao extrair metadados estruturados de %s com extruct: %s", url, e)
        return metadata_extraida

    def normalizar_dados_de_metadados(self, metadata_bruta: Dict[str, Any]) -> Dict[str, Any]:
        """Execute normalizar dados de metadados as part of this module workflow."""
        dados_norm: Dict[str, Any] = {}
        produto_json_ld = metadata_bruta.get("json-ld_product_candidate")
        produto_microdata = metadata_bruta.get("microdata_product_candidate")
        opengraph_props_list = metadata_bruta.get("opengraph")
        opengraph = (
            opengraph_props_list[0]
            if isinstance(opengraph_props_list, list) and opengraph_props_list
            else (opengraph_props_list if isinstance(opengraph_props_list, dict) else {})
        )

        if produto_json_ld and isinstance(produto_json_ld, dict):
            dados_norm["nome"] = self._get_first_string(produto_json_ld.get("name"))
            dados_norm["descricao_curta"] = self._get_first_string(produto_json_ld.get("description"))
            img = produto_json_ld.get("image")
            if isinstance(img, dict):
                img = img.get("url") or img.get("@id")
            elif isinstance(img, list):
                img = self._get_first_string([i.get("url") if isinstance(i, dict) else i for i in img])
            dados_norm["imagem_url"] = self._get_first_string(img)

            marca_info = produto_json_ld.get("brand")
            if isinstance(marca_info, dict):
                dados_norm["marca"] = self._get_first_string(marca_info.get("name"))
            else:
                dados_norm["marca"] = self._get_first_string(marca_info)

            dados_norm["sku"] = self._get_first_string(
                produto_json_ld.get("sku") or produto_json_ld.get("mpn")
            )

            offers = produto_json_ld.get("offers")
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            if isinstance(offers, dict):
                dados_norm["preco"] = self._get_first_string(
                    offers.get("price") or offers.get("lowPrice") or offers.get("highPrice")
                )
                dados_norm["moeda_preco"] = self._get_first_string(offers.get("priceCurrency"))
                disponibilidade = self._get_first_string(offers.get("availability"))
                if disponibilidade and "schema.org" in disponibilidade:
                    dados_norm["disponibilidade"] = disponibilidade.split("/")[-1]
                else:
                    dados_norm["disponibilidade"] = disponibilidade

        if produto_microdata and isinstance(produto_microdata, dict):
            if not dados_norm.get("nome"):
                dados_norm["nome"] = self._get_first_string(produto_microdata.get("name"))
            if not dados_norm.get("descricao_curta"):
                dados_norm["descricao_curta"] = self._get_first_string(produto_microdata.get("description"))
            if not dados_norm.get("imagem_url"):
                dados_norm["imagem_url"] = self._get_first_string(produto_microdata.get("image"))
            if not dados_norm.get("marca"):
                dados_norm["marca"] = self._get_first_string(produto_microdata.get("brand"))
            if not dados_norm.get("sku"):
                dados_norm["sku"] = self._get_first_string(
                    produto_microdata.get("sku") or produto_microdata.get("mpn")
                )

        if opengraph and isinstance(opengraph, dict):
            if not dados_norm.get("nome"):
                dados_norm["nome"] = self._get_first_string(opengraph.get("og:title"))
            if not dados_norm.get("descricao_curta"):
                dados_norm["descricao_curta"] = self._get_first_string(opengraph.get("og:description"))
            if not dados_norm.get("imagem_url"):
                dados_norm["imagem_url"] = self._get_first_string(opengraph.get("og:image"))
            if not dados_norm.get("marca") and opengraph.get("og:type") == "product":
                dados_norm["marca"] = self._get_first_string(
                    opengraph.get("product:brand") or opengraph.get("og:site_name")
                )
            elif not dados_norm.get("marca"):
                dados_norm["marca"] = self._get_first_string(opengraph.get("og:site_name"))

        return {k: v for k, v in dados_norm.items() if v is not None and v != ""}


# --- LLM-based Data Extraction from Text ---
class WebLLMExtractionEngineRuntime:
    """Engine runtime OO para extração de dados de produto com LLM."""
    def __init__(
        self,
        ai_provider_workflow_factory: Optional[Callable[[], AiProviderWorkflow]] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web LLMExtraction Engine Runtime."""
        self._ai_provider_workflow_factory = (
            ai_provider_workflow_factory or (lambda: AiProviderWorkflow())
        )

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extrair dados produto com llm."""
        if not texto_pagina and not metadados_normalizados:
            logger.info("Nenhum texto de página nem metadados fornecidos para extração LLM.")
            return {"erro_llm": "Nenhum conteúdo para processar"}

        prompt_contexto_inicial = [
            f"Você é um assistente especialista em extrair informações detalhadas de produtos de e-commerce para o produto '{produto_nome_base}'.",
            "Seu objetivo é preencher um JSON com os campos solicitados da forma mais precisa possível, com base no contexto fornecido.",
        ]
        contexto_para_llm = ""
        if (
            metadados_normalizados
            and isinstance(metadados_normalizados, dict)
            and any(metadados_normalizados.values())
        ):
            contexto_para_llm += "Contexto de Metadados Estruturados (use como base, valide e complemente com o texto principal):\n"
            for k, v_item in metadados_normalizados.items():
                contexto_para_llm += f"- {k.replace('_', ' ')}: {str(v_item)[:200]}\n"
        if texto_pagina:
            contexto_para_llm += f'\nTexto Principal da Página (use para encontrar informações e complementar/corrigir metadados):\n"""\n{texto_pagina[:10000]}\n"""'

        if not contexto_para_llm.strip():
            logger.info(
                "Contexto insuficiente para LLM (metadados e texto da página vazios ou muito curtos)."
            )
            return {"erro_llm": "Contexto insuficiente para processar"}

        if not campos_desejados:
            campos_desejados = [
                "nome_base",
                "marca",
                "sku_original",
                "descricao_original",
                "preco_original",
                "imagem_url_original",
            ]

        campos_formatados_prompt = ",\n".join([f'    "{campo}": "..."' for campo in campos_desejados])

        prompt = (
            "\n".join(prompt_contexto_inicial)
            + "\n\nA partir do contexto e do texto da página fornecidos, extraia RIGOROSAMENTE os seguintes campos e retorne APENAS um objeto JSON válido com esta estrutura:\n"
            + f"{{\n{campos_formatados_prompt}\n}}\n"
            + "Se uma informação para um campo específico não for encontrada de forma clara e inequívoca, retorne null para esse campo. Não invente informações.\n"
            + "Para campos do tipo lista (ex: 'lista_caracteristicas_beneficios_bullets', 'palavras_chave_seo_relevantes_lista'), retorne uma lista de strings.\n"
            + "Para campos do tipo dicionário (ex: 'especificacoes_tecnicas_dict'), retorne um dicionário chave-valor.\n"
            + f"\nContexto e Texto para Análise:\n{contexto_para_llm}"
        )

        if user is not None:
            api_key_para_usar = user.chave_openai_pessoal or settings.OPENAI_API_KEY
        else:
            api_key_para_usar = settings.OPENAI_API_KEY
        if not api_key_para_usar:
            logger.warning(
                "Nenhuma chave API OpenAI disponível para extração de dados com LLM."
            )
            return {"erro_llm": "Chave API OpenAI não configurada"}

        json_str_resposta = ""
        try:
            prompt_messages = [
                {
                    "role": "system",
                    "content": "Sua tarefa é extrair informações de um texto e retorná-las em formato JSON conforme o schema solicitado. Seja preciso e não adicione campos extras.",
                },
                {"role": "user", "content": prompt},
            ]
            ai_provider_workflow = self._ai_provider_workflow_factory()
            json_str_resposta = await ai_provider_workflow.call_openai_api(
                prompt_messages=prompt_messages,
                api_key=api_key_para_usar,
                model="gpt-3.5-turbo-0125",
                max_tokens=2048,
                temperature=0.0,
            )

            match = re.search(r"\{.*\}", json_str_resposta, re.DOTALL)
            if match:
                json_str_limpo = match.group(0)
            else:
                json_str_limpo = json_str_resposta

            dados_extraidos_llm = json.loads(json_str_limpo)

            final_data = (
                metadados_normalizados.copy()
                if metadados_normalizados and isinstance(metadados_normalizados, dict)
                else {}
            )
            if isinstance(dados_extraidos_llm, dict):
                for key_llm, val_llm in dados_extraidos_llm.items():
                    if val_llm is not None or key_llm not in final_data:
                        final_data[key_llm] = val_llm
            return final_data
        except json.JSONDecodeError as json_e:
            logger.error(
                "Erro ao decodificar JSON da resposta da LLM: %s. Resposta bruta: %s",
                json_e,
                json_str_resposta,
            )
            return {"extracao_bruta_llm_com_erro_json": json_str_resposta, **(metadados_normalizados or {})}
        except ValueError as ve:
            logger.error("Erro na chamada da LLM para extração: %s", ve)
            return {"erro_llm": str(ve), **(metadados_normalizados or {})}
        except Exception as e:
            import traceback

            logger.error("Erro inesperado na extração com LLM: %s", traceback.format_exc())
            return {"erro_llm_inesperado": str(e), **(metadados_normalizados or {})}


# Função principal do serviço de extração, combinando as etapas
class WebExtractionEnrichmentWorkflow:
    """Workflow OO para extracao/enriquecimento de uma URL de produto."""

    def __init__(
        self,
        *,
        db: Session,
        url: str,
        produto: models.Produto,
        runtime: Optional["WebExtractionEnrichmentRuntime"] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Extraction Enrichment Workflow."""
        self.db = db
        self.url = url
        self.produto = produto
        self.log_enriquecimento: List[Dict[str, Any]] = []
        self._runtime = runtime or WebExtractionEnrichmentRuntime()

    def _add_log(
        self,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Execute add log as part of this module workflow."""
        entry = {
            "timestamp": self._runtime.now_iso(),
            "level": level,
            "message": message,
        }
        if details:
            entry["details"] = details
        self.log_enriquecimento.append(entry)

    def _persist_status(self, status: models.StatusEnriquecimentoEnum) -> None:
        """Execute persist status as part of this module workflow."""
        self.produto.status_enriquecimento_web = status
        self.db.add(self.produto)
        self.db.commit()

    async def _collect_html(self) -> Optional[str]:
        """Execute collect html as part of this module workflow."""
        self._add_log(
            "INFO",
            f"Iniciando enriquecimento web para produto ID {self.produto.id} com URL: {self.url}",
        )
        self._persist_status(models.StatusEnriquecimentoEnum.EM_PROGRESSO)
        return await self._runtime.collect_html(url=self.url)

    def _merge_metadata(self, dados_normalizados_de_meta: Dict[str, Any]) -> None:
        """Execute merge metadata as part of this module workflow."""
        if self.produto.dados_brutos_web is None:
            self.produto.dados_brutos_web = {}
        for key, value in dados_normalizados_de_meta.items():
            if value is not None or key not in self.produto.dados_brutos_web:
                self.produto.dados_brutos_web[key] = value

    def _define_status_final(
        self,
        *,
        dados_normalizados_de_meta: Dict[str, Any],
        texto_principal: Optional[str],
    ) -> models.StatusEnriquecimentoEnum:
        """Execute define status final as part of this module workflow."""
        if not dados_normalizados_de_meta and not texto_principal:
            self._add_log(
                "WARNING",
                "Nenhuma informacao util (metadados ou texto principal) foi extraida da URL.",
            )
            return models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA

        if not dados_normalizados_de_meta and texto_principal:
            self._add_log(
                "INFO",
                "Enriquecimento concluido com dados parciais (apenas texto da pagina).",
            )
            return models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS

        self._add_log("INFO", "Enriquecimento web concluido com sucesso.")
        return models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO

    async def run(self) -> models.Produto:
        """Execute run as part of this module workflow."""
        html_content = await self._collect_html()
        if not html_content:
            self._add_log("ERROR", "Falha ao coletar HTML da pagina.")
            self.produto.log_enriquecimento_web = self.log_enriquecimento
            self._persist_status(models.StatusEnriquecimentoEnum.FALHOU)
            self.db.refresh(self.produto)
            return self.produto

        self._add_log("INFO", "Conteudo HTML coletado com sucesso.")
        texto_principal = self._runtime.extract_main_text(html_content=html_content)
        if texto_principal:
            self._add_log("INFO", "Texto principal extraido com Trafilatura.")
        else:
            self._add_log(
                "WARNING",
                "Nao foi possivel extrair texto principal com Trafilatura.",
            )

        metadados_estruturados = self._runtime.extract_structured_metadata(
            html_content=html_content,
            url=self.url,
        )
        if metadados_estruturados:
            self._add_log(
                "INFO",
                "Metadados estruturados extraidos.",
                {"metadata_keys": list(metadados_estruturados.keys())},
            )
        else:
            self._add_log(
                "INFO",
                "Nenhum metadado estruturado (JSON-LD, Microdata, Opengraph) encontrado.",
            )

        dados_normalizados_de_meta = self._runtime.normalize_metadata(
            metadata=metadados_estruturados
        )
        if dados_normalizados_de_meta:
            self._add_log(
                "INFO",
                "Metadados normalizados.",
                {"normalized_keys": list(dados_normalizados_de_meta.keys())},
            )
        self._merge_metadata(dados_normalizados_de_meta)

        if texto_principal and isinstance(self.produto.dados_brutos_web, dict):
            self.produto.dados_brutos_web["texto_pagina_extraido"] = texto_principal[:15000]

        self.produto.status_enriquecimento_web = self._define_status_final(
            dados_normalizados_de_meta=dados_normalizados_de_meta,
            texto_principal=texto_principal,
        )
        self.produto.log_enriquecimento_web = self.log_enriquecimento

        self.db.add(self.produto)
        self.db.commit()
        self.db.refresh(self.produto)
        self.db.refresh(self.produto, attribute_names=["fornecedor"])
        return self.produto


class WebExtractionEnrichmentRuntime:
    """Represent Web Extraction Enrichment Runtime and centralize its responsibilities inside this module."""
    def __init__(
        self,
        *,
        content_collection_workflow: Optional[WebContentCollectionWorkflow] = None,
        extraction_support_workflow: Optional["WebExtractionSupportWorkflow"] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Extraction Enrichment Runtime."""
        self._content_collection_workflow = (
            content_collection_workflow or WebContentCollectionWorkflow()
        )
        self._extraction_support_workflow = (
            extraction_support_workflow or WebExtractionSupportWorkflow()
        )

    def now_iso(self) -> str:
        """Execute now iso as part of this module workflow."""
        return datetime.now(timezone.utc).isoformat()

    async def collect_html(self, *, url: str) -> Optional[str]:
        """Execute collect html as part of this module workflow."""
        return await self._content_collection_workflow.coletar_conteudo_pagina_playwright(url)

    def extract_main_text(self, *, html_content: str) -> Optional[str]:
        """Execute extract main text as part of this module workflow."""
        return self._extraction_support_workflow.extrair_texto_principal_com_trafilatura(
            html_content
        )

    def extract_structured_metadata(
        self, *, html_content: str, url: str
    ) -> Dict[str, Any]:
        """Execute extract structured metadata as part of this module workflow."""
        return self._extraction_support_workflow.extrair_metadados_estruturados(
            html_content,
            url,
        )

    def normalize_metadata(self, *, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize metadata to keep behavior consistent across callers."""
        return self._extraction_support_workflow.normalizar_dados_de_metadados(metadata)


WebExtractionEnrichmentWorkflow = WebExtractionEnrichmentWorkflow


class WebURLExtractionEngineRuntime:
    """Engine runtime OO para enriquecimento de produto por URL."""

    async def extract_relevant_data_from_url(
        self,
        db: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Extract relevant data from url."""
        workflow = WebExtractionEnrichmentWorkflow(db=db, url=url, produto=produto)
        return await workflow.run()


class WebOCREngineRuntime:
    """Engine runtime OO para OCR de região de imagem."""

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        try:
            from google.cloud import vision  # type: ignore
        except Exception as e:  # pragma: no cover - optional dependency
            logger.exception("Google Cloud Vision not available")
            raise HTTPException(
                status_code=500,
                detail="Ocorreu um erro durante a extração de dados.",
            ) from e

        try:
            logger.debug("Enviando para a API de OCR")
            client = vision.ImageAnnotatorClient()
            image = vision.Image(content=image_bytes)
            response = client.document_text_detection(image=image)
            logger.debug("Recebendo resposta da API")
            if response.error.message:
                raise RuntimeError(response.error.message)
            return response.full_text_annotation
        except Exception as e:
            logger.exception("Falha ao extrair texto da imagem")
            raise HTTPException(
                status_code=500,
                detail="Ocorreu um erro durante a extração de dados.",
            ) from e


class WebExtractionSupportRuntime:
    """Runtime OO para utilitarios de extração web e OCR."""

    RUNTIME_FIELDS = (
        "metadata_runtime",
        "llm_runtime",
        "enrichment_runtime",
        "ocr_runtime",
    )

    def __init__(
        self,
        *,
        metadata_runtime: Optional[Any] = None,
        llm_runtime: Optional[Any] = None,
        enrichment_runtime: Optional[Any] = None,
        ocr_runtime: Optional[Any] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Extraction Support Runtime."""
        self.metadata_runtime = metadata_runtime
        self.llm_runtime = llm_runtime
        self.enrichment_runtime = enrichment_runtime
        self.ocr_runtime = ocr_runtime

    def apply_overrides(self, runtime: Any) -> "WebExtractionSupportRuntime":
        """Execute apply overrides as part of this module workflow."""
        for field_name in self.RUNTIME_FIELDS:
            setattr(self, field_name, getattr(runtime, field_name, getattr(self, field_name)))
        return self


class WebExtractionSupportWorkflow:
    """Workflow OO para utilitarios de extração web e OCR."""

    def __init__(
        self,
        metadata_runtime: Optional[MetadataExtractionRuntime] = None,
        llm_runtime: Optional["WebLLMExtractionRuntime"] = None,
        enrichment_runtime: Optional["WebURLExtractionRuntime"] = None,
        ocr_runtime: Optional["WebOCRRuntime"] = None,
        runtime: Optional[Any] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Extraction Support Workflow."""
        runtime_obj = WebExtractionSupportRuntime(
            metadata_runtime=metadata_runtime,
            llm_runtime=llm_runtime,
            enrichment_runtime=enrichment_runtime,
            ocr_runtime=ocr_runtime,
        )
        if runtime is not None:
            runtime_obj.apply_overrides(runtime)

        self._runtime = runtime_obj
        self._metadata_runtime = runtime_obj.metadata_runtime or MetadataExtractionRuntime()
        self._llm_runtime = runtime_obj.llm_runtime or WebLLMExtractionRuntime()
        self._enrichment_runtime = runtime_obj.enrichment_runtime or WebURLExtractionRuntime()
        self._ocr_runtime = runtime_obj.ocr_runtime or WebOCRRuntime()

    def extrair_texto_principal_com_trafilatura(
        self, html_content: str
    ) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        return self._metadata_runtime.extrair_texto_principal_com_trafilatura(html_content)

    def extrair_metadados_estruturados(
        self, html_content: str, url: str
    ) -> Dict[str, Any]:
        """Execute extrair metadados estruturados as part of this module workflow."""
        return self._metadata_runtime.extrair_metadados_estruturados(
            html_content=html_content,
            url=url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute normalizar dados de metadados as part of this module workflow."""
        return self._metadata_runtime.normalizar_dados_de_metadados(metadata_bruta)

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extrair dados produto com llm."""
        return await self._llm_runtime.extrair_dados_produto_com_llm(
            texto_pagina=texto_pagina,
            metadados_normalizados=metadados_normalizados,
            campos_desejados=campos_desejados,
            produto_nome_base=produto_nome_base,
            user=user,
        )

    async def extract_relevant_data_from_url(
        self,
        db: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Extract relevant data from url."""
        return await self._enrichment_runtime.extract_relevant_data_from_url(
            db=db,
            url=url,
            produto=produto,
        )

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self._ocr_runtime.extract_text_from_image_region(
            image_bytes=image_bytes
        )


class WebLLMExtractionRuntime:
    """Runtime OO para extração de dados de produto via LLM."""

    def __init__(
        self,
        engine_runtime: Optional[WebLLMExtractionEngineRuntime] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web LLMExtraction Runtime."""
        self._engine_runtime = engine_runtime or WebLLMExtractionEngineRuntime()

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extrair dados produto com llm."""
        return await self._engine_runtime.extrair_dados_produto_com_llm(
            texto_pagina=texto_pagina,
            metadados_normalizados=metadados_normalizados,
            campos_desejados=campos_desejados,
            produto_nome_base=produto_nome_base,
            user=user,
        )


class WebURLExtractionRuntime:
    """Runtime OO para enriquecimento de produto por URL."""

    def __init__(
        self,
        engine_runtime: Optional[WebURLExtractionEngineRuntime] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web URLExtraction Runtime."""
        self._engine_runtime = engine_runtime or WebURLExtractionEngineRuntime()

    async def extract_relevant_data_from_url(
        self,
        db: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Extract relevant data from url."""
        return await self._engine_runtime.extract_relevant_data_from_url(
            db=db,
            url=url,
            produto=produto,
        )


class WebOCRRuntime:
    """Runtime OO para OCR de região de imagem."""

    def __init__(
        self,
        engine_runtime: Optional[WebOCREngineRuntime] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web OCRRuntime."""
        self._engine_runtime = engine_runtime or WebOCREngineRuntime()

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self._engine_runtime.extract_text_from_image_region(
            image_bytes=image_bytes
        )


class WebDataExtractorRuntime:
    """Composicao OO sem estado global para fluxos de extracao web."""

    def __init__(
        self,
        *,
        search_engine_runtime: Optional[WebSearchEngineRuntime] = None,
        content_fetch_engine_runtime: Optional[WebContentFetchEngineRuntime] = None,
        metadata_extraction_runtime: Optional[MetadataExtractionRuntime] = None,
        llm_extraction_engine_runtime: Optional[WebLLMExtractionEngineRuntime] = None,
        url_extraction_engine_runtime: Optional[WebURLExtractionEngineRuntime] = None,
        ocr_engine_runtime: Optional[WebOCREngineRuntime] = None,
        search_workflow: Optional[WebSearchWorkflow] = None,
        content_collection_workflow: Optional[WebContentCollectionWorkflow] = None,
        extraction_support_workflow: Optional[WebExtractionSupportWorkflow] = None,
        playwright_chromium_indisponivel: bool = False,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Data Extractor Runtime."""
        self._search_engine_runtime = search_engine_runtime or WebSearchEngineRuntime()
        self._content_fetch_engine_runtime = (
            content_fetch_engine_runtime
            or WebContentFetchEngineRuntime(search_runtime=self._search_engine_runtime)
        )
        self._metadata_extraction_runtime = (
            metadata_extraction_runtime or MetadataExtractionRuntime()
        )
        self._llm_extraction_engine_runtime = (
            llm_extraction_engine_runtime or WebLLMExtractionEngineRuntime()
        )
        self._url_extraction_engine_runtime = (
            url_extraction_engine_runtime or WebURLExtractionEngineRuntime()
        )
        self._ocr_engine_runtime = ocr_engine_runtime or WebOCREngineRuntime()

        self._search_workflow = search_workflow or WebSearchWorkflow(
            runtime=WebSearchRuntime(engine_runtime=self._search_engine_runtime)
        )
        self._content_collection_workflow = (
            content_collection_workflow
            or WebContentCollectionWorkflow(
                runtime=WebContentCollectionRuntime(
                    engine_runtime=self._content_fetch_engine_runtime
                )
            )
        )
        self._extraction_support_workflow = extraction_support_workflow or WebExtractionSupportWorkflow(
            metadata_runtime=self._metadata_extraction_runtime,
            llm_runtime=WebLLMExtractionRuntime(
                engine_runtime=self._llm_extraction_engine_runtime
            ),
            enrichment_runtime=WebURLExtractionRuntime(
                engine_runtime=self._url_extraction_engine_runtime
            ),
            ocr_runtime=WebOCRRuntime(engine_runtime=self._ocr_engine_runtime),
        )
        self._content_fetch_engine_runtime.set_playwright_chromium_indisponivel(
            playwright_chromium_indisponivel
        )

    @property
    def search_workflow(self) -> WebSearchWorkflow:
        """Execute search workflow as part of this module workflow."""
        return self._search_workflow

    @property
    def content_collection_workflow(self) -> WebContentCollectionWorkflow:
        """Execute content collection workflow as part of this module workflow."""
        return self._content_collection_workflow

    @property
    def extraction_support_workflow(self) -> WebExtractionSupportWorkflow:
        """Execute extraction support workflow as part of this module workflow."""
        return self._extraction_support_workflow

    def busca_publica_disponivel(self) -> bool:
        """Execute busca publica disponivel as part of this module workflow."""
        return self._search_workflow.busca_publica_disponivel()

    async def buscar_urls_publicas(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls publicas as part of this module workflow."""
        return await self._search_workflow.buscar_urls_publicas(
            query=query,
            num_results=num_results,
        )

    async def buscar_urls_google(
        self,
        query: str,
        num_results: int = 3,
    ) -> List[str]:
        """Execute buscar urls google as part of this module workflow."""
        return await self._search_workflow.buscar_urls_google(
            query=query,
            num_results=num_results,
        )

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        """Execute coletar conteudo pagina playwright as part of this module workflow."""
        return await self._content_collection_workflow.coletar_conteudo_pagina_playwright(
            url
        )

    def extrair_texto_principal_com_trafilatura(
        self,
        html_content: str,
    ) -> Optional[str]:
        """Extrair texto principal com trafilatura."""
        return self._extraction_support_workflow.extrair_texto_principal_com_trafilatura(
            html_content
        )

    def extrair_metadados_estruturados(
        self,
        html_content: str,
        url: str,
    ) -> Dict[str, Any]:
        """Execute extrair metadados estruturados as part of this module workflow."""
        return self._extraction_support_workflow.extrair_metadados_estruturados(
            html_content,
            url,
        )

    def normalizar_dados_de_metadados(
        self,
        metadata_bruta: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute normalizar dados de metadados as part of this module workflow."""
        return self._extraction_support_workflow.normalizar_dados_de_metadados(
            metadata_bruta
        )

    async def extrair_dados_produto_com_llm(
        self,
        texto_pagina: Optional[str],
        metadados_normalizados: Optional[Dict[str, Any]] = None,
        campos_desejados: Optional[List[str]] = None,
        produto_nome_base: str = "Produto",
        user: Optional[models.User] = None,
    ) -> Optional[Dict[str, Any]]:
        """Extrair dados produto com llm."""
        return await self._extraction_support_workflow.extrair_dados_produto_com_llm(
            texto_pagina=texto_pagina,
            metadados_normalizados=metadados_normalizados,
            campos_desejados=campos_desejados,
            produto_nome_base=produto_nome_base,
            user=user,
        )

    async def extract_relevant_data_from_url(
        self,
        *,
        session: Session,
        url: str,
        produto: models.Produto,
    ) -> models.Produto:
        """Extract relevant data from url."""
        return await self._extraction_support_workflow.extract_relevant_data_from_url(
            db=session,
            url=url,
            produto=produto,
        )

    def extract_text_from_image_region(self, image_bytes: bytes):
        """Extract text from image region."""
        return self._extraction_support_workflow.extract_text_from_image_region(
            image_bytes
        )

