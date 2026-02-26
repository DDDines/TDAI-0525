# catalogai_project/Backend/services/web_data_extractor_service.py
import asyncio
import sys
import time
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from bs4 import BeautifulSoup
import trafilatura # type: ignore
import extruct # type: ignore
import json
import re
from typing import List, Dict, Optional, Any, Tuple
from fastapi import HTTPException
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse
from urllib.request import Request, urlopen
from sqlalchemy.orm import Session # Importar Session para type hinting, se necessÃ¡rio
from datetime import datetime, timezone
from Backend.core.logging_config import get_logger

logger = get_logger(__name__)
PLAYWRIGHT_CHROMIUM_INDISPONIVEL = False


try:
    from googleapiclient.discovery import build # type: ignore
    GOOGLE_API_CLIENT_INSTALLED = True
except ImportError:
    GOOGLE_API_CLIENT_INSTALLED = False
    logger.warning(
        "Biblioteca google-api-python-client nÃ£o instalada ou com problemas. Busca no Google pode nÃ£o funcionar."
    )

# Ajustando as importaÃ§Ãµes para serem absolutas a partir da raiz do projeto (Backend)
# Assumindo que 'Backend' estÃ¡ no sys.path ou Ã© o diretÃ³rio de trabalho.
from Backend.core.config import settings
from Backend import models
from Backend.application.services.ia_generation_facade import IAGenerationFacade

ia_generation_service = IAGenerationFacade()

# --- Google Search Service ---
def busca_publica_disponivel() -> bool:
    """Indica se busca web sem API key pode ser usada como fallback."""
    return True


_SEARCH_CACHE: Dict[str, Tuple[float, List[str]]] = {}
_SEARCH_CACHE_TTL_SECONDS = 600.0
_SEARCH_CACHE_MAX_ENTRIES = 300
_SEARCH_CACHE_LOCK: Optional[asyncio.Lock] = None
_SEARCH_SEMAPHORE: Optional[asyncio.Semaphore] = None

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


def _get_search_cache_lock() -> asyncio.Lock:
    global _SEARCH_CACHE_LOCK
    if _SEARCH_CACHE_LOCK is None:
        _SEARCH_CACHE_LOCK = asyncio.Lock()
    return _SEARCH_CACHE_LOCK


def _get_search_semaphore() -> asyncio.Semaphore:
    global _SEARCH_SEMAPHORE
    if _SEARCH_SEMAPHORE is None:
        limit = int(getattr(settings, "WEB_SEARCH_CONCURRENCY", 3) or 3)
        _SEARCH_SEMAPHORE = asyncio.Semaphore(max(1, limit))
    return _SEARCH_SEMAPHORE


async def _search_cache_get(query_key: str) -> Optional[List[str]]:
    lock = _get_search_cache_lock()
    now = time.monotonic()
    async with lock:
        cached = _SEARCH_CACHE.get(query_key)
        if not cached:
            return None
        ts, urls = cached
        if (now - ts) > _SEARCH_CACHE_TTL_SECONDS:
            _SEARCH_CACHE.pop(query_key, None)
            return None
        return list(urls)


async def _search_cache_set(query_key: str, urls: List[str]) -> None:
    lock = _get_search_cache_lock()
    now = time.monotonic()
    async with lock:
        if len(_SEARCH_CACHE) >= _SEARCH_CACHE_MAX_ENTRIES:
            oldest_key = min(_SEARCH_CACHE.items(), key=lambda item: item[1][0])[0]
            _SEARCH_CACHE.pop(oldest_key, None)
        _SEARCH_CACHE[query_key] = (now, list(urls))


def _score_url_publica(url: str) -> int:
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


def _url_deve_ser_ignorada_antes_da_coleta(url: str) -> bool:
    """Evita coletar links de tracking, redirecionamento e pÃ¡ginas de busca."""
    parsed = urlparse(str(url or "").strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()

    if parsed.scheme not in {"http", "https"}:
        return True
    if not host:
        return True

    # Endpoints de tracking/redirect de buscadores.
    if "duckduckgo.com" in host and path in {"/y.js", "/redirect"}:
        return True
    if "bing.com" in host and path.startswith("/aclick"):
        return True
    if "bing.com" in host and path in {"/search", "/images/search"}:
        return True
    if "google.com" in host and path in {"/search", "/imgres", "/url"}:
        return True

    # Consultas com assinatura tÃ­pica de tracking.
    if any(hint in query for hint in _TRACKING_QUERY_HINTS):
        return True

    # Links diretos para PDF costumam abortar no Playwright e nÃ£o sÃ£o Ãºteis
    # no enriquecimento web textual padrÃ£o.
    if path.endswith(".pdf"):
        return True

    return False


def _normalizar_url_busca(candidata: str, base_url: str) -> Optional[str]:
    if not candidata:
        return None
    url_final = str(candidata).strip()
    if not url_final:
        return None
    if url_final.startswith("/"):
        url_final = urljoin(base_url, url_final)

    parsed = urlparse(url_final)
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()

    # URLs internas/trackers de buscadores nÃ£o devem entrar no pipeline.
    if "duckduckgo.com" in host:
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
        else:
            return None

        # Se continuou no domÃ­nio DuckDuckGo, descarta.
        if "duckduckgo.com" in host:
            return None

    # Alguns resultados vÃªm como click-tracker do Bing.
    if "bing.com" in host and parsed.path.lower().startswith("/aclick"):
        return None
    if "bing.com" in host and path in {"/search", "/images/search"}:
        return None
    if "google.com" in host and path in {"/search", "/imgres"}:
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
    if _url_deve_ser_ignorada_antes_da_coleta(url_final):
        return None
    return url_final


def _buscar_urls_publicas_sync(query: str, num_results: int = 3) -> List[str]:
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
            url_norm = _normalizar_url_busca(href or "", endpoint)
            if not url_norm or url_norm in vistos:
                continue
            vistos.add(url_norm)
            urls.append(url_norm)
            if len(urls) >= max(1, num_results):
                break
        if len(urls) >= max(1, num_results):
            break

    # Fallback adicional: proxy textual que costuma escapar bloqueios de JS/anti-bot.
    if len(urls) < max(1, num_results):
        proxy_endpoint = f"https://r.jina.ai/http://duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            req = Request(proxy_endpoint, headers=headers, method="GET")
            with urlopen(req, timeout=10) as resp:
                proxy_text = resp.read().decode("utf-8", errors="ignore")

            for href in re.findall(r"\((https?://[^)]+)\)", proxy_text):
                url_norm = _normalizar_url_busca(href, proxy_endpoint)
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
    scored_urls = sorted(deduped_urls, key=_score_url_publica, reverse=True)
    filtered_urls = [u for u in scored_urls if _score_url_publica(u) > -20]
    return filtered_urls[: max(1, num_results)] if filtered_urls else scored_urls[: max(1, num_results)]


async def _buscar_urls_publicas_async_impl(query: str, num_results: int = 3) -> List[str]:
    return await asyncio.to_thread(_buscar_urls_publicas_sync, query, num_results)


async def _buscar_urls_google_async_impl(query: str, num_results: int = 3) -> List[str]:
    query_limpa = str(query or "").strip()
    if not query_limpa:
        return []
    limite = max(1, num_results)
    cache_key = query_limpa.lower()

    cached_urls = await _search_cache_get(cache_key)
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

    async with _get_search_semaphore():
        if google_disponivel:
            try:
                def _executar_busca_google_interna_valida():
                    service = build("customsearch", "v1", developerKey=settings.GOOGLE_CSE_API_KEY, cache_discovery=False)
                    res = service.cse().list(q=query_limpa, cx=settings.GOOGLE_CSE_ID, num=limite).execute()
                    return [item['link'] for item in res.get('items', []) if 'link' in item]

                urls_encontradas = await asyncio.to_thread(_executar_busca_google_interna_valida)
                if urls_encontradas:
                    urls_encontradas = [
                        _normalizar_url_busca(url, "https://www.google.com")
                        for url in urls_encontradas
                    ]
                    urls_encontradas = [url for url in urls_encontradas if url]
                    logger.info(
                        "Busca Google CSE retornou %s URL(s) para query '%s'.",
                        len(urls_encontradas),
                        query_limpa,
                    )
                    urls_unicas = list(dict.fromkeys(urls_encontradas))[:limite]
                    await _search_cache_set(cache_key, urls_unicas)
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
            motivos_txt = ", ".join(motivos_google_indisponivel) if motivos_google_indisponivel else "configuracao ausente"
            logger.warning(
                "Google CSE indisponivel (%s). Usando fallback de busca publica.",
                motivos_txt,
            )

        urls_encontradas = await _buscar_urls_publicas_async_impl(
            query=query_limpa, num_results=limite
        )
        urls_unicas = list(dict.fromkeys(urls_encontradas))[:limite]
        if urls_unicas:
            logger.info(
                "Fallback de busca publica retornou %s URL(s) para query '%s'.",
                len(urls_unicas),
                query_limpa,
            )
        else:
            logger.warning("Fallback de busca publica nao retornou URLs para query '%s'.", query_limpa)
        await _search_cache_set(cache_key, urls_unicas)
        return urls_unicas

# --- Playwright Content Fetching Service ---
def _coletar_conteudo_pagina_http_sync(url: str, timeout: int = 20) -> Optional[str]:
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

    # Evita retornar binÃ¡rio/imagem quando a URL nÃ£o Ã© uma pÃ¡gina HTML.
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        return None
    return raw.decode("utf-8", errors="ignore")


async def _coletar_conteudo_pagina_http(url: str, timeout: int = 20) -> Optional[str]:
    try:
        return await asyncio.to_thread(_coletar_conteudo_pagina_http_sync, url, timeout)
    except Exception as e:
        logger.warning("Falha ao coletar conteÃºdo HTTP direto para %s: %s", url, e)
        return None


async def _coletar_conteudo_pagina_playwright_core(url: str) -> Optional[str]:
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


def _coletar_conteudo_playwright_em_thread_sync(url: str) -> Optional[str]:
    loop = None
    try:
        if sys.platform.startswith("win") and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
            loop = asyncio.WindowsProactorEventLoopPolicy().new_event_loop()  # type: ignore[attr-defined]
        else:
            loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(_coletar_conteudo_pagina_playwright_core(url))
    finally:
        if loop is not None:
            try:
                loop.run_until_complete(loop.shutdown_asyncgens())
            except Exception:
                pass
            loop.close()
        asyncio.set_event_loop(None)


async def _coletar_conteudo_pagina_playwright_impl(url: str) -> Optional[str]:
    global PLAYWRIGHT_CHROMIUM_INDISPONIVEL
    if _url_deve_ser_ignorada_antes_da_coleta(url):
        logger.info(
            "URL ignorada antes da coleta por baixa relevancia/tracking: %s",
            url,
        )
        return None
    if PLAYWRIGHT_CHROMIUM_INDISPONIVEL:
        return await _coletar_conteudo_pagina_http(url)

    # Em alguns ambientes Windows o loop padrao nao suporta subprocesso.
    # Nesses casos, tentamos executar Playwright em thread dedicada com loop Proactor.
    loop_name = asyncio.get_running_loop().__class__.__name__.lower()
    if sys.platform.startswith("win") and "selector" in loop_name:
        logger.warning(
            "Loop asyncio sem suporte a subprocesso detectado (%s). Tentando Playwright em thread dedicada.",
            loop_name,
        )
        try:
            html_from_thread = await asyncio.to_thread(
                _coletar_conteudo_playwright_em_thread_sync, url
            )
            if html_from_thread:
                logger.info("Playwright executado com sucesso via thread dedicada para %s.", url)
                return html_from_thread
        except PlaywrightTimeoutError:
            logger.error("Timeout ao carregar URL com Playwright (thread dedicada): %s", url)
        except Exception as e:
            erro_str = str(e)
            erro_curto = erro_str.splitlines()[0] if erro_str else "erro_desconhecido"
            if "Executable doesn't exist" in erro_str:
                if not PLAYWRIGHT_CHROMIUM_INDISPONIVEL:
                    logger.warning(
                        "Playwright Chromium indisponivel no ambiente. Usando fallback HTTP direto para proximas coletas."
                    )
                PLAYWRIGHT_CHROMIUM_INDISPONIVEL = True
                logger.warning("Falha Playwright (thread dedicada) para %s: %s", url, erro_curto)
            else:
                logger.warning(
                    "Falha Playwright via thread dedicada para %s: %s. Caindo para HTTP direto.",
                    url,
                    erro_curto,
                )
        return await _coletar_conteudo_pagina_http(url)

    try:
        return await _coletar_conteudo_pagina_playwright_core(url)
    except PlaywrightTimeoutError:
        logger.error("Timeout ao carregar URL com Playwright: %s", url)
        html_content = await _coletar_conteudo_pagina_http(url)
        if html_content:
            logger.info("Fallback HTTP direto usado apÃ³s timeout do Playwright para %s.", url)
        return html_content
    except Exception as e:
        erro_str = str(e)
        erro_curto = erro_str.splitlines()[0] if erro_str else "erro_desconhecido"
        if "Executable doesn't exist" in erro_str:
            if not PLAYWRIGHT_CHROMIUM_INDISPONIVEL:
                logger.warning(
                    "Playwright Chromium indisponivel no ambiente. Usando fallback HTTP direto para proximas coletas."
                )
            PLAYWRIGHT_CHROMIUM_INDISPONIVEL = True
            logger.warning("Falha Playwright para %s: %s", url, erro_curto)
        else:
            import traceback
            logger.error(
                "Erro ao coletar conteÃºdo com Playwright para %s: %s\n%s",
                url,
                e,
                traceback.format_exc(),
            )
        html_content = await _coletar_conteudo_pagina_http(url)
        if html_content:
            logger.info("Fallback HTTP direto usado apÃ³s falha do Playwright para %s.", url)
        return html_content
    except NotImplementedError:
        logger.warning(
            "Playwright indisponivel neste loop asyncio. Usando fallback HTTP direto para %s.",
            url,
        )
        return await _coletar_conteudo_pagina_http(url)
class _WebSearchWorkflow:
    """Workflow OO para estrategias de busca web."""

    async def buscar_urls_publicas(self, query: str, num_results: int = 3) -> List[str]:
        return await _buscar_urls_publicas_async_impl(query=query, num_results=num_results)

    async def buscar_urls_google(self, query: str, num_results: int = 3) -> List[str]:
        return await _buscar_urls_google_async_impl(query=query, num_results=num_results)


class _WebContentCollectionWorkflow:
    """Workflow OO para coleta de conteudo de pagina."""

    async def coletar_conteudo_pagina_playwright(self, url: str) -> Optional[str]:
        return await _coletar_conteudo_pagina_playwright_impl(url)


_web_search_workflow = _WebSearchWorkflow()
_web_content_collection_workflow = _WebContentCollectionWorkflow()


async def buscar_urls_publicas(query: str, num_results: int = 3) -> List[str]:
    return await _web_search_workflow.buscar_urls_publicas(
        query=query,
        num_results=num_results,
    )


async def buscar_urls_google(query: str, num_results: int = 3) -> List[str]:
    return await _web_search_workflow.buscar_urls_google(
        query=query,
        num_results=num_results,
    )


async def coletar_conteudo_pagina_playwright(url: str) -> Optional[str]:
    return await _web_content_collection_workflow.coletar_conteudo_pagina_playwright(url)


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
        logger.error("Erro ao extrair metadados estruturados de %s com extruct: %s", url, e)
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
    metadados_normalizados: Optional[Dict[str, Any]] = None,
    campos_desejados: Optional[List[str]] = None,
    produto_nome_base: str = "Produto",
    user: Optional[models.User] = None,
) -> Optional[Dict[str, Any]]:
    
    if not texto_pagina and not metadados_normalizados:
        logger.info("Nenhum texto de pÃ¡gina nem metadados fornecidos para extraÃ§Ã£o LLM.")
        return {"erro_llm": "Nenhum conteÃºdo para processar"}

    prompt_contexto_inicial = [
        f"VocÃª Ã© um assistente especialista em extrair informaÃ§Ãµes detalhadas de produtos de e-commerce para o produto '{produto_nome_base}'.",
        "Seu objetivo Ã© preencher um JSON com os campos solicitados da forma mais precisa possÃ­vel, com base no contexto fornecido."
    ]
    contexto_para_llm = ""
    if metadados_normalizados and isinstance(metadados_normalizados, dict) and any(metadados_normalizados.values()):
        contexto_para_llm += "Contexto de Metadados Estruturados (use como base, valide e complemente com o texto principal):\n"
        for k, v_item in metadados_normalizados.items():
            contexto_para_llm += f"- {k.replace('_', ' ')}: {str(v_item)[:200]}\n" # Limita o tamanho da string de valor
    if texto_pagina:
        contexto_para_llm += f"\nTexto Principal da PÃ¡gina (use para encontrar informaÃ§Ãµes e complementar/corrigir metadados):\n\"\"\"\n{texto_pagina[:10000]}\n\"\"\"" # Limita o tamanho do texto

    if not contexto_para_llm.strip():
        logger.info(
            "Contexto insuficiente para LLM (metadados e texto da pÃ¡gina vazios ou muito curtos)."
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
        "\n".join(prompt_contexto_inicial) +
        f"\n\nA partir do contexto e do texto da pÃ¡gina fornecidos, extraia RIGOROSAMENTE os seguintes campos e retorne APENAS um objeto JSON vÃ¡lido com esta estrutura:\n"
        f"{{\n{campos_formatados_prompt}\n}}\n"
        f"Se uma informaÃ§Ã£o para um campo especÃ­fico nÃ£o for encontrada de forma clara e inequÃ­voca, retorne null para esse campo. NÃ£o invente informaÃ§Ãµes.\n"
        f"Para campos do tipo lista (ex: 'lista_caracteristicas_beneficios_bullets', 'palavras_chave_seo_relevantes_lista'), retorne uma lista de strings.\n"
        f"Para campos do tipo dicionÃ¡rio (ex: 'especificacoes_tecnicas_dict'), retorne um dicionÃ¡rio chave-valor.\n"
        f"\nContexto e Texto para AnÃ¡lise:\n{contexto_para_llm}"
    )
    
    if user is not None:
        api_key_para_usar = user.chave_openai_pessoal or settings.OPENAI_API_KEY
    else:
        api_key_para_usar = settings.OPENAI_API_KEY
    if not api_key_para_usar:
        logger.warning(
            "Nenhuma chave API OpenAI disponÃ­vel para extraÃ§Ã£o de dados com LLM."
        )
        return {"erro_llm": "Chave API OpenAI nÃ£o configurada"}

    json_str_resposta = "" # Inicializa para evitar UnboundLocalError no except
    try:
        # A funÃ§Ã£o call_openai_api estÃ¡ em ia_generation_service
        prompt_messages = [
            {
                "role": "system",
                "content": "Sua tarefa Ã© extrair informaÃ§Ãµes de um texto e retornÃ¡-las em formato JSON conforme o schema solicitado. Seja preciso e nÃ£o adicione campos extras.",
            },
            {"role": "user", "content": prompt},
        ]
        json_str_resposta = await ia_generation_service.call_openai_api(
            prompt_messages=prompt_messages,
            api_key=api_key_para_usar,
            model="gpt-3.5-turbo-0125", # Exemplo de modelo, pode ser configurÃ¡vel
            max_tokens=2048, # Ajustar conforme necessidade
            temperature=0.0, # Baixa temperatura para extraÃ§Ã£o factual
        )
        
        # Tentativa de limpar a resposta da LLM para pegar apenas o JSON
        match = re.search(r"\{.*\}", json_str_resposta, re.DOTALL)
        if match:
            json_str_limpo = match.group(0)
        else:
            json_str_limpo = json_str_resposta # Se nÃ£o encontrar JSON delimitado, usa a resposta como estÃ¡

        dados_extraidos_llm = json.loads(json_str_limpo)
        
        # Merge inteligente: prioriza dados da LLM, mas mantÃ©m metadados se LLM nÃ£o fornecer
        final_data = metadados_normalizados.copy() if metadados_normalizados and isinstance(metadados_normalizados, dict) else {}
        if isinstance(dados_extraidos_llm, dict):
            for key_llm, val_llm in dados_extraidos_llm.items():
                # Sobrescreve ou adiciona apenas se o valor da LLM nÃ£o for None,
                # ou se a chave nÃ£o existia nos metadados (para adicionar novos campos extraÃ­dos)
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
    except ValueError as ve: # Ex: erro de API key na chamada da OpenAI
        logger.error("Erro na chamada da LLM para extraÃ§Ã£o: %s", ve)
        return {"erro_llm": str(ve), **(metadados_normalizados or {})}
    except Exception as e:
        import traceback
        logger.error("Erro inesperado na extraÃ§Ã£o com LLM: %s", traceback.format_exc())
        return {"erro_llm_inesperado": str(e), **(metadados_normalizados or {})}

# FunÃ§Ã£o principal do serviÃ§o de extraÃ§Ã£o, combinando as etapas
class _WebExtractionEnrichmentWorkflow:
    """Workflow OO para extracao/enriquecimento de uma URL de produto."""

    def __init__(self, *, db: Session, url: str, produto: models.Produto) -> None:
        self.db = db
        self.url = url
        self.produto = produto
        self.log_enriquecimento: List[Dict[str, Any]] = []

    def _add_log(
        self,
        level: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message,
        }
        if details:
            entry["details"] = details
        self.log_enriquecimento.append(entry)

    def _persist_status(self, status: models.StatusEnriquecimentoEnum) -> None:
        self.produto.status_enriquecimento_web = status
        self.db.add(self.produto)
        self.db.commit()

    async def _collect_html(self) -> Optional[str]:
        self._add_log(
            "INFO",
            f"Iniciando enriquecimento web para produto ID {self.produto.id} com URL: {self.url}",
        )
        self._persist_status(models.StatusEnriquecimentoEnum.EM_PROGRESSO)
        return await coletar_conteudo_pagina_playwright(self.url)

    def _merge_metadata(self, dados_normalizados_de_meta: Dict[str, Any]) -> None:
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
        html_content = await self._collect_html()
        if not html_content:
            self._add_log("ERROR", "Falha ao coletar HTML da pagina.")
            self.produto.log_enriquecimento_web = self.log_enriquecimento
            self._persist_status(models.StatusEnriquecimentoEnum.FALHOU)
            self.db.refresh(self.produto)
            return self.produto

        self._add_log("INFO", "Conteudo HTML coletado com sucesso.")
        texto_principal = extrair_texto_principal_com_trafilatura(html_content)
        if texto_principal:
            self._add_log("INFO", "Texto principal extraido com Trafilatura.")
        else:
            self._add_log(
                "WARNING",
                "Nao foi possivel extrair texto principal com Trafilatura.",
            )

        metadados_estruturados = extrair_metadados_estruturados(html_content, self.url)
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

        dados_normalizados_de_meta = _normalizar_dados_de_metadados(metadados_estruturados)
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


async def extract_relevant_data_from_url(
    db: Session,
    url: str,
    produto: models.Produto,
) -> models.Produto:
    workflow = _WebExtractionEnrichmentWorkflow(db=db, url=url, produto=produto)
    return await workflow.run()

def extract_text_from_image_region(image_bytes: bytes):
    """Extract text annotation for an image region using Google Vision."""
    try:
        from google.cloud import vision  # type: ignore
    except Exception as e:  # pragma: no cover - optional dependency
        logger.exception("Google Cloud Vision not available")
        raise HTTPException(status_code=500, detail="Ocorreu um erro durante a extraÃ§Ã£o de dados.") from e

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
        raise HTTPException(status_code=500, detail="Ocorreu um erro durante a extraÃ§Ã£o de dados.") from e

class WebDataExtractorLegacyService:
    """OO compatibility layer for legacy web extractor module."""

    def busca_publica_disponivel(self) -> bool:
        return busca_publica_disponivel()

    async def buscar_urls_publicas(self, *args: Any, **kwargs: Any):
        return await buscar_urls_publicas(*args, **kwargs)

    async def buscar_urls_google(self, *args: Any, **kwargs: Any):
        return await buscar_urls_google(*args, **kwargs)

    async def coletar_conteudo_pagina_playwright(self, *args: Any, **kwargs: Any):
        return await coletar_conteudo_pagina_playwright(*args, **kwargs)

    def extrair_texto_principal_com_trafilatura(self, *args: Any, **kwargs: Any):
        return extrair_texto_principal_com_trafilatura(*args, **kwargs)

    def extrair_metadados_estruturados(self, *args: Any, **kwargs: Any):
        return extrair_metadados_estruturados(*args, **kwargs)

    def normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return _normalizar_dados_de_metadados(*args, **kwargs)

    def _normalizar_dados_de_metadados(self, *args: Any, **kwargs: Any):
        return _normalizar_dados_de_metadados(*args, **kwargs)

    async def extrair_dados_produto_com_llm(self, *args: Any, **kwargs: Any):
        return await extrair_dados_produto_com_llm(*args, **kwargs)

    async def extract_relevant_data_from_url(self, *args: Any, **kwargs: Any):
        return await extract_relevant_data_from_url(*args, **kwargs)

    def extract_text_from_image_region(self, *args: Any, **kwargs: Any):
        return extract_text_from_image_region(*args, **kwargs)


web_data_extractor_legacy_service = WebDataExtractorLegacyService()


