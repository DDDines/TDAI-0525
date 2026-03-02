"""Module test validator crew service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from Backend.application.services.validator_crew_service import ValidatorCrewService


class _RunnerStub:
    """Class _RunnerStub.

    Encapsulates one responsibility in the backend architecture.
    """
    def __init__(self, *, should_fail: bool = False) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self.should_fail = should_fail

    def run_validation_crew(self, raw_data):
        """Execute run_validation_crew.

        This callable is documented to make behavior explicit for readers.
        """
        if self.should_fail:
            raise RuntimeError("boom")
        return {"validated": raw_data}


class _TopLevelFunctionSurface:

    """Class _TopLevelFunctionSurface.

    Encapsulates one responsibility in the backend architecture.
    """
    def test_validator_crew_service_delegates_to_runner():
        """Execute test_validator_crew_service_delegates_to_runner.

        This callable is documented to make behavior explicit for readers.
        """
        service = ValidatorCrewService(runner=_RunnerStub())
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == {"validated": payload}

    def test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error():
        """Execute test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error.

        This callable is documented to make behavior explicit for readers.
        """
        service = ValidatorCrewService(runner=_RunnerStub(should_fail=True))
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == payload

test_validator_crew_service_delegates_to_runner = _TopLevelFunctionSurface.test_validator_crew_service_delegates_to_runner
test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error = _TopLevelFunctionSurface.test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error


