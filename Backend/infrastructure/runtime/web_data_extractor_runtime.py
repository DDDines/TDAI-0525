from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.services import web_data_extractor_service

    return web_data_extractor_service
