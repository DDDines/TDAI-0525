"""Document validator crew module module responsibilities and runtime integration points."""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from typing import Any


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
    def build_llm():
        """Build llm from current inputs and configuration."""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not (openai_key and CREW_RUNTIME_AVAILABLE):
            return None
        return ChatOpenAI(
            model="gpt-4-turbo",
            verbose=True,
            temperature=0.1,
        )

    @staticmethod
    def build_executor() -> ThreadPoolExecutor:
        """Build executor from current inputs and configuration."""
        return ThreadPoolExecutor(
            max_workers=max(1, int(os.getenv("VALIDATION_CREW_WORKERS", "2")))
        )


class _ValidationCrewPromptBuilder:
    """Centraliza o prompt de validacao para evitar duplicacao."""

    ROLE = "Auditor de Qualidade de Dados de E-commerce"
    GOAL = """
        Sua missao e receber um dicionario de dados de produto (JSON) extraido de forma bruta
        e transforma-lo em um JSON limpo, padronizado e pronto para ser salvo em um banco de dados
        de e-commerce. Voce e o guardiao da qualidade dos dados.
    """
    BACKSTORY = """
        Voce e um especialista em dados de e-commerce com um olhar treinado para identificar
        e corrigir inconsistencias. Voce entende a importancia de SKUs, EANs, nomes de produtos,
        precos e descricoes para o funcionamento de uma loja online. Sua experiencia foi forjada
        analisando milhares de catalogos de produtos e corrigindo erros comuns de OCR, digitacao e
        formatacao. Voce e metodico, preciso e implacavel na busca pela padronizacao.
    """
    EXPECTED_OUTPUT = "Um objeto JSON contendo os dados do produto limpos e padronizados."

    @classmethod
    def build_validation_description(cls, raw_data: Any) -> str:
        """Build validation description from current inputs and configuration."""
        return f"""
            Analise o seguinte dicionario de dados brutos de um produto:
            ---
            {raw_data}
            ---

            Execute as seguintes acoes de limpeza e padronizacao:

            1.  **SKU e EAN**:
                - Remova espacos em branco extras, no inicio, no fim e no meio.
                - Corrija erros comuns de OCR: troque a letra 'O' por '0' (zero) e
                  a letra 'I' ou 'l' por '1' (um), apenas quando fizer sentido no
                  contexto de codigo de barras ou SKU.
                - Se o campo estiver vazio ou for nulo, mantenha `null` ou `None`.

            2.  **Nome do Produto (nome_base)**:
                - Corrija a capitalizacao para "Title Case".
                - Remova termos promocionais como "PROMOCAO" e "OFERTA".
                - Corrija erros obvios de digitacao, quando possivel.

            3.  **Preco (preco_original)**:
                - O valor deve ser numerico. Remova simbolos de moeda.
                - Converta virgula decimal para ponto.
                - Se nao for preco valido, retorne `null`.

            4.  **Descricao (descricao_original)**:
                - Corrija gramatica e ortografia.
                - Remova quebras excessivas e normalize espacos.
                - Mantenha apenas texto informativo e relevante.

            5.  **Marca (marca)**:
                - Padronize capitalizacao.

            IMPORTANTE:
            - O output final deve conter APENAS o objeto JSON corrigido.
            - Nao inclua explicacoes.
            - Campos invalidos devem ser `null`.
            - Mantenha a estrutura de chaves original.
        """


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
            role=self._prompt_builder.ROLE,
            goal=self._prompt_builder.GOAL,
            backstory=self._prompt_builder.BACKSTORY,
            verbose=True,
            llm=self._llm,
            allow_delegation=False,
        )
        validation_task = self._task_cls(
            description=self._prompt_builder.build_validation_description(raw_data),
            agent=data_quality_auditor,
            expected_output=self._prompt_builder.EXPECTED_OUTPUT,
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



