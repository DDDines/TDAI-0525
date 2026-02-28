from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.services import file_processing_service

    return file_processing_service
