from __future__ import annotations

from typing import Any

from Backend.infrastructure.runtime.validator_crew_runtime import (
    get_runtime_service,
)


def _default_validator_runtime_service() -> Any:
    return get_runtime_service()


class ValidatorCrewServiceAdapter:
    """OOP port adapter backed by the current validator implementation."""

    def __init__(self, service: Any | None = None) -> None:
        self._service = service or _default_validator_runtime_service()

    def run_validation_crew(self, raw_data: Any):
        return self._service.run_validation_crew(raw_data)
