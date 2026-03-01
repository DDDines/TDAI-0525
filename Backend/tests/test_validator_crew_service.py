from __future__ import annotations

from Backend.application.services.validator_crew_service import ValidatorCrewService


class _RunnerStub:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def run_validation_crew(self, raw_data):
        if self.should_fail:
            raise RuntimeError("boom")
        return {"validated": raw_data}


class _TopLevelFunctionSurface:

    def test_validator_crew_service_delegates_to_runner():
        service = ValidatorCrewService(runner=_RunnerStub())
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == {"validated": payload}

    def test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error():
        service = ValidatorCrewService(runner=_RunnerStub(should_fail=True))
        payload = {"a": 1}
    
        result = service.run_validation_crew(payload)
    
        assert result == payload

test_validator_crew_service_delegates_to_runner = _TopLevelFunctionSurface.test_validator_crew_service_delegates_to_runner
test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error = _TopLevelFunctionSurface.test_validator_crew_service_fallbacks_to_passthrough_on_runtime_error


