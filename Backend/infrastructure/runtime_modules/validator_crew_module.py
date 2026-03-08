"""Document validator crew module module responsibilities and runtime integration points."""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any
import httpx

from Backend.core.api_key_validation import looks_like_openai_api_key, normalize_optional_secret
from Backend.core.config import settings
from Backend.infrastructure.repositories.prompt_template_repository import (
    PromptTemplateName,
    PromptTemplateResolver,
)


ENABLE_VALIDATION_CREW = os.getenv("ENABLE_VALIDATION_CREW", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

if ENABLE_VALIDATION_CREW:
    try:
        from crewai import Agent, Crew, Process, Task
        from langchain_openai import ChatOpenAI

        CREW_RUNTIME_AVAILABLE = True
    except Exception:
        Agent = Task = Crew = Process = None  # type: ignore
        ChatOpenAI = None  # type: ignore
        CREW_RUNTIME_AVAILABLE = False
else:
    Agent = Task = Crew = Process = None  # type: ignore
    ChatOpenAI = None  # type: ignore
    CREW_RUNTIME_AVAILABLE = False

class _ValidationCrewFactory:
    """Represent Validation Crew Factory and centralize its responsibilities inside this module."""

    @staticmethod
    def _is_lm_studio_enabled() -> bool:
        """Check whether validation crew should use the local OpenAI-compatible endpoint."""
        return (normalize_optional_secret(settings.AI_PROVIDER) or "openai").lower() == "lm_studio"

    @staticmethod
    def _resolve_openai_compatible_api_key() -> str | None:
        """Resolve the API key used by ChatOpenAI for the active provider."""
        if _ValidationCrewFactory._is_lm_studio_enabled():
            return normalize_optional_secret(settings.LM_STUDIO_API_KEY) or "lm-studio"

        openai_key = normalize_optional_secret(os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY)
        if looks_like_openai_api_key(openai_key):
            return openai_key
        return None

    @staticmethod
    def _resolve_openai_compatible_base_url() -> str | None:
        """Resolve the base URL for the active OpenAI-compatible provider."""
        if _ValidationCrewFactory._is_lm_studio_enabled():
            return str(settings.LM_STUDIO_BASE_URL or "http://127.0.0.1:1234/v1").rstrip("/")
        return None

    @staticmethod
    def _resolve_openai_compatible_model() -> str | None:
        """Resolve the model name used by validator crew."""
        if not _ValidationCrewFactory._is_lm_studio_enabled():
            return "gpt-4-turbo"

        configured_model = normalize_optional_secret(settings.LM_STUDIO_MODEL)
        if configured_model:
            return configured_model

        base_url = _ValidationCrewFactory._resolve_openai_compatible_base_url()
        api_key = _ValidationCrewFactory._resolve_openai_compatible_api_key()
        headers = {
            "Authorization": f"Bearer {api_key or 'lm-studio'}",
            "Content-Type": "application/json",
        }
        try:
            response = httpx.get(f"{base_url}/models", headers=headers, timeout=15.0)
            response.raise_for_status()
            payload = response.json()
            for model_item in payload.get("data", []):
                model_id = normalize_optional_secret((model_item or {}).get("id"))
                if model_id:
                    return model_id
        except Exception:
            return None
        return None

    @staticmethod
    def build_llm():
        """Build llm from current inputs and configuration."""
        openai_key = _ValidationCrewFactory._resolve_openai_compatible_api_key()
        model_name = _ValidationCrewFactory._resolve_openai_compatible_model()
        if not (openai_key and model_name and CREW_RUNTIME_AVAILABLE):
            return None
        llm_kwargs = {
            "model": model_name,
            "verbose": True,
            "temperature": 0.1,
            "api_key": openai_key,
        }
        base_url = _ValidationCrewFactory._resolve_openai_compatible_base_url()
        if base_url:
            llm_kwargs["base_url"] = base_url
        return ChatOpenAI(**llm_kwargs)

    @staticmethod
    def build_executor() -> ThreadPoolExecutor:
        """Build executor from current inputs and configuration."""
        return ThreadPoolExecutor(
            max_workers=max(1, int(os.getenv("VALIDATION_CREW_WORKERS", "2")))
        )


class _ValidationCrewPromptBuilder:
    """Centraliza o prompt de validacao para evitar duplicacao."""
    _resolver = PromptTemplateResolver()

    @classmethod
    def get_role(cls) -> str:
        """Return the validator crew role prompt from the prompt repository."""
        return cls._resolver.get_prompt(nome=PromptTemplateName.VALIDATOR_CREW_ROLE).conteudo

    @classmethod
    def get_goal(cls) -> str:
        """Return the validator crew goal prompt from the prompt repository."""
        return cls._resolver.get_prompt(nome=PromptTemplateName.VALIDATOR_CREW_GOAL).conteudo

    @classmethod
    def get_backstory(cls) -> str:
        """Return the validator crew backstory prompt from the prompt repository."""
        return cls._resolver.get_prompt(nome=PromptTemplateName.VALIDATOR_CREW_BACKSTORY).conteudo

    @classmethod
    def get_expected_output(cls) -> str:
        """Return the validator crew expected output prompt from the prompt repository."""
        return cls._resolver.get_prompt(nome=PromptTemplateName.VALIDATOR_CREW_EXPECTED_OUTPUT).conteudo

    @classmethod
    def build_validation_description(cls, raw_data: Any) -> str:
        """Build validation description from current inputs and configuration."""
        return cls._resolver.get_prompt(
            nome=PromptTemplateName.VALIDATOR_CREW_DESCRIPTION,
            context={"raw_data": raw_data},
        ).conteudo


class ValidationCrewRuntime:
    """Runtime OO para validacao opcional via crewAI."""

    def __init__(
        self,
        *,
        llm_instance,
        runtime_available: bool,
        agent_cls,
        task_cls,
        crew_cls,
        process_cls,
        executor: ThreadPoolExecutor,
        prompt_builder: type[_ValidationCrewPromptBuilder] = _ValidationCrewPromptBuilder,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Validation Crew Runtime."""
        self._llm = llm_instance
        self._runtime_available = runtime_available
        self._agent_cls = agent_cls
        self._task_cls = task_cls
        self._crew_cls = crew_cls
        self._process_cls = process_cls
        self._executor = executor
        self._prompt_builder = prompt_builder

    def _is_available(self) -> bool:
        """Execute is available as part of this module workflow."""
        return bool(self._runtime_available and self._llm is not None)

    def _build_crew(self, raw_data: Any):
        """Build crew from current inputs and configuration."""
        if not self._is_available():
            return None

        data_quality_auditor = self._agent_cls(
            role=self._prompt_builder.get_role(),
            goal=self._prompt_builder.get_goal(),
            backstory=self._prompt_builder.get_backstory(),
            verbose=True,
            llm=self._llm,
            allow_delegation=False,
        )
        validation_task = self._task_cls(
            description=self._prompt_builder.build_validation_description(raw_data),
            agent=data_quality_auditor,
            expected_output=self._prompt_builder.get_expected_output(),
        )
        return self._crew_cls(
            agents=[data_quality_auditor],
            tasks=[validation_task],
            process=self._process_cls.sequential,
            verbose=2,
        )

    def _run_sync(self, raw_data: Any):
        """Execute run sync as part of this module workflow."""
        crew = self._build_crew(raw_data)
        if crew is None:
            return raw_data
        return crew.kickoff()

    def run(self, raw_data: Any, timeout_seconds: int = 8):
        """Execute run as part of this module workflow."""
        if not self._is_available():
            return raw_data
        try:
            future = self._executor.submit(self._run_sync, raw_data)
            return future.result(timeout=timeout_seconds)
        except TimeoutError:
            return raw_data
        except Exception:
            return raw_data


class ValidationCrewWorkflow:
    """Workflow OO para validacao opcional via crewAI."""

    def __init__(self, runtime: ValidationCrewRuntime | None = None) -> None:
        """Initialize injected dependencies and runtime configuration for Validation Crew Workflow."""
        self._runtime = runtime or ValidationCrewRuntime(
            llm_instance=_ValidationCrewFactory.build_llm(),
            runtime_available=CREW_RUNTIME_AVAILABLE,
            agent_cls=Agent,
            task_cls=Task,
            crew_cls=Crew,
            process_cls=Process,
            executor=_ValidationCrewFactory.build_executor(),
        )

    def run_validation_crew(self, raw_data: Any, timeout_seconds: int = 8):
        """Execute run validation crew as part of this module workflow."""
        return self._runtime.run(raw_data=raw_data, timeout_seconds=timeout_seconds)



