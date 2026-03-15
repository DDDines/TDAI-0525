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
INCOMPLETE_REFERENCE_TOKEN_PATTERN = re.compile(r"\bref(?:erencia)?\b\s*$", re.IGNORECASE)
COMPANY_TIMELINE_PATTERN = re.compile(
    r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|anos\s+de\s+mercado|historico\s+da\s+empresa)\b",
    re.IGNORECASE,
)
DESCRIPTION_REQUIRED_HEADINGS = (
    "Resumo tecnico:",
    "Aplicacao:",
    "Referencia:",
    "Material:",
    "Conteudo da embalagem:",
    "Especificacoes tecnicas:",
    "Destaques tecnicos:",
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
    r"seu|sua|seus|suas|compre|tenha|melhore|renove|encante|celebre|leve\s+agora)\b",
    re.IGNORECASE,
)
TITLE_GENERIC_PATTERN = re.compile(r"\b(?:decor|decoracao|decorativo|decorativa|original|display)\b", re.IGNORECASE)
DESCRIPTION_CTA_PATTERN = re.compile(
    r"\b(?:adquira|compre|garanta|aproveite|invista|descubra|impulsione?|transforme|renove|eleve)\b",
    re.IGNORECASE,
)
DESCRIPTION_LOW_VALUE_PATTERN = re.compile(
    r"(?:depende\s+do\s+contexto|elementos?\s+decorativos?\s+ou\s+funcionais|"
    r"aplicacoes?\s+diversas|protecao\s+e\s+acabamento\s+visual|"
    r"oferecer\s+suporte\s+e\s+revestimento)",
    re.IGNORECASE,
)
GENERIC_MATERIAL_VARIANT_TOKENS = {
    "aco",
    "abs",
    "aluminio",
    "algodao",
    "borracha",
    "composto",
    "eva",
    "friccao",
    "liga",
    "metal",
    "mesh",
    "plastico",
    "policarbonato",
    "poliester",
    "tactel",
    "vidro",
}


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
    parser.add_argument(
        "--max-cases",
        type=int,
        default=0,
        help="Optional limit for the number of validation cases. Zero runs the full suite.",
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


def normalize_structured_key(value: Any) -> str:
    """Normalize structured spec keys so duplicates can be detected reliably."""
    normalized = re.sub(r"[^a-z0-9]+", "_", normalize_text(value)).strip("_")
    if normalized == "conteudo":
        return "conteudo_da_embalagem"
    return normalized


def _extract_section_lines(*, output_text: str, heading: str) -> List[str]:
    """Return the non-empty lines captured under one structured heading."""
    normalized_heading = normalize_text(heading)
    lines = [line.strip() for line in str(output_text or "").splitlines()]
    captured: List[str] = []
    in_section = False
    for line in lines:
        if not line:
            if in_section and captured:
                break
            continue
        normalized_line = normalize_text(line)
        if normalized_line == normalized_heading:
            in_section = True
            continue
        if in_section and normalized_line in {
            normalize_text(section_heading)
            for section_heading in DESCRIPTION_REQUIRED_HEADINGS
        }:
            break
        if in_section:
            captured.append(line)
    return captured


def validate_generated_text(
    *,
    output_text: str,
    required_tokens: Sequence[str],
    forbidden_terms: Sequence[str] = (),
    min_words: int,
    max_words: int,
    check_title_style: bool = False,
    expected_headings: Sequence[str] = (),
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
        if INCOMPLETE_REFERENCE_TOKEN_PATTERN.search(normalized_output):
            issues.append("referencia incompleta no titulo")
    else:
        if DESCRIPTION_CTA_PATTERN.search(normalized_output):
            issues.append("cta/promocional na descricao")
        if DESCRIPTION_LOW_VALUE_PATTERN.search(normalized_output):
            issues.append("resumo generico/placeholder")

    for heading in expected_headings:
        if normalize_text(heading) not in lowered_output:
            issues.append(f"secao obrigatoria ausente: {heading}")

    if expected_headings:
        non_empty_lines = [line.strip() for line in str(output_text or "").splitlines() if line.strip()]
        if non_empty_lines:
            last_line = non_empty_lines[-1]
            if last_line.endswith(":"):
                issues.append("descricao truncada ou mal finalizada")
            if last_line.startswith("- ") and not re.search(r"[.!?)]$", last_line):
                issues.append("bullet final truncado")

    normalized_required_tokens = [normalize_text(token) for token in required_tokens if normalize_text(token)]
    matched_tokens = [token for token in normalized_required_tokens if token in lowered_output]
    if normalized_required_tokens and len(set(matched_tokens)) < min(2, len(set(normalized_required_tokens))):
        issues.append("identidade do produto insuficiente")

    for forbidden_term in forbidden_terms:
        normalized_forbidden = normalize_text(forbidden_term)
        if not normalized_forbidden:
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(normalized_forbidden)}(?![a-z0-9])", lowered_output):
            issues.append(f"token proibido presente: {normalized_forbidden}")

    if expected_headings:
        description_lines = [line.strip() for line in str(output_text or "").splitlines() if line.strip()]
        product_heading = description_lines[0] if description_lines else ""
        summary_lines = _extract_section_lines(
            output_text=output_text,
            heading="Resumo tecnico:",
        )
        if product_heading and summary_lines:
            normalized_product_heading = normalize_text(product_heading)
            normalized_summary_first_line = normalize_text(summary_lines[0])
            if normalized_summary_first_line.startswith(normalized_product_heading + " "):
                summary_remainder = summary_lines[0][len(product_heading):].lstrip(" -:,.")
                if len(summary_remainder.split()) >= 3 and not summary_remainder[:1].islower():
                    issues.append("resumo repete o nome completo do produto")

        spec_lines = _extract_section_lines(
            output_text=output_text,
            heading="Especificacoes tecnicas:",
        )
        seen_spec_keys: set[str] = set()
        for spec_line in spec_lines:
            normalized_line = spec_line.strip()
            if normalized_line.startswith("- "):
                normalized_line = normalized_line[2:].strip()
            if ":" not in normalized_line:
                continue
            raw_key = normalized_line.split(":", 1)[0].strip()
            normalized_key = normalize_structured_key(raw_key)
            if not normalized_key:
                continue
            if normalized_key in seen_spec_keys:
                issues.append(f"chave duplicada em especificacoes tecnicas: {normalized_key}")
                continue
            seen_spec_keys.add(normalized_key)

    return issues


def _resolve_case_product_type_id(
    *,
    product_type_key: str,
    product_type_id: int,
    product_type_ids: Dict[str, int] | None,
) -> int:
    """Resolve one case product type using the keyed map when available."""
    normalized_key = normalize_structured_key(product_type_key)
    if product_type_ids and normalized_key in product_type_ids:
        return int(product_type_ids[normalized_key])
    return int(product_type_id)


def build_smoke_product_payload(
    *,
    fornecedor_id: int,
    product_type_id: int,
    product_type_ids: Dict[str, int] | None = None,
) -> Dict[str, Any]:
    """Build a disposable product payload rich enough for local prompt validation."""
    return build_smoke_product_cases(
        fornecedor_id=fornecedor_id,
        product_type_id=product_type_id,
        product_type_ids=product_type_ids,
    )[0]["payload"]


def build_smoke_product_cases(
    *,
    fornecedor_id: int,
    product_type_id: int,
    product_type_ids: Dict[str, int] | None = None,
) -> List[Dict[str, Any]]:
    """Return a broader local workflow validation suite spanning multiple product patterns."""
    run_suffix = int(time.time())
    return [
        {
            "id": "pump_bosch_flex",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Bomba de combustivel Bosch 12V flex",
                "descricao_original": (
                    "Bomba de combustivel eletrica 12V para injecao eletronica, "
                    "com pressao estavel, baixo ruido e aplicacao em motores flex."
                ),
                "marca": "Bosch",
                "modelo": f"0580454{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-PUMP-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "voltagem": "12V",
                    "aplicacao": "motores flex",
                    "material": "Aco",
                },
            },
            "required_tokens": ("bomba", "combustivel", "bosch", "12v"),
            "expect_reference_variant": True,
        },
        {
            "id": "lamp_philips_h7",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Lampada LED Philips H7 6500K 12V",
                "descricao_original": (
                    "Lampada LED H7 para substituicao automotiva com temperatura de cor 6500K, "
                    "alimentacao 12V e aplicacao em farois automotivos."
                ),
                "marca": "Philips",
                "modelo": f"12972WV{run_suffix % 100:02d}",
                "sku": f"LLM-SMOKE-LAMP-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "temperatura_cor": "6500K",
                    "voltagem": "12V",
                    "aplicacao": "farol automotivo",
                },
            },
            "required_tokens": ("lampada", "led", "philips", "h7"),
            "expect_reference_variant": True,
        },
        {
            "id": "filter_mann_primary",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Filtro de Ar Primario Mann C27010",
                "descricao_original": (
                    "Elemento filtrante primario para retencao de particulas em operacao severa, "
                    "com aplicacao em linha pesada."
                ),
                "marca": "Mann",
                "modelo": f"C27{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-FILTER-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "linha pesada",
                    "material": "papel filtrante",
                    "categoria": "filtracao de ar",
                },
            },
            "required_tokens": ("filtro", "ar", "mann"),
            "forbidden_terms": ("man",),
            "expect_reference_variant": True,
        },
        {
            "id": "sensor_abs_delphi",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Sensor ABS Delphi Traseiro 24V",
                "descricao_original": (
                    "Sensor para monitoramento do sistema ABS em eixos traseiros, "
                    "com operacao em 24V e aplicacao em caminhoes."
                ),
                "marca": "Delphi",
                "modelo": f"SS20{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-SENSOR-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "voltagem": "24V",
                    "posicao": "traseiro",
                    "aplicacao": "caminhoes",
                },
            },
            "required_tokens": ("sensor", "abs", "delphi", "24v"),
            "expect_reference_variant": True,
        },
        {
            "id": "brake_pad_trw_front",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Jogo de Pastilhas de Freio TRW Dianteira",
                "descricao_original": (
                    "Jogo de pastilhas dianteiras para freio a disco, com composto semimetalico "
                    "e aplicacao em veiculos de linha leve."
                ),
                "marca": "TRW",
                "modelo": f"GDB{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-BRAKE-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "posicao": "dianteira",
                    "aplicacao": "linha leve",
                    "material": "composto semimetalico",
                },
            },
            "required_tokens": ("pastilhas", "freio", "trw", "dianteira"),
            "expect_reference_variant": True,
        },
        {
            "id": "oil_filter_mahle_oc90",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Filtro de Oleo Mahle OC90",
                "descricao_original": (
                    "Filtro de oleo rosqueavel para lubrificacao de motores, com vedacao confiavel "
                    "e aplicacao em manutencao automotiva."
                ),
                "marca": "Mahle",
                "modelo": f"OC{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-OIL-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "lubrificacao de motores",
                    "material": "carcaca metalica",
                    "conteudo": "1 filtro",
                },
            },
            "required_tokens": ("filtro", "oleo", "mahle"),
            "forbidden_terms": ("man",),
            "expect_reference_variant": True,
        },
        {
            "id": "wheel_bearing_skf_vkba",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Rolamento de Roda SKF VKBA 3660",
                "descricao_original": (
                    "Rolamento de roda para cubo dianteiro com lubrificacao permanente "
                    "e aplicacao em linha leve."
                ),
                "marca": "SKF",
                "modelo": f"VKBA{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-BEARING-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "cubo dianteiro",
                    "material": "aco temperado",
                    "posicao": "dianteiro",
                },
            },
            "required_tokens": ("rolamento", "roda", "skf"),
            "forbidden_terms": ("man",),
            "expect_reference_variant": True,
        },
        {
            "id": "clutch_kit_luk_manual",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Kit de Embreagem Luk Cambio Manual",
                "descricao_original": (
                    "Kit de embreagem com disco, plato e rolamento, indicado para transmissao manual "
                    "e aplicacao em linha leve."
                ),
                "marca": "Luk",
                "modelo": f"62030{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-CLUTCH-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "cambio manual",
                    "conteudo": "disco, plato e rolamento",
                    "material": "aco e composto de friccao",
                },
            },
            "required_tokens": ("embreagem", "luk", "manual"),
            "forbidden_terms": ("man",),
            "expect_reference_variant": True,
        },
        {
            "id": "spark_plug_ngk_bkr6e11",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Vela de Ignicao NGK BKR6E-11",
                "descricao_original": (
                    "Vela de ignicao resistiva para motores a gasolina e flex, com partida confiavel "
                    "e faixa termica adequada para manutencao preventiva."
                ),
                "marca": "NGK",
                "modelo": f"BKR6E-{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-SPARK-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "motores gasolina e flex",
                    "material": "liga metalica",
                    "rosca": "14 mm",
                },
            },
            "required_tokens": ("vela", "ignicao", "ngk", "bkr6e"),
            "expect_reference_variant": True,
        },
        {
            "id": "timing_belt_contitech_ct1028",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Correia Dentada Contitech CT1028",
                "descricao_original": (
                    "Correia dentada para sincronismo de motores, com composto resistente ao desgaste "
                    "e aplicacao em manutencao de linha leve."
                ),
                "marca": "Contitech",
                "modelo": f"CT10{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-BELT-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "sincronismo de motores",
                    "material": "borracha reforcada",
                    "categoria": "transmissao",
                },
            },
            "required_tokens": ("correia", "dentada", "contitech", "ct"),
            "expect_reference_variant": True,
        },
        {
            "id": "wiper_bosch_aerofit_af26",
            "product_type_key": "automotivo",
            "payload": {
                "nome_base": "Palheta Limpador Bosch Aerofit AF26",
                "descricao_original": (
                    "Palheta limpadora com estrutura aerodinamica, borracha de limpeza uniforme "
                    "e aplicacao no para-brisa dianteiro."
                ),
                "marca": "Bosch",
                "modelo": f"AF{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-WIPER-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="automotivo",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "aplicacao": "para-brisa dianteiro",
                    "material": "borracha e aco",
                    "comprimento": "26 polegadas",
                },
            },
            "required_tokens": ("palheta", "limpador", "bosch", "aerofit"),
            "expect_reference_variant": True,
        },
        {
            "id": "headphone_jbl_tune_510bt",
            "product_type_key": "eletronicos",
            "payload": {
                "nome_base": "Fone Bluetooth JBL Tune 510BT Preto",
                "descricao_original": (
                    "Fone bluetooth on-ear com bateria de longa duracao, conexao sem fio "
                    "e assinatura sonora JBL Pure Bass para uso diario."
                ),
                "marca": "JBL",
                "modelo": f"T510BT{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-AUDIO-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="eletronicos",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "voltagem": "5V",
                    "cor_principal": "Preto",
                    "garantia_meses": "12",
                    "aplicacao": "uso diario",
                    "conteudo da embalagem": "fone e cabo usb-c",
                },
            },
            "required_tokens": ("fone", "bluetooth", "jbl", "510bt"),
            "expect_reference_variant": True,
        },
        {
            "id": "charger_baseus_gan_65w",
            "product_type_key": "eletronicos",
            "payload": {
                "nome_base": "Carregador USB-C Baseus GaN 65W Preto",
                "descricao_original": (
                    "Carregador compacto com tecnologia GaN, potencia de 65W e suporte a "
                    "carregamento rapido para notebooks e smartphones."
                ),
                "marca": "Baseus",
                "modelo": f"CCGAN65{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-CHARGER-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="eletronicos",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "voltagem": "Bivolt",
                    "cor_principal": "Preto",
                    "garantia_meses": "12",
                    "aplicacao": "carregamento rapido",
                    "conteudo da embalagem": "carregador e cabo usb-c",
                    "material": "abs e policarbonato",
                },
            },
            "required_tokens": ("carregador", "usb", "baseus", "65w"),
            "expect_reference_variant": True,
        },
        {
            "id": "mouse_logitech_m170_preto",
            "product_type_key": "eletronicos",
            "payload": {
                "nome_base": "Mouse Sem Fio Logitech M170 Preto",
                "descricao_original": (
                    "Mouse sem fio com conexao estavel 2.4 GHz, formato ambidestro e uso pratico "
                    "para escritorio e estudo."
                ),
                "marca": "Logitech",
                "modelo": f"M170{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-MOUSE-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="eletronicos",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "cor_principal": "Preto",
                    "conectividade": "2.4 GHz",
                    "aplicacao": "escritorio e estudo",
                    "conteudo da embalagem": "mouse e receptor usb",
                },
            },
            "required_tokens": ("mouse", "fio", "logitech", "m170"),
            "expect_reference_variant": True,
        },
        {
            "id": "teclado_redragon_kumara_k552",
            "product_type_key": "eletronicos",
            "payload": {
                "nome_base": "Teclado Mecanico Redragon Kumara K552",
                "descricao_original": (
                    "Teclado mecanico compacto com switches de resposta rapida, estrutura reforcada "
                    "e uso indicado para digitacao e jogos."
                ),
                "marca": "Redragon",
                "modelo": f"K552-{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-KEYBOARD-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="eletronicos",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "cor_principal": "Preto",
                    "material": "abs e metal",
                    "aplicacao": "digitacao e jogos",
                    "conteudo da embalagem": "teclado e cabo usb",
                },
            },
            "required_tokens": ("teclado", "mecanico", "redragon", "k552"),
            "expect_reference_variant": True,
        },
        {
            "id": "smart_tv_samsung_50_4k",
            "product_type_key": "eletronicos",
            "payload": {
                "nome_base": "Smart TV Samsung 50 4K UHD",
                "descricao_original": (
                    "Televisor com painel 4K, conectividade inteligente e imagem de alta definicao "
                    "para entretenimento domestico."
                ),
                "marca": "Samsung",
                "modelo": f"UN50UHD{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-TV-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="eletronicos",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "voltagem": "Bivolt",
                    "resolucao": "4K UHD",
                    "tamanho_tela": "50",
                    "aplicacao": "entretenimento domestico",
                },
            },
            "required_tokens": ("smart", "tv", "samsung", "4k"),
            "expect_reference_variant": True,
        },
        {
            "id": "camiseta_dryfit_unissex",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Camiseta Dry Fit Unissex Preta",
                "descricao_original": (
                    "Camiseta leve para treino e uso diario, com tecido respiravel, secagem "
                    "rapida e modelagem confortavel."
                ),
                "marca": "Move",
                "modelo": f"DRYFIT{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-SHIRT-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "G",
                    "cor": "Preta",
                    "material": "poliester",
                    "genero_vestuario": "Unissex",
                    "aplicacao": "treino e uso diario",
                },
            },
            "required_tokens": ("camiseta", "dry", "fit", "preta"),
            "expect_reference_variant": True,
        },
        {
            "id": "jaqueta_impermeavel_masculina",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Jaqueta Impermeavel Masculina Azul",
                "descricao_original": (
                    "Jaqueta com tecido impermeavel, forro leve e ajuste confortavel para "
                    "uso urbano em clima frio e chuva leve."
                ),
                "marca": "Northwind",
                "modelo": f"JAQ{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-JACKET-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "M",
                    "cor": "Azul",
                    "material": "poliester impermeavel",
                    "genero_vestuario": "Masculino",
                    "conteudo da embalagem": "1 jaqueta",
                    "aplicacao": "clima frio e chuva leve",
                },
            },
            "required_tokens": ("jaqueta", "impermeavel", "masculina", "azul"),
            "expect_reference_variant": True,
        },
        {
            "id": "calca_jeans_masculina_slim",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Calca Jeans Masculina Slim Azul Escuro",
                "descricao_original": (
                    "Calca jeans com modelagem slim, toque confortavel e uso indicado para "
                    "rotina casual."
                ),
                "marca": "Denim Co",
                "modelo": f"SLIM{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-JEANS-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "42",
                    "cor": "Azul Escuro",
                    "material": "algodao e elastano",
                    "genero_vestuario": "Masculino",
                    "aplicacao": "uso casual",
                },
            },
            "required_tokens": ("calca", "jeans", "masculina", "slim"),
            "expect_reference_variant": True,
        },
        {
            "id": "tenis_corrida_feminino_mesh",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Tenis Corrida Feminino Mesh Rosa",
                "descricao_original": (
                    "Tenis esportivo com cabedal em mesh, solado leve e uso voltado para corrida "
                    "e caminhada."
                ),
                "marca": "Sprint",
                "modelo": f"RUN{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-SHOE-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "38",
                    "cor": "Rosa",
                    "material": "mesh e eva",
                    "genero_vestuario": "Feminino",
                    "aplicacao": "corrida e caminhada",
                },
            },
            "required_tokens": ("tenis", "corrida", "feminino", "rosa"),
            "expect_reference_variant": True,
        },
        {
            "id": "moletom_canguru_unissex_cinza",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Moletom Canguru Unissex Cinza Mescla",
                "descricao_original": (
                    "Moletom com bolso frontal, toque macio e uso indicado para clima ameno "
                    "e combinacoes casuais."
                ),
                "marca": "Urban Fit",
                "modelo": f"MLT{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-HOODIE-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "GG",
                    "cor": "Cinza Mescla",
                    "material": "algodao e poliester",
                    "genero_vestuario": "Unissex",
                    "aplicacao": "clima ameno",
                },
            },
            "required_tokens": ("moletom", "canguru", "unissex", "cinza"),
            "expect_reference_variant": True,
        },
        {
            "id": "bermuda_tactel_masculina_preta",
            "product_type_key": "vestuario",
            "payload": {
                "nome_base": "Bermuda Tactel Masculina Preta",
                "descricao_original": (
                    "Bermuda leve de secagem rapida, com cintura confortavel e uso indicado para "
                    "praia, treino e lazer."
                ),
                "marca": "Wave",
                "modelo": f"TACTEL{run_suffix % 1000:03d}",
                "sku": f"LLM-SMOKE-SHORTS-{run_suffix}",
                "fornecedor_id": fornecedor_id,
                "product_type_id": _resolve_case_product_type_id(
                    product_type_key="vestuario",
                    product_type_id=product_type_id,
                    product_type_ids=product_type_ids,
                ),
                "dynamic_attributes": {
                    "tamanho": "M",
                    "cor": "Preta",
                    "material": "tactel",
                    "genero_vestuario": "Masculino",
                    "aplicacao": "praia treino e lazer",
                },
            },
            "required_tokens": ("bermuda", "tactel", "masculina", "preta"),
            "expect_reference_variant": True,
        },
    ]


def validate_title_set(
    *,
    titles: Sequence[str],
    required_tokens: Sequence[str],
    forbidden_terms: Sequence[str] = (),
    expect_reference_variant: bool = False,
) -> List[str]:
    """Validate the saved title list as a group, not only per-row fragments."""
    issues: List[str] = []
    normalized_titles = [str(title or "").strip() for title in titles if str(title or "").strip()]
    if len(normalized_titles) < 3:
        issues.append("menos de 3 titulos salvos")
        return issues

    seen = {normalize_text(item) for item in normalized_titles}
    if len(seen) != len(normalized_titles):
        issues.append("titulos duplicados")

    if expect_reference_variant and all(
        "ref " not in normalize_text(item) and "referencia " not in normalize_text(item)
        for item in normalized_titles
    ):
        issues.append("nenhuma variacao com referencia tecnica")

    if len(
        {
            normalize_text(item)
            for item in normalized_titles[1:]
            if normalize_text(item) != normalize_text(normalized_titles[0])
        }
    ) < 2:
        issues.append("baixa diversidade de variacoes de titulo")

    base_tokens = {
        token
        for token in tokenize_text(normalized_titles[0])
        if len(token) >= 3 and token not in {"ref", "referencia"}
    }
    for index, title in enumerate(normalized_titles, start=1):
        current_issues = validate_generated_text(
            output_text=title,
            required_tokens=required_tokens,
            forbidden_terms=forbidden_terms,
            min_words=3,
            max_words=16,
            check_title_style=True,
        )
        if index > 1:
            variant_tokens = {
                token
                for token in tokenize_text(title)
                if len(token) >= 3 and token not in {"ref", "referencia"}
            }
            extra_tokens = variant_tokens - base_tokens
            if variant_tokens and not extra_tokens and "ref " not in normalize_text(title):
                current_issues.append("variacao sem ganho semantico")
            if extra_tokens and extra_tokens <= GENERIC_MATERIAL_VARIANT_TOKENS and "ref " not in normalize_text(title):
                current_issues.append("variacao material generica")
        issues.extend([f"titulo_{index}: {issue}" for issue in current_issues])
    return issues


def compute_quality_score(*, issues: Sequence[str], penalty_per_issue: int) -> int:
    """Collapse deterministic validation issues into a simple quality score."""
    clean_issues = [issue for issue in issues if str(issue or "").strip()]
    return max(0, 100 - (len(clean_issues) * max(1, int(penalty_per_issue or 1))))


def summarize_quality_scores(case_reports: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Build aggregate metrics from per-case quality reports."""
    passed_cases = [case for case in case_reports if case.get("ok") is True]
    failed_cases = [case for case in case_reports if case.get("ok") is not True]
    title_scores = [
        int((case.get("title_quality") or {}).get("score"))
        for case in case_reports
        if isinstance((case.get("title_quality") or {}).get("score"), int)
    ]
    description_scores = [
        int((case.get("description_quality") or {}).get("score"))
        for case in case_reports
        if isinstance((case.get("description_quality") or {}).get("score"), int)
    ]
    case_scores = [
        float(case.get("case_score"))
        for case in case_reports
        if isinstance(case.get("case_score"), (int, float))
    ]

    def _avg(values: Sequence[float]) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 1)

    return {
        "total_cases": len(case_reports),
        "passed_cases": len(passed_cases),
        "failed_cases": len(failed_cases),
        "failed_case_ids": [case.get("id") for case in failed_cases],
        "title_score_avg": _avg(title_scores),
        "description_score_avg": _avg(description_scores),
        "case_score_avg": _avg(case_scores),
        "case_score_min": min(case_scores) if case_scores else None,
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
        self._created_product_ids: List[int] = []
        self._last_report: Dict[str, Any] | None = None

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

    def _fetch_product_type_map(self) -> Dict[str, int]:
        response = self._client.get(
            self._api_url("/product-types/"),
            headers=self._headers(),
            params={"skip": 0, "limit": 100},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            raise WorkflowValidationFailure("Nenhum tipo de produto disponivel para montar o smoke local.")
        product_type_map: Dict[str, int] = {}
        for item in payload:
            item_id = int(item["id"])
            key_name = normalize_structured_key(item.get("key_name"))
            friendly_name = normalize_structured_key(item.get("friendly_name"))
            if key_name:
                product_type_map[key_name] = item_id
            if friendly_name:
                product_type_map.setdefault(friendly_name, item_id)
        if not product_type_map:
            raise WorkflowValidationFailure("Nao foi possivel resolver um mapa valido de tipos de produto.")
        return product_type_map

    def create_smoke_product(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a disposable product for the local LM Studio smoke validation."""
        response = self._client.post(
            self._api_url("/produtos/"),
            headers=self._headers(),
            json=payload,
        )
        response.raise_for_status()
        product = response.json()
        self._created_product_ids.append(int(product["id"]))
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
        if self._args.keep_product or not self._created_product_ids:
            return
        cleanup_errors: List[str] = []
        for product_id in list(self._created_product_ids):
            response = self._client.delete(
                self._api_url(f"/produtos/{product_id}"),
                headers=self._headers(),
            )
            if response.status_code not in {200, 204}:
                cleanup_errors.append(f"{product_id}:{response.status_code}")
        if cleanup_errors:
            raise WorkflowValidationFailure(
                "Falha ao limpar produto(s) temporario(s): " + ", ".join(cleanup_errors)
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
        fornecedor_id = self._fetch_first_fornecedor_id()
        product_type_map = self._fetch_product_type_map()
        default_product_type_id = (
            product_type_map.get("automotivo")
            or product_type_map.get("eletronicos")
            or next(iter(product_type_map.values()))
        )
        cases = build_smoke_product_cases(
            fornecedor_id=fornecedor_id,
            product_type_id=default_product_type_id,
            product_type_ids=product_type_map,
        )
        if self._args.max_cases and self._args.max_cases > 0:
            cases = cases[: int(self._args.max_cases)]

        case_reports: List[Dict[str, Any]] = []
        failures: List[str] = []
        for case in cases:
            smoke_product = self.create_smoke_product(payload=case["payload"])
            product_id = int(smoke_product["id"])
            required_tokens = tuple(case.get("required_tokens") or ())
            case_report: Dict[str, Any] = {
                "id": case["id"],
                "product_id": product_id,
                "nome_base": case["payload"]["nome_base"],
                "modelo": case["payload"].get("modelo"),
                "product_type_key": case.get("product_type_key"),
                "product_type_id": case["payload"].get("product_type_id"),
            }
            try:
                self.trigger_generation(
                    product_id=product_id,
                    endpoint="/geracao/titulos/openai/{product_id}",
                    params={"num_titulos": 3},
                )
                title_result = self.wait_for_generation(product_id=product_id, status_field="status_titulo_ia")
                titles = list((title_result.get("dados_brutos_web") or {}).get("titulos_sugeridos_gerados") or [])
                if not titles:
                    raise WorkflowValidationFailure(
                        "A geracao de titulos concluiu sem retornar titulos_sugeridos_gerados."
                    )
                title_issues = validate_title_set(
                    titles=titles,
                    required_tokens=required_tokens,
                    expect_reference_variant=bool(case.get("expect_reference_variant")),
                )
                case_report["titles"] = titles
                case_report["title_quality"] = {
                    "issues": list(title_issues),
                    "score": compute_quality_score(issues=title_issues, penalty_per_issue=18),
                }
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
                    expected_headings=DESCRIPTION_REQUIRED_HEADINGS,
                )
                case_report["description"] = description_text
                case_report["description_quality"] = {
                    "issues": list(description_issues),
                    "score": compute_quality_score(issues=description_issues, penalty_per_issue=12),
                }
                titles_after_description = list(
                    ((description_result.get("dados_brutos_web") or {}).get("titulos_sugeridos_gerados") or [])
                )
                if titles_after_description != titles_before_description:
                    description_issues.append("geracao de descricao alterou os titulos existentes")
                    case_report["description_quality"] = {
                        "issues": list(description_issues),
                        "score": compute_quality_score(issues=description_issues, penalty_per_issue=12),
                    }
                if description_issues:
                    raise WorkflowValidationFailure(
                        "Falha de qualidade na descricao: " + "; ".join(description_issues)
                    )
                case_report["case_score"] = round(
                    (
                        case_report["title_quality"]["score"]
                        + case_report["description_quality"]["score"]
                    )
                    / 2,
                    1,
                )

                case_report.update(
                    {
                        "ok": True,
                        "titles": titles_before_description,
                        "description": description_text,
                        "status_titulo_ia": title_result.get("status_titulo_ia"),
                        "status_descricao_ia": description_result.get("status_descricao_ia"),
                    }
                )
            except Exception as exc:
                if "case_score" not in case_report:
                    title_score = (case_report.get("title_quality") or {}).get("score")
                    description_score = (case_report.get("description_quality") or {}).get("score")
                    known_scores = [
                        float(score)
                        for score in [title_score, description_score]
                        if isinstance(score, (int, float))
                    ]
                    if known_scores:
                        case_report["case_score"] = round(sum(known_scores) / len(known_scores), 1)
                case_report.update({"ok": False, "error": str(exc)})
                failures.append(f"{case['id']}: {exc}")
            case_reports.append(case_report)

        report = {
            "backend_base_url": self._base_url,
            "api_prefix": self._api_prefix,
            "lm_base_url": self._args.lm_base_url.rstrip("/"),
            "lm_model": lm_model,
            "cases": case_reports,
            "summary": summarize_quality_scores(case_reports),
            "ok": not failures,
        }
        self._last_report = report
        if failures:
            raise WorkflowValidationFailure(" ; ".join(failures))
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
        payload = validator._last_report or {}
        payload.update(
            {
                "ok": False,
                "error": str(exc),
                "product_ids": list(validator._created_product_ids),
            }
        )
        exit_code = 1
    finally:
        try:
            validator.cleanup()
        except Exception as cleanup_exc:
            if exit_code == 0:
                payload = validator._last_report or {}
                payload.update(
                    {
                        "ok": False,
                        "error": f"Falha ao limpar produto temporario: {cleanup_exc}",
                        "product_ids": list(validator._created_product_ids),
                    }
                )
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
