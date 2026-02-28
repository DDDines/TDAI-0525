from __future__ import annotations

from typing import Any


def get_runtime_module() -> Any:
    from Backend.infrastructure.runtime_modules import file_processing_module

    return file_processing_module
