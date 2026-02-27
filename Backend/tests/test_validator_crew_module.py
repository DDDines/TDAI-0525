from __future__ import annotations

from concurrent.futures import TimeoutError

import Backend.services.validator_crew as validator_crew


class _AgentStub:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _TaskStub:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs


class _CrewStub:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def kickoff(self):
        return {"validated": True}


class _ProcessStub:
    sequential = "sequential"


class _FutureTimeoutStub:
    @staticmethod
    def result(timeout=None):
        raise TimeoutError()


class _ExecutorTimeoutStub:
    @staticmethod
    def submit(_fn, *_args, **_kwargs):
        return _FutureTimeoutStub()


def test_runtime_returns_raw_data_when_unavailable():
    runtime = validator_crew._ValidationCrewRuntime(
        llm_instance=None,
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorTimeoutStub(),
    )
    payload = {"sku_original": "123"}

    result = runtime.run(payload)

    assert result == payload


def test_runtime_returns_raw_data_on_timeout():
    runtime = validator_crew._ValidationCrewRuntime(
        llm_instance=object(),
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorTimeoutStub(),
    )
    payload = {"nome_base": "Teste"}

    result = runtime.run(payload, timeout_seconds=1)

    assert result == payload


def test_run_validation_crew_delegates_to_workflow(monkeypatch):
    captured = {}

    class _WorkflowStub:
        @staticmethod
        def run_validation_crew(raw_data, timeout_seconds=8):
            captured["raw_data"] = raw_data
            captured["timeout_seconds"] = timeout_seconds
            return {"ok": raw_data}

    monkeypatch.setattr(validator_crew, "_validation_crew_workflow", _WorkflowStub())

    payload = {"id": 10}
    result = validator_crew.run_validation_crew(payload, timeout_seconds=5)

    assert result == {"ok": payload}
    assert captured == {"raw_data": payload, "timeout_seconds": 5}


def test_legacy_service_delegates_to_public_function(monkeypatch):
    monkeypatch.setattr(
        validator_crew,
        "run_validation_crew",
        lambda payload, timeout_seconds=8: {"legacy": payload, "timeout": timeout_seconds},
    )

    payload = {"x": 1}
    result = validator_crew.validator_crew_legacy_service.run_validation_crew(payload, timeout_seconds=3)

    assert result == {"legacy": payload, "timeout": 3}
