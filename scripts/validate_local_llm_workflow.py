"""Validate the local LM Studio workflow through the real CatalogAI API."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.core.config import settings  # noqa: E402


STATUS_PENDING = {"PENDENTE", "EM_PROGRESSO"}
STATUS_SUCCESS = {"CONCLUIDO"}
STATUS_FAILURE = {"FALHA"}
PHONE_OR_ID_BLOCK_PATTERN = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
COMPANY_TIMELINE_PATTERN = re.compile(
    r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|anos\s+de\s+mercado|historico\s+da\s+empresa)\b",
    re.IGNORECASE,
)
GENERIC_COMMERCE_PATTERNS = (
    re.compile(r"\bwhats(?:app)?\b", re.IGNORECASE),
    re.compile(r"\bcompra\s+online\b", re.IGNORECASE),
    re.compile(r"\bpolitica\s+de\b", re.IGNORECASE),
    re.compile(r"\bentrega\s+rapida\b", re.IGNORECASE),
    re.compile(r"\bfrete\b", re.IGNORECASE),
)
TITLE_CTA_PATTERN = re.compile(
    r"\b(?:exiba|exibir|descubra|transforme|aproveite|garanta|ideal|perfeito|perfeita|"
    r"seu|sua|seus|suas|compre|leve|tenha|melhore|renove|encante|celebre)\b",
    re.IGNORECASE,
)
TITLE_GENERIC_PATTERN = re.compile(r"\b(?:decor|decoracao|decorativo|decorativa)\b", re.IGNORECASE)
DESCRIPTION_CTA_PATTERN = re.compile(
    r"\b(?:adquira|compre|garanta|aproveite|invista|descubra|impulsione?|transforme|renove|eleve)\b",
    re.IGNORECASE,
)


class WorkflowValidationFailure(Exception):
    """Signal a deterministic local workflow validation failure."""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the local workflow validator."""
    parser = argparse.ArgumentParser(
        description="Validate the local LM Studio workflow through the real CatalogAI API."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL without /api/v1.")
    parser.add_argument("--api-prefix", default=settings.API_V1_STR, help="API prefix.")
    parser.add_argument("--admin-email", default=settings.ADMIN_EMAIL, help="Admin user email.")
    parser.add_argument("--admin-password", default=settings.ADMIN_PASSWORD, help="Admin user password.")
    parser.add_argument(
        "--lm-base-url",
        default=str(settings.LM_STUDIO_BASE_URL or "http://127.0.0.1:1234/v1").rstrip("/"),
        help="LM Studio OpenAI-compatible base URL.",
    )
    parser.add_argument(
        "--lm-model",
        default=str(settings.LM_STUDIO_MODEL or "").strip(),
        help="Explicit LM Studio model. Falls back to /models when empty.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=180,
        help="Maximum wait time for each generation task to reach a terminal status.",
    )
    parser.add_argument(
        "--report-path",
        default=str(PROJECT_ROOT / ".runtime" / "local-llm-validation-report.json"),
        help="Path to write the JSON report.",
    )
    parser.add_argument(
        "--keep-product",
        action="store_true",
        help="Keep the disposable smoke product instead of deleting it at the end.",
    )
    return parser.parse_args()


def normalize_text(value: Any) -> str:
    """Normalize text for deterministic comparisons."""
    text = str(value or "").strip()
    normalized = unicodedata.normalize("NFKD", text)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_text.split()).lower()


def tokenize_text(value: Any) -> List[str]:
    """Extract normalized tokens from text."""
    return re.findall(r"[a-z0-9]+", normalize_text(value))


def validate_generated_text(
    *,
    output_text: str,
    required_tokens: Sequence[str],
    min_words: int,
    max_words: int,
    check_title_style: bool = False,
) -> List[str]:
    """Apply deterministic anti-hallucination checks to a generated output."""
    issues: List[str] = []
    normalized_output = " ".join(str(output_text or "").split())
    lowered_output = normalize_text(normalized_output)
    words = [token for token in normalized_output.split() if token]

    if not normalized_output:
        issues.append("saida vazia")
        return issues

    if min_words and len(words) < min_words:
        issues.append(f"saida curta demais: {len(words)} palavras")
    if max_words and len(words) > max_words:
        issues.append(f"saida longa demais: {len(words)} palavras")

    if contains_suspicious_contact_number(normalized_output):
        issues.append("telefone ou bloco numerico suspeito")
    if EMAIL_PATTERN.search(normalized_output):
        issues.append("email indevido")
    if URL_PATTERN.search(normalized_output):
        issues.append("url indevida")
    if COMPANY_TIMELINE_PATTERN.search(normalized_output):
        issues.append("historico de empresa/alucinacao institucional")

    for pattern in GENERIC_COMMERCE_PATTERNS:
        if pattern.search(normalized_output):
            issues.append(f"boilerplate comercial: {pattern.pattern}")
    if check_title_style:
        if TITLE_CTA_PATTERN.search(normalized_output):
            issues.append("cta/promocional indevido")
        if TITLE_GENERIC_PATTERN.search(normalized_output):
            issues.append("complemento generico")
    elif DESCRIPTION_CTA_PATTERN.search(normalized_output):
        issues.append("cta/promocional na descricao")

    normalized_required_tokens = [normalize_text(token) for token in required_tokens if normalize_text(token)]
    matched_tokens = [token for token in normalized_required_tokens if token in lowered_output]
    if normalized_required_tokens and len(set(matched_tokens)) < min(2, len(set(normalized_required_tokens))):
        issues.append("identidade do produto insuficiente")

    return issues


def build_smoke_product_payload(*, fornecedor_id: int, product_type_id: int) -> Dict[str, Any]:
    """Build a disposable product payload rich enough for local prompt validation."""
    run_suffix = int(time.time())
    return {
        "nome_base": "Bomba de combustivel Bosch 12V flex",
        "descricao_original": (
            "Bomba de combustivel eletrica 12V para injecao eletronica, "
            "com pressao estavel, baixo ruido e aplicacao em motores flex."
        ),
        "marca": "Bosch",
        "modelo": f"F000TE{run_suffix}",
        "sku": f"LLM-SMOKE-{run_suffix}",
        "fornecedor_id": fornecedor_id,
        "product_type_id": product_type_id,
        "dynamic_attributes": {
            "voltagem": "12V",
            "aplicacao": "motores flex",
            "material": "aco",
        },
    }


def contains_suspicious_contact_number(output_text: str) -> bool:
    """Distinguish contact numbers from legitimate model/reference identifiers."""
    for match in PHONE_OR_ID_BLOCK_PATTERN.finditer(str(output_text or "")):
        candidate = match.group(0)
        digits_only = re.sub(r"\D", "", candidate)
        has_separator = bool(re.search(r"[\s()./-]", candidate))
        prefix_window = normalize_text(output_text[max(0, match.start() - 24):match.start()])

        if not digits_only:
            continue
        if any(keyword in prefix_window for keyword in ("modelo", "referencia", "ref", "codigo", "sku")):
            continue
        if not has_separator and len(digits_only) > 14:
            continue
        if len(digits_only) >= 10 and has_separator:
            return True
        if any(keyword in prefix_window for keyword in ("telefone", "celular", "whatsapp", "ligue")):
            return True
    return False


def resolve_lm_model(*, lm_base_url: str, api_key: str, requested_model: str) -> str:
    """Resolve the active LM Studio model from the local /models endpoint when needed."""
    if requested_model:
        return requested_model

    response = httpx.get(
        f"{lm_base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=20.0,
    )
    response.raise_for_status()
    payload = response.json()
    for item in payload.get("data", []):
        model_id = str((item or {}).get("id") or "").strip()
        if model_id:
            return model_id
    raise WorkflowValidationFailure("Nenhum modelo carregado foi encontrado no LM Studio.")


class LocalWorkflowValidator:
    """Drive a real local API workflow against the active LM Studio model."""

    def __init__(self, args: argparse.Namespace) -> None:
        self._args = args
        self._base_url = args.base_url.rstrip("/")
        self._api_prefix = args.api_prefix.rstrip("/")
        self._report_path = Path(args.report_path)
        self._report_path.parent.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(timeout=30.0)
        self._token: str | None = None
        self._created_product_id: int | None = None

    def _api_url(self, path: str) -> str:
        """Compose an absolute API URL from a route path."""
        return f"{self._base_url}{self._api_prefix}{path}"

    def _headers(self) -> Dict[str, str]:
        """Build authorization headers after login."""
        if not self._token:
            raise WorkflowValidationFailure("Token de autenticacao ausente.")
        return {"Authorization": f"Bearer {self._token}"}

    def ensure_backend_health(self) -> Dict[str, Any]:
        """Fail early when the local backend is not reachable."""
        response = self._client.get(f"{self._base_url}/health")
        response.raise_for_status()
        return response.json()

    def login(self) -> str:
        """Authenticate with the local backend using the configured admin user."""
        response = self._client.post(
            self._api_url("/auth/token"),
            data={"username": self._args.admin_email, "password": self._args.admin_password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        payload = response.json()
        token = str(payload.get("access_token") or "").strip()
        if not token:
            raise WorkflowValidationFailure("O endpoint de token nao retornou access_token.")
        self._token = token
        return token

    def _fetch_first_fornecedor_id(self) -> int:
        response = self._client.get(
            self._api_url("/fornecedores/"),
            headers=self._headers(),
            params={"skip": 0, "limit": 1},
        )
        response.raise_for_status()
        payload = response.json()
        items = payload.get("items") or []
        if not items:
            raise WorkflowValidationFailure("Nenhum fornecedor disponivel para montar o smoke local.")
        return int(items[0]["id"])

    def _fetch_first_product_type_id(self) -> int:
        response = self._client.get(
            self._api_url("/product-types/"),
            headers=self._headers(),
            params={"skip": 0, "limit": 1},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowValidationFailure("Nenhum tipo de produto disponivel para montar o smoke local.")
        return int(payload[0]["id"])

    def create_smoke_product(self) -> Dict[str, Any]:
        """Create a disposable product for the local LM Studio smoke validation."""
        fornecedor_id = self._fetch_first_fornecedor_id()
        product_type_id = self._fetch_first_product_type_id()
        payload = build_smoke_product_payload(
            fornecedor_id=fornecedor_id,
            product_type_id=product_type_id,
        )
        response = self._client.post(
            self._api_url("/produtos/"),
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        product = response.json()
        self._created_product_id = int(product["id"])
        return product

    def get_product(self, product_id: int) -> Dict[str, Any]:
        """Fetch the current product state from the API."""
        response = self._client.get(
            self._api_url(f"/produtos/{product_id}"),
            headers=self._headers(),
        )
        response.raise_for_status()
        return response.json()

    def trigger_generation(self, *, product_id: int, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Call one of the generation endpoints with query parameters."""
        response = self._client.post(
            self._api_url(endpoint.format(product_id=product_id)),
            headers=self._headers(),
            params=params,
        )
        response.raise_for_status()
        return response.json()

    def wait_for_generation(self, *, product_id: int, status_field: str) -> Dict[str, Any]:
        """Poll the product until a generation status reaches a terminal state."""
        deadline = time.monotonic() + max(10, self._args.timeout_seconds)
        last_product: Dict[str, Any] | None = None
        while time.monotonic() < deadline:
            current = self.get_product(product_id)
            last_product = current
            status_value = str(current.get(status_field) or "")
            if status_value in STATUS_SUCCESS:
                return current
            if status_value in STATUS_FAILURE:
                raise WorkflowValidationFailure(
                    f"Geracao falhou para campo {status_field}: status={status_value}"
                )
            time.sleep(2)

        raise WorkflowValidationFailure(
            f"Timeout aguardando {status_field}. Ultimo status observado: "
            f"{(last_product or {}).get(status_field)}"
        )

    def cleanup(self) -> None:
        """Delete the disposable smoke product when requested."""
        if self._args.keep_product or self._created_product_id is None:
            return
        response = self._client.delete(
            self._api_url(f"/produtos/{self._created_product_id}"),
            headers=self._headers(),
        )
        if response.status_code not in {200, 204}:
            raise WorkflowValidationFailure(
                f"Falha ao limpar o produto descartavel {self._created_product_id}: "
                f"status={response.status_code}"
            )

    def run(self) -> Dict[str, Any]:
        """Run the complete local LM Studio workflow validation."""
        self.ensure_backend_health()
        self.login()
        lm_model = resolve_lm_model(
            lm_base_url=self._args.lm_base_url,
            api_key="lm-studio",
            requested_model=self._args.lm_model,
        )
        smoke_product = self.create_smoke_product()
        product_id = int(smoke_product["id"])

        self.trigger_generation(
            product_id=product_id,
            endpoint="/geracao/titulos/openai/{product_id}",
            params={"num_titulos": 3},
        )
        title_result = self.wait_for_generation(product_id=product_id, status_field="status_titulo_ia")
        titles = list((title_result.get("dados_brutos_web") or {}).get("titulos_sugeridos_gerados") or [])
        if not titles:
            raise WorkflowValidationFailure("A geracao de titulos concluiu sem retornar titulos_sugeridos_gerados.")

        title_issues: List[str] = []
        required_tokens = ("bomba", "combustivel", "bosch", "12v")
        for index, title in enumerate(titles, start=1):
            current_issues = validate_generated_text(
                output_text=str(title or ""),
                required_tokens=required_tokens,
                min_words=3,
                max_words=16,
                check_title_style=True,
            )
            title_issues.extend([f"titulo_{index}: {issue}" for issue in current_issues])
        if len({normalize_text(item) for item in titles if normalize_text(item)}) != len(titles):
            title_issues.append("titulos duplicados")
        if title_issues:
            raise WorkflowValidationFailure("Falha de qualidade nos titulos: " + "; ".join(title_issues))

        titles_before_description = list(titles)
        self.trigger_generation(
            product_id=product_id,
            endpoint="/geracao/descricao/openai/{product_id}",
            params={"tamanho_palavras": 140},
        )
        description_result = self.wait_for_generation(product_id=product_id, status_field="status_descricao_ia")
        description_text = str(description_result.get("descricao_chat_api") or "")
        description_issues = validate_generated_text(
            output_text=description_text,
            required_tokens=required_tokens,
            min_words=40,
            max_words=220,
        )
        titles_after_description = list(
            ((description_result.get("dados_brutos_web") or {}).get("titulos_sugeridos_gerados") or [])
        )
        if titles_after_description != titles_before_description:
            description_issues.append("geracao de descricao alterou os titulos existentes")
        if description_issues:
            raise WorkflowValidationFailure(
                "Falha de qualidade na descricao: " + "; ".join(description_issues)
            )

        report = {
            "backend_base_url": self._base_url,
            "api_prefix": self._api_prefix,
            "lm_base_url": self._args.lm_base_url.rstrip("/"),
            "lm_model": lm_model,
            "product_id": product_id,
            "titles": titles_before_description,
            "description": description_text,
            "status_titulo_ia": title_result.get("status_titulo_ia"),
            "status_descricao_ia": description_result.get("status_descricao_ia"),
        }
        return report

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()


def main() -> int:
    """Run the local LM Studio workflow validation and write a JSON report."""
    args = parse_args()
    validator = LocalWorkflowValidator(args)
    payload: Dict[str, Any]
    exit_code = 0
    try:
        report = validator.run()
        payload = {"ok": True, **report}
    except Exception as exc:
        payload = {
            "ok": False,
            "error": str(exc),
            "product_id": validator._created_product_id,
        }
        exit_code = 1
    finally:
        try:
            validator.cleanup()
        except Exception as cleanup_exc:
            if exit_code == 0:
                payload = {
                    "ok": False,
                    "error": f"Falha ao limpar produto temporario: {cleanup_exc}",
                    "product_id": validator._created_product_id,
                }
                exit_code = 1
        validator.close()

    Path(args.report_path).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
