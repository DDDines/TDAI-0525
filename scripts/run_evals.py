"""Run deterministic local LLM evals against the versioned CatalogAI prompt set."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.infrastructure.repositories.prompt_template_repository import (  # noqa: E402
    DEFAULT_PROMPT_TEMPLATES,
    PromptTemplateName,
)


DEFAULT_DATASET_PATH = PROJECT_ROOT / "scripts" / "evals" / "catalog_gold_cases.json"
DEFAULT_BASE_URL = os.getenv("LM_STUDIO_BASE_URL", "http://127.0.0.1:1234/v1").rstrip("/")
DEFAULT_API_KEY = os.getenv("LM_STUDIO_API_KEY", "lm-studio") or "lm-studio"
DEFAULT_MODEL = os.getenv("LM_STUDIO_MODEL", "").strip()
COMPANY_TIMELINE_PATTERN = re.compile(
    r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|anos\s+de\s+mercado|historico\s+da\s+empresa)\b",
    re.IGNORECASE,
)
PHONE_OR_ID_BLOCK_PATTERN = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")


class EvalFailure(Exception):
    """Signal a deterministic eval failure that should fail the process."""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the local eval runner."""
    parser = argparse.ArgumentParser(description="Run CatalogAI local LLM evals against LM Studio.")
    parser.add_argument("--dataset", default=str(DEFAULT_DATASET_PATH), help="Path to the JSON dataset.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="OpenAI-compatible base URL.")
    parser.add_argument("--api-key", default=DEFAULT_API_KEY, help="OpenAI-compatible API key.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="Model override. If omitted, uses /models discovery.")
    parser.add_argument("--min-pass-rate", type=float, default=0.90, help="Minimum pass rate required.")
    parser.add_argument("--max-failures", type=int, default=0, help="Maximum number of critical failures allowed.")
    return parser.parse_args()


def load_dataset(dataset_path: Path) -> List[Dict[str, Any]]:
    """Load the fixed eval dataset from disk."""
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise EvalFailure(f"Dataset invalido em {dataset_path}.")
    return payload


def resolve_model(base_url: str, api_key: str, requested_model: str) -> str:
    """Resolve the model from CLI override or the local /models endpoint."""
    if requested_model:
        return requested_model

    response = httpx.get(
        f"{base_url}/models",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    for item in payload.get("data", []):
        model_id = str((item or {}).get("id") or "").strip()
        if model_id:
            return model_id
    raise EvalFailure("Nenhum modelo carregado foi encontrado no LM Studio.")


def build_messages(case: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build the chat-completions payload using the same prompt templates as the backend."""
    product = case["input"]
    context = {
        "nome_base": product.get("nome_base", ""),
        "descricao": product.get("descricao_original", ""),
        "marca": product.get("marca", ""),
        "modelo": product.get("modelo", ""),
        "num_titulos": 1,
        "tamanho_palavras": 70,
    }
    if case["type"] == "title":
        return [
            {
                "role": "system",
                "content": DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_TITLE_SYSTEM].format(**context),
            },
            {
                "role": "user",
                "content": DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_TITLE_USER].format(**context),
            },
        ]

    return [
        {
            "role": "system",
            "content": DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_DESCRIPTION_SYSTEM].format(**context),
        },
        {
            "role": "user",
            "content": DEFAULT_PROMPT_TEMPLATES[PromptTemplateName.IA_OPENAI_DESCRIPTION_USER].format(**context),
        },
    ]


def call_model(*, base_url: str, api_key: str, model: str, case: Dict[str, Any]) -> str:
    """Call the local OpenAI-compatible endpoint for a single eval case."""
    response = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": build_messages(case),
            "temperature": 0.2,
            "max_tokens": 220,
        },
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    return str(payload["choices"][0]["message"]["content"]).strip()


def validate_case(case: Dict[str, Any], output_text: str) -> Tuple[bool, List[str]]:
    """Apply deterministic anti-hallucination checks to a generated output."""
    issues: List[str] = []
    normalized_text = " ".join(str(output_text or "").split())
    lowered_text = normalized_text.lower()

    if not normalized_text:
        issues.append("saida vazia")

    for forbidden in case.get("forbidden_patterns", []):
        if forbidden.lower() in lowered_text:
            issues.append(f"padrao proibido: {forbidden}")

    if COMPANY_TIMELINE_PATTERN.search(normalized_text):
        issues.append("historico de empresa/alucinacao institucional")
    if PHONE_OR_ID_BLOCK_PATTERN.search(normalized_text):
        issues.append("telefone ou bloco numerico suspeito")

    words = [word for word in re.split(r"\s+", normalized_text) if word]
    max_words = int(case.get("max_words", 0) or 0)
    min_words = int(case.get("min_words", 0) or 0)
    if max_words and len(words) > max_words:
        issues.append(f"saida longa demais: {len(words)} palavras")
    if min_words and len(words) < min_words:
        issues.append(f"saida curta demais: {len(words)} palavras")

    must_include_any = [str(item).lower() for item in case.get("must_include_any", []) if str(item).strip()]
    if must_include_any and not any(token in lowered_text for token in must_include_any):
        issues.append("nao menciona identidade minima do produto")

    return (len(issues) == 0, issues)


def main() -> int:
    """Run the local eval suite and exit non-zero on unacceptable quality."""
    args = parse_args()
    dataset_path = Path(args.dataset).resolve()
    cases = load_dataset(dataset_path)
    model_name = resolve_model(args.base_url.rstrip("/"), args.api_key, args.model)

    results = []
    for case in cases:
        output_text = call_model(
            base_url=args.base_url.rstrip("/"),
            api_key=args.api_key,
            model=model_name,
            case=case,
        )
        passed, issues = validate_case(case, output_text)
        results.append(
            {
                "id": case["id"],
                "type": case["type"],
                "passed": passed,
                "issues": issues,
                "output": output_text,
            }
        )

    failures = [result for result in results if not result["passed"]]
    pass_rate = (len(results) - len(failures)) / len(results)

    print(f"Model: {model_name}")
    print(f"Dataset: {dataset_path}")
    print(f"Pass rate: {pass_rate:.2%} ({len(results) - len(failures)}/{len(results)})")
    if failures:
        print("\nFailures:")
        for failure in failures[:10]:
            print(f"- {failure['id']} [{failure['type']}]: {', '.join(failure['issues'])}")
            print(f"  Output: {failure['output']}")

    if len(failures) > args.max_failures:
        print(f"\nCritical eval failure count exceeded: {len(failures)} > {args.max_failures}")
        return 1
    if pass_rate < args.min_pass_rate:
        print(f"\nPass rate below threshold: {pass_rate:.2%} < {args.min_pass_rate:.2%}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
