from __future__ import annotations

from typing import Any, Optional

from Backend.infrastructure.legacy.validator_crew_bridge import (
    LegacyValidatorCrewBridge,
)


class _FallbackValidatorCrew:
    @staticmethod
    def run_validation_crew(raw_data: Any):
        return raw_data


class ValidatorCrewFacade:
    """OOP facade for IA validator with safe fallback."""

    def __init__(
        self,
        *,
        logger: Any = None,
        legacy_runner: Optional[Any] = None,
    ) -> None:
        self._logger = logger
        if legacy_runner is not None:
            self._runner = legacy_runner
            return

        try:
            self._runner = LegacyValidatorCrewBridge()
        except Exception as exc:  # pragma: no cover
            if self._logger:
                self._logger.warning(
                    "IA validator unavailable at startup (%s). Running in pass-through mode.",
                    exc,
                )
            self._runner = _FallbackValidatorCrew()

    def run_validation_crew(self, raw_data: Any):
        try:
            return self._runner.run_validation_crew(raw_data)
        except Exception as exc:
            if self._logger:
                self._logger.warning(
                    "IA validator runtime failure (%s). Using pass-through fallback.",
                    exc,
                )
            return raw_data
