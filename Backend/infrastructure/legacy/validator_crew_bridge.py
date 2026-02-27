from __future__ import annotations

from typing import Any, Optional

from Backend.core.legacy_guard import assert_legacy_usage_allowed
from Backend.services import validator_crew


class LegacyValidatorCrewBridge:
    """Bridge explicito para o modulo legado de validacao crew."""

    def __init__(self, module: Optional[Any] = None) -> None:
        self._module = module or validator_crew

    def run_validation_crew(self, *args: Any, **kwargs: Any):
        assert_legacy_usage_allowed(
            "Backend.infrastructure.legacy.LegacyValidatorCrewBridge"
        )
        return self._module.run_validation_crew(*args, **kwargs)
