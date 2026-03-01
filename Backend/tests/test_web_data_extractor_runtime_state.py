from __future__ import annotations

import pytest

from Backend.testing.runtime_apis import web_extractor


class _TopLevelFunctionSurface:

    @pytest.mark.asyncio
    async def test_runtime_isola_cache_e_semaforo_de_busca_por_instancia():
        runtime_a = web_extractor.WebSearchEngineRuntime()
        runtime_b = web_extractor.WebSearchEngineRuntime()
    
        await runtime_a.search_cache_set("peca:a", ["https://example.com/a"])
        assert await runtime_a.search_cache_get("peca:a") == ["https://example.com/a"]
        assert await runtime_b.search_cache_get("peca:a") is None
    
        sem_a = runtime_a.get_search_semaphore()
        sem_b = runtime_b.get_search_semaphore()
        assert sem_a is not sem_b

    def test_runtime_sincroniza_flag_playwright():
        search_engine = web_extractor.WebSearchEngineRuntime()
        runtime = web_extractor.WebContentFetchEngineRuntime(search_runtime=search_engine)
        runtime.set_playwright_chromium_indisponivel(True)
        assert runtime.is_playwright_chromium_indisponivel() is True
    
        runtime.set_playwright_chromium_indisponivel(False)
        assert runtime.is_playwright_chromium_indisponivel() is False

test_runtime_isola_cache_e_semaforo_de_busca_por_instancia = _TopLevelFunctionSurface.test_runtime_isola_cache_e_semaforo_de_busca_por_instancia
test_runtime_sincroniza_flag_playwright = _TopLevelFunctionSurface.test_runtime_sincroniza_flag_playwright




