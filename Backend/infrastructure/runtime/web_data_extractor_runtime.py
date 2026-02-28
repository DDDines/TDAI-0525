from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.infrastructure.runtime_modules import web_data_extractor_module

    return web_data_extractor_module
