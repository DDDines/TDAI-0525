from __future__ import annotations

import pytest

from Backend.testing.runtime_apis import web_extractor


@pytest.mark.asyncio
async def test_runtime_state_isola_cache_e_semaforo_de_busca():
    original_state = web_extractor.get_web_data_extractor_runtime_state()
    try:
        state_a = web_extractor._build_web_data_extractor_runtime_state()
        web_extractor.apply_web_data_extractor_runtime_state(state_a)

        await web_extractor._search_cache_set("peca:a", ["https://example.com/a"])
        assert await web_extractor._search_cache_get("peca:a") == ["https://example.com/a"]
        sem_a = web_extractor._get_search_semaphore()

        state_b = web_extractor._build_web_data_extractor_runtime_state()
        web_extractor.apply_web_data_extractor_runtime_state(state_b)

        assert await web_extractor._search_cache_get("peca:a") is None
        sem_b = web_extractor._get_search_semaphore()
        assert sem_a is not sem_b
    finally:
        web_extractor.apply_web_data_extractor_runtime_state(original_state)


def test_runtime_state_sincroniza_flag_playwright():
    original_state = web_extractor.get_web_data_extractor_runtime_state()
    try:
        state_on = web_extractor._build_web_data_extractor_runtime_state(
            playwright_chromium_indisponivel=True
        )
        web_extractor.apply_web_data_extractor_runtime_state(state_on)
        assert web_extractor.PLAYWRIGHT_CHROMIUM_INDISPONIVEL is True
        assert (
            web_extractor.get_web_data_extractor_runtime_state()
            .playwright_chromium_indisponivel
            is True
        )

        state_off = web_extractor._build_web_data_extractor_runtime_state(
            playwright_chromium_indisponivel=False
        )
        web_extractor.apply_web_data_extractor_runtime_state(state_off)
        assert web_extractor.PLAYWRIGHT_CHROMIUM_INDISPONIVEL is False
        assert (
            web_extractor.get_web_data_extractor_runtime_state()
            .playwright_chromium_indisponivel
            is False
        )
    finally:
        web_extractor.apply_web_data_extractor_runtime_state(original_state)

