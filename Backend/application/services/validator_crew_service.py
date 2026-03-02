"""Document validator crew service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Optional

from Backend.infrastructure.adapters.validator_crew_adapter import (
    ValidatorCrewServiceAdapter,
)


class _FallbackValidatorCrew:
    """Represent Fallback Validator Crew and centralize its responsibilities inside this module."""
    @staticmethod
    def run_validation_crew(raw_data: Any):
        """Execute run validation crew as part of this module workflow."""
        return raw_data


class ValidatorCrewService:
    """OOP service for IA validation with safe fallback."""

    def __init__(
        self,
        *,
        logger: Any = None,
        runner: Optional[Any] = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Validator Crew Service."""
        self._logger = logger
        if runner is not None:
            self._runner = runner
            return

        try:
            self._runner = ValidatorCrewServiceAdapter()
        except Exception as exc:  # pragma: no cover
            if self._logger:
                self._logger.warning(
                    "IA validator unavailable at startup (%s). Running in pass-through mode.",
                    exc,
                )
            self._runner = _FallbackValidatorCrew()

    def run_validation_crew(self, raw_data: Any):
        """Execute run validation crew as part of this module workflow."""
        try:
            return self._runner.run_validation_crew(raw_data)
        except Exception as exc:
            if self._logger:
                self._logger.warning(
                    "IA validator runtime failure (%s). Using pass-through fallback.",
                    exc,
                )
            return raw_data
