from __future__ import annotations

from concurrent.futures import TimeoutError

from Backend.testing.runtime_apis import validator_crew


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


class _TopLevelFunctionSurface:

    def test_runtime_returns_raw_data_when_unavailable():
        runtime = validator_crew.ValidationCrewRuntime(
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
        runtime = validator_crew.ValidationCrewRuntime(
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

    def test_run_validation_crew_delegates_to_runtime():
        captured = {}
    
        class _RuntimeStub:
            @staticmethod
            def run(raw_data, timeout_seconds=8):
                captured["raw_data"] = raw_data
                captured["timeout_seconds"] = timeout_seconds
                return {"ok": raw_data}
    
        workflow = validator_crew.ValidationCrewWorkflow(runtime=_RuntimeStub())
        payload = {"id": 10}
        result = workflow.run_validation_crew(payload, timeout_seconds=5)
    
        assert result == {"ok": payload}
        assert captured == {"raw_data": payload, "timeout_seconds": 5}

test_runtime_returns_raw_data_when_unavailable = _TopLevelFunctionSurface.test_runtime_returns_raw_data_when_unavailable
test_runtime_returns_raw_data_on_timeout = _TopLevelFunctionSurface.test_runtime_returns_raw_data_on_timeout
test_run_validation_crew_delegates_to_runtime = _TopLevelFunctionSurface.test_run_validation_crew_delegates_to_runtime







