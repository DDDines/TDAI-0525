from __future__ import annotations

from Backend.application.services.validator_crew_facade import ValidatorCrewFacade


class _LegacyRunnerStub:
    def __init__(self, *, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    def run_validation_crew(self, raw_data):
        if self.should_fail:
            raise RuntimeError("boom")
        return {"validated": raw_data}


def test_validator_crew_facade_delegates_to_legacy_runner():
    facade = ValidatorCrewFacade(legacy_runner=_LegacyRunnerStub())
    payload = {"a": 1}

    result = facade.run_validation_crew(payload)

    assert result == {"validated": payload}


def test_validator_crew_facade_fallbacks_to_passthrough_on_runtime_error():
    facade = ValidatorCrewFacade(legacy_runner=_LegacyRunnerStub(should_fail=True))
    payload = {"a": 1}

    result = facade.run_validation_crew(payload)

    assert result == payload

