# Backend/services/validator_crew.py

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError

ENABLE_VALIDATION_CREW = os.getenv("ENABLE_VALIDATION_CREW", "false").lower() in (
    "1",
    "true",
    "yes",
    "on",
)

if ENABLE_VALIDATION_CREW:
    try:
        from crewai import Agent, Task, Crew, Process
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

# from langchain_google_genai import ChatGoogleGenerativeAI
# from dotenv import load_dotenv

# load_dotenv()

# llm = ChatGoogleGenerativeAI(
#     model="gemini-1.5-flash-latest",
#     verbose=True,
#     temperature=0.1,
#     google_api_key=os.getenv("GOOGLE_API_KEY"),
# )

# os.environ["OPENAI_API_KEY"] = "YOUR_API_KEY"
# os.environ["OPENAI_MODEL_NAME"] = "gpt-4-turbo"

_openai_key = os.getenv("OPENAI_API_KEY")
llm = (
    ChatOpenAI(
        model="gpt-4-turbo",
        verbose=True,
        temperature=0.1,
    )
    if _openai_key and CREW_RUNTIME_AVAILABLE
    else None
)

_validation_executor = ThreadPoolExecutor(
    max_workers=max(1, int(os.getenv("VALIDATION_CREW_WORKERS", "2")))
)


def _build_crew(raw_data):
    if llm is None or not CREW_RUNTIME_AVAILABLE:
        return None
    # --- AGENTE DE QUALIDADE DE DADOS ---
    data_quality_auditor = Agent(
        role="Auditor de Qualidade de Dados de E-commerce",
        goal="""
            Sua missão é receber um dicionário de dados de produto (JSON) extraído de forma bruta
            e transformá-lo em um JSON limpo, padronizado e pronto para ser salvo em um banco de dados
            de e-commerce. Você é o guardião da qualidade dos dados.
        """,
        backstory="""
            Você é um especialista em dados de e-commerce com um olhar treinado para identificar
            e corrigir inconsistências. Você entende a importância de SKUs, EANs, nomes de produtos,
            preços e descrições para o funcionamento de uma loja online. Sua experiência foi forjada
            analisando milhares de catálogos de produtos e corrigindo os erros mais comuns de OCR,
            digitação e formatação. Você é metódico, preciso e implacável na busca pela
            padronização.
        """,
        verbose=True,
        llm=llm,
        allow_delegation=False,
    )

    # --- TAREFA DE VALIDAÇÃO E LIMPEZA ---
    validation_task = Task(
        description=f"""
            Analise o seguinte dicionário de dados brutos de um produto:
            ---
            {raw_data}
            ---

            Execute as seguintes ações de limpeza e padronização:

            1.  **SKU e EAN**:
                - Remova espaços em branco extras, no início, no fim e no meio.
                - Corrija erros comuns de OCR: troque a letra 'O' por '0' (zero) e a letra 'I' ou 'l' por '1' (um), mas apenas se fizer sentido no contexto de um código de barras ou SKU.
                - Se o campo estiver vazio ou for nulo, mantenha-o como `null` ou `None`.

            2.  **Nome do Produto (nome_base)**:
                - Corrija a capitalização para "Title Case" (Ex: "nome do produto" -> "Nome do Produto").
                - Remova termos promocionais ou jargões desnecessários como "PROMOÇÃO", "OFERTA", etc.
                - Corrija erros de digitação óbvios, se possível.

            3.  **Preço (preco_original)**:
                - O valor deve ser um número (float ou int). Remova "R$", ",", "€" e outros símbolos de moeda.
                - Converta a vírgula decimal brasileira (`,`) para ponto (`.`). Ex: "1.234,56" -> 1234.56.
                - Se o campo contiver texto que não seja um preço (ex: "Sob consulta"), retorne `null`.

            4.  **Descrição (descricao_original)**:
                - Corrija erros de gramática e ortografia.
                - Remova quebras de linha excessivas e normalize o espaçamento.
                - Mantenha o texto informativo e relevante para o produto.

            5.  **Marca (marca)**:
                - Padronize a capitalização (ex: "marca A" -> "Marca A").

            **IMPORTANTE**: O seu output final **DEVE** ser **APENAS** o objeto JSON corrigido e nada mais.
            Não inclua explicações, apenas o JSON. Se um campo não puder ser corrigido ou for
            inválido, seu valor deve ser `null`. Mantenha a estrutura de chaves original.

            Exemplo de input:
            {{
                "nome_base": "pneu ARO 15 pirelli NOVO EM OFERTA",
                "sku_original": "PIR O15 ABC l23",
                "preco_original": "R$ 1.234,56",
                "descricao_original": "Pneu   novo, em otimo estado,  para carros de passeio.",
                "marca": "pirelli"
            }}

            Exemplo de output esperado:
            {{
                "nome_base": "Pneu Aro 15 Pirelli Novo",
                "sku_original": "PIR015ABC123",
                "preco_original": 1234.56,
                "descricao_original": "Pneu novo, em ótimo estado, para carros de passeio.",
                "marca": "Pirelli"
            }}
        """,
        agent=data_quality_auditor,
        expected_output="Um objeto JSON contendo os dados do produto limpos e padronizados.",
    )

    # --- MONTAGEM DA CREW ---
    validator_crew = Crew(
        agents=[data_quality_auditor],
        tasks=[validation_task],
        process=Process.sequential,
        verbose=2,
    )
    return validator_crew


def _run_validation_crew_sync(raw_data):
    crew = _build_crew(raw_data)
    if crew is None:
        return raw_data
    return crew.kickoff()


def _run_validation_crew_impl(raw_data, timeout_seconds: int = 8):
    """
    Executa a validação/limpeza via crewAI com timeout e fallback.
    Se houver falha ou estouro de tempo, devolve os dados brutos originais.
    """
    if llm is None:
        return raw_data
    try:
        future = _validation_executor.submit(_run_validation_crew_sync, raw_data)
        return future.result(timeout=timeout_seconds)
    except TimeoutError:
        return raw_data
    except Exception:
        return raw_data


class _ValidationCrewWorkflow:
    """Workflow OO para validação opcional via crewAI."""

    def run_validation_crew(self, raw_data, timeout_seconds: int = 8):
        return _run_validation_crew_impl(
            raw_data=raw_data,
            timeout_seconds=timeout_seconds,
        )


_validation_crew_workflow = _ValidationCrewWorkflow()


def run_validation_crew(raw_data, timeout_seconds: int = 8):
    return _validation_crew_workflow.run_validation_crew(
        raw_data=raw_data,
        timeout_seconds=timeout_seconds,
    )

class ValidatorCrewLegacyService:
    """OO compatibility layer for legacy validator crew module."""

    def run_validation_crew(self, *args, **kwargs):
        return run_validation_crew(*args, **kwargs)


validator_crew_legacy_service = ValidatorCrewLegacyService()
