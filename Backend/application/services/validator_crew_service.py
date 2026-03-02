"""Module validator crew service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any, Optional

from Backend.infrastructure.adapters.validator_crew_adapter import (
    ValidatorCrewServiceAdapter,
)


class _FallbackValidatorCrew:
    """Class _FallbackValidatorCrew.

    Encapsulates one responsibility in the backend architecture.
    """
    @staticmethod
    def run_validation_crew(raw_data: Any):
        """Execute run_validation_crew.

        This callable is documented to make behavior explicit for readers.
        """
        return raw_data


class ValidatorCrewService:
    """OOP service for IA validation with safe fallback."""

    def __init__(
        self,
        *,
        logger: Any = None,
        runner: Optional[Any] = None,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
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
        """Execute run_validation_crew.

        This callable is documented to make behavior explicit for readers.
        """
        try:
            return self._runner.run_validation_crew(raw_data)
        except Exception as exc:
            if self._logger:
                self._logger.warning(
                    "IA validator runtime failure (%s). Using pass-through fallback.",
                    exc,
                )
            return raw_data
