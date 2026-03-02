"""Module test validator crew service.

Contains backend logic related to test validator crew service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from Backend.application.services.validator_crew_service import ValidatorCrewService


class _RunnerStub:
    """Represent runner stub and centralize responsibilities for this module."""
    def __init__(self, *, should_fail: bool = False) -> None:
        """Initialize collaborators and configuration required by this component."""
        self.should_fail = should_fail

    def run_validation_crew(self, raw_data):
        """Run validation crew for this workflow."""
        if self.should_fail:
            raise RuntimeError("boom")
        return {"validated": raw_data}


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def test_validator_crew_service_delegates_to_runner():
        """Run test validator crew service delegates to runner in this workflow."""
        service = ValidatorCrewService(runner=_RunnerStub())
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == {"validated": payload}

    def test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error():
        """Run test validator crew service fallbacks to passthrough on runtime error in this workflow."""
        service = ValidatorCrewService(runner=_RunnerStub(should_fail=True))
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == payload

test_validator_crew_service_delegates_to_runner = _TopLevelFunctionSurface.test_validator_crew_service_delegates_to_runner
test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error = _TopLevelFunctionSurface.test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error


