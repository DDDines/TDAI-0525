from __future__ import annotations

from typing import Any, Optional


class _FallbackValidatorCrew:
    @staticmethod
    def run_validation_crew(raw_data: Any):
        return raw_data


class ValidatorCrewFacade:
    """Adaptador OO para o validador IA com fallback seguro.

    Se dependências opcionais do validador não estiverem disponíveis,
    mantém o pipeline funcionando em modo pass-through.
    """

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
            from Backend.services import validator_crew as imported_runner  # type: ignore

            self._runner = getattr(
                imported_runner,
                "validator_crew_legacy_service",
                imported_runner,
            )
        except Exception as exc:  # pragma: no cover - depende de deps opcionais
            if self._logger:
                self._logger.warning(
                    "Validador IA indisponivel no startup (%s). Importacao seguira em modo fallback.",
                    exc,
                )
            self._runner = _FallbackValidatorCrew()

    def run_validation_crew(self, raw_data: Any):
        try:
            return self._runner.run_validation_crew(raw_data)
        except Exception as exc:
            if self._logger:
                self._logger.warning(
                    "Validador IA falhou durante execucao (%s). Usando fallback pass-through.",
                    exc,
                )
            return raw_data
