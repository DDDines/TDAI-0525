"""Detailed coverage for validator crew bootstrap and runtime branches."""

from __future__ import annotations

import importlib.util
import sys
import types
from concurrent.futures import TimeoutError
from pathlib import Path

from Backend.testing.runtime_apis import validator_crew


def _load_validator_probe_module(monkeypatch, *, enabled: bool, available_imports: bool):
    monkeypatch.setenv("ENABLE_VALIDATION_CREW", "true" if enabled else "false")
    module_name = "Backend.tests._validator_probe_runtime"
    sys.modules.pop(module_name, None)

    if available_imports:
        crewai_module = types.ModuleType("crewai")
        crewai_module.Agent = type("Agent", (), {})
        crewai_module.Crew = type("Crew", (), {})
        crewai_module.Task = type("Task", (), {})
        crewai_module.Process = type("Process", (), {"sequential": "sequential"})
        langchain_module = types.ModuleType("langchain_openai")

        class _ChatOpenAI:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

        langchain_module.ChatOpenAI = _ChatOpenAI
        monkeypatch.setitem(sys.modules, "crewai", crewai_module)
        monkeypatch.setitem(sys.modules, "langchain_openai", langchain_module)
    else:
        monkeypatch.delitem(sys.modules, "crewai", raising=False)
        monkeypatch.delitem(sys.modules, "langchain_openai", raising=False)

    spec = importlib.util.spec_from_file_location(
        module_name,
        Path(__file__).resolve().parents[1] / "infrastructure" / "runtime_modules" / "validator_crew_module.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_validator_crew_bootstrap_handles_enabled_import_failure(monkeypatch):
    module = _load_validator_probe_module(
        monkeypatch,
        enabled=True,
        available_imports=False,
    )

    assert module.CREW_RUNTIME_AVAILABLE is False
    assert module.Agent is None
    assert module.ChatOpenAI is None


def test_validator_crew_bootstrap_factory_and_prompt_builder(monkeypatch):
    module = _load_validator_probe_module(
        monkeypatch,
        enabled=True,
        available_imports=True,
    )
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-12345678901234567890")
    monkeypatch.setenv("VALIDATION_CREW_WORKERS", "5")
    monkeypatch.setattr(module.settings, "OPENAI_API_KEY", None, raising=False)
    monkeypatch.setattr(module.settings, "AI_PROVIDER", "openai", raising=False)

    llm = module._ValidationCrewFactory.build_llm()
    executor = module._ValidationCrewFactory.build_executor()
    prompt = module._ValidationCrewPromptBuilder.build_validation_description({"sku": "1"})

    assert llm.kwargs["model"] == "gpt-4-turbo"
    assert llm.kwargs["temperature"] == 0.1
    assert llm.kwargs["api_key"] == "sk-openai-12345678901234567890"
    assert executor._max_workers == 5
    assert "sku" in prompt
    assert "Nome do Produto" in prompt
    assert module._ValidationCrewPromptBuilder.get_role() == "Auditor de Qualidade de Dados de E-commerce"
    executor.shutdown(wait=False)

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setattr(module.settings, "OPENAI_API_KEY", None, raising=False)
    assert module._ValidationCrewFactory.build_llm() is None


def test_validator_crew_bootstrap_factory_supports_lm_studio(monkeypatch):
    module = _load_validator_probe_module(
        monkeypatch,
        enabled=True,
        available_imports=True,
    )

    class _ResponseStub:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{"id": "google/gemma-3-12b"}]}

    monkeypatch.setattr(module.settings, "AI_PROVIDER", "lm_studio", raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1", raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_MODEL", None, raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_API_KEY", "lm-studio", raising=False)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: _ResponseStub())

    llm = module._ValidationCrewFactory.build_llm()

    assert llm.kwargs["model"] == "google/gemma-3-12b"
    assert llm.kwargs["base_url"] == "http://127.0.0.1:1234/v1"
    assert llm.kwargs["api_key"] == "lm-studio"


def test_validator_crew_factory_lm_studio_model_resolution_branches(monkeypatch):
    module = _load_validator_probe_module(
        monkeypatch,
        enabled=True,
        available_imports=True,
    )
    monkeypatch.setattr(module.settings, "AI_PROVIDER", "lm_studio", raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_BASE_URL", None, raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_MODEL", "google/gemma-3-12b", raising=False)
    monkeypatch.setattr(module.settings, "LM_STUDIO_API_KEY", "", raising=False)

    assert module._ValidationCrewFactory._resolve_openai_compatible_api_key() == "lm-studio"
    assert module._ValidationCrewFactory._resolve_openai_compatible_base_url() == "http://127.0.0.1:1234/v1"
    assert module._ValidationCrewFactory._resolve_openai_compatible_model() == "google/gemma-3-12b"

    class _ResponseWithModel:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{"id": "google/gemma-3-12b"}]}

    monkeypatch.setattr(module.settings, "LM_STUDIO_MODEL", None, raising=False)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: _ResponseWithModel())
    assert module._ValidationCrewFactory._resolve_openai_compatible_model() == "google/gemma-3-12b"

    monkeypatch.setattr(module.settings, "LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1", raising=False)
    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    assert module._ValidationCrewFactory._resolve_openai_compatible_model() is None

    class _ResponseWithoutModel:
        @staticmethod
        def raise_for_status():
            return None

        @staticmethod
        def json():
            return {"data": [{}]}

    monkeypatch.setattr(module.httpx, "get", lambda *args, **kwargs: _ResponseWithoutModel())
    assert module._ValidationCrewFactory._resolve_openai_compatible_model() is None


class _AgentStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _TaskStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class _CrewStub:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def kickoff(self):
        return {"validated": True}


class _ProcessStub:
    sequential = "sequential"


class _FutureSuccessStub:
    def __init__(self, result_value):
        self._result_value = result_value

    def result(self, timeout=None):
        _ = timeout
        return self._result_value


class _ExecutorSuccessStub:
    def submit(self, fn, *args, **kwargs):
        return _FutureSuccessStub(fn(*args, **kwargs))


class _FutureErrorStub:
    def __init__(self, error):
        self._error = error

    def result(self, timeout=None):
        _ = timeout
        raise self._error


class _ExecutorErrorStub:
    def __init__(self, error):
        self._error = error

    def submit(self, _fn, *_args, **_kwargs):
        return _FutureErrorStub(self._error)


def test_validation_crew_runtime_build_run_and_error_paths():
    runtime = validator_crew.ValidationCrewRuntime(
        llm_instance=object(),
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorSuccessStub(),
    )

    crew = runtime._build_crew({"sku": "1"})
    assert crew.kwargs["process"] == "sequential"
    assert crew.kwargs["tasks"][0].kwargs["expected_output"] == (
        validator_crew._ValidationCrewPromptBuilder.get_expected_output()
    )
    assert runtime._run_sync({"sku": "1"}) == {"validated": True}
    assert runtime.run({"sku": "1"}, timeout_seconds=3) == {"validated": True}

    unavailable_runtime = validator_crew.ValidationCrewRuntime(
        llm_instance=None,
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorSuccessStub(),
    )
    assert unavailable_runtime._build_crew({"sku": "1"}) is None
    assert unavailable_runtime._run_sync({"sku": "1"}) == {"sku": "1"}

    error_runtime = validator_crew.ValidationCrewRuntime(
        llm_instance=object(),
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorErrorStub(RuntimeError("boom")),
    )
    assert error_runtime.run({"sku": "1"}) == {"sku": "1"}

    timeout_runtime = validator_crew.ValidationCrewRuntime(
        llm_instance=object(),
        runtime_available=True,
        agent_cls=_AgentStub,
        task_cls=_TaskStub,
        crew_cls=_CrewStub,
        process_cls=_ProcessStub,
        executor=_ExecutorErrorStub(TimeoutError()),
    )
    assert timeout_runtime.run({"sku": "1"}) == {"sku": "1"}


def test_validation_crew_workflow_builds_default_runtime(monkeypatch):
    monkeypatch.setattr(
        validator_crew._ValidationCrewFactory,
        "build_llm",
        staticmethod(lambda: "llm-instance"),
    )
    monkeypatch.setattr(
        validator_crew._ValidationCrewFactory,
        "build_executor",
        staticmethod(lambda: "executor-instance"),
    )
    monkeypatch.setattr(validator_crew, "CREW_RUNTIME_AVAILABLE", True)
    monkeypatch.setattr(validator_crew, "Agent", _AgentStub)
    monkeypatch.setattr(validator_crew, "Task", _TaskStub)
    monkeypatch.setattr(validator_crew, "Crew", _CrewStub)
    monkeypatch.setattr(validator_crew, "Process", _ProcessStub)

    workflow = validator_crew.ValidationCrewWorkflow()

    assert workflow._runtime._llm == "llm-instance"
    assert workflow._runtime._executor == "executor-instance"
