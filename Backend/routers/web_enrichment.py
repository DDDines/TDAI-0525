# catalogai_project/Backend/routers/web_enrichment.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError # Para capturar exceções do SQLAlchemy
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import re
import unicodedata
from urllib.parse import urlparse

from Backend import crud_users
from Backend import crud_produtos
from Backend import crud
from Backend import models
from Backend import schemas
from Backend.database import get_db, SessionLocal

from .auth_utils import get_current_active_user

from Backend.services import web_data_extractor_service as web_extractor
from Backend.core.config import settings
from Backend.core.logging_config import get_logger

router = APIRouter(
    prefix="/enriquecimento-web",
    tags=["Enriquecimento de Produto via Web"],
    dependencies=[Depends(get_current_active_user)],
    # Evita 307 por barra final/ausente que pode perder Authorization em alguns clientes.
    redirect_slashes=False,
)

logger = get_logger(__name__)


def _fold_text(value: Any) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def _is_empty(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return True
        folded = _fold_text(raw)
        return folded in {"none", "null", "nan", "na", "n a", "-", "--"}
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) == 0
    return False


def _as_text(value: Any, max_len: int = 8000) -> Optional[str]:
    if _is_empty(value):
        return None
    if isinstance(value, (list, tuple, set)):
        parts = [str(v).strip() for v in value if not _is_empty(v)]
        text = " | ".join(parts)
    else:
        text = str(value).strip()
    if not text:
        return None
    return text[:max_len] if len(text) > max_len else text


def _first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if not _is_empty(value):
            return value
    return None


def _parse_price(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("R$", "").replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    else:
        text = text.replace(",", ".")
    text = re.sub(r"[^0-9.\-]", "", text)
    try:
        return float(text)
    except Exception:
        return None


def _sanitize_code_value(value: Any) -> Optional[str]:
    text = _as_text(value, max_len=120)
    if not text:
        return None
    clean = (
        unicodedata.normalize("NFKD", text)
        .encode("ascii", "ignore")
        .decode("ascii")
        .upper()
        .strip()
    )
    clean = re.sub(r"[^A-Z0-9./-]", "", clean)
    for suffix in ("MARCA", "MATERIAL", "PESO", "QUANTIDADE", "REFERENCIA", "CODIGO", "ATENCAO"):
        if clean.endswith(suffix) and len(clean) > len(suffix) + 2:
            clean = clean[: -len(suffix)]
            break
    clean = clean.strip("-./")
    return clean or None


def _is_suspicious_code(value: Any) -> bool:
    text = _sanitize_code_value(value)
    if not text:
        return False
    return any(
        str(value or "").upper().endswith(suffix)
        for suffix in ("MARCA", "MATERIAL", "PESO", "QUANTIDADE", "ATENCAO")
    )


def _extract_signals_from_description(text: Any) -> Dict[str, str]:
    raw = _as_text(text, max_len=12000)
    if not raw:
        return {}

    compact = re.sub(r"\s+", " ", raw)
    normalized = unicodedata.normalize("NFKD", compact).encode("ascii", "ignore").decode("ascii")
    normalized_low = normalized.lower()
    extracted: Dict[str, str] = {}

    code_match = re.search(
        r"\b(?:codigo(?:\s+original)?|referencia(?:\s+original)?)\s*[:\-]\s*([A-Za-z0-9./-]{2,40}?)(?=\s*(?:marca|material|peso|quantidade|$|[;,.]))",
        normalized_low,
        flags=re.IGNORECASE,
    )
    if code_match:
        extracted["codigo_original"] = code_match.group(1).strip().upper()

    material_match = re.search(
        r"\bmaterial\s*[:\-]\s*(.+?)(?=\b(?:peso|quantidade|atencao|marca|codigo|referencia)\b|$)",
        normalized_low,
        flags=re.IGNORECASE,
    )
    if material_match:
        material_value = material_match.group(1).strip(" -:;,.")
        if material_value:
            extracted["material"] = material_value

    return extracted


_PLACEHOLDER_HINTS = {
    "n a",
    "na",
    "none",
    "null",
    "sem descricao",
    "sem informacao",
    "nao informado",
    "nao informada",
    "todos",
    "todas",
    "geral",
}
_PART_NAME_HINTS = (
    "paralama",
    "estribo",
    "suporte",
    "defletor",
    "ponteira",
    "cobertura",
    "mascara",
    "revestimento",
    "pisante",
    "coluna",
    "porta",
    "grade",
    "farol",
    "lateral",
    "painel",
)
_APPLICATION_HINTS = (
    "actros",
    "cargo",
    "constellation",
    "scania",
    "randon",
    "volks",
    "mercedes",
    "ford",
    "iveco",
    "volvo",
    "man",
    "dianteiro",
    "traseiro",
)


def _contains_part_hint(text_folded: str) -> bool:
    return any(hint in text_folded for hint in _PART_NAME_HINTS)


def _looks_like_application_only(value: Any) -> bool:
    text = _as_text(value, max_len=500)
    if not text:
        return False
    folded = _fold_text(text)
    if not folded:
        return False
    has_application_hint = any(hint in folded for hint in _APPLICATION_HINTS)
    has_year = bool(re.search(r"\b(19|20)\d{2}\b", folded))
    has_range = bool(re.search(r"\b\d{4}\s*-\s*\d{4}\b", text))
    few_words = len(folded.split()) <= 10
    return has_application_hint and (has_year or has_range) and few_words and not _contains_part_hint(folded)


def _is_weak_existing_field(field_name: str, value: Any) -> bool:
    text = _as_text(value, max_len=2500)
    if not text:
        return True
    folded = _fold_text(text)
    if not folded:
        return True
    if folded in _PLACEHOLDER_HINTS:
        return True

    if field_name == "nome_chat_api":
        if len(folded) < 8:
            return True
        if re.fullmatch(r"[0-9./\-\s]+", text):
            return True
        if _looks_like_application_only(text):
            return True
        return False

    if field_name in {"descricao_original", "descricao_chat_api"}:
        if len(folded) < 20:
            return True
        if _looks_like_application_only(text):
            return True
        if "anotac" in folded or "observac" in folded:
            return True
        return False

    if field_name == "marca":
        if len(folded) < 3:
            return True
        if folded in {"sm", "s m", "sem marca", "generico"}:
            return True
        return False

    return False


def _is_weak_dynamic_value(attr_key: str, value: Any) -> bool:
    text = _as_text(value, max_len=1500)
    if not text:
        return True
    folded = _fold_text(text)
    if not folded:
        return True
    if folded in _PLACEHOLDER_HINTS:
        return True

    attr_norm = _fold_text(attr_key)
    if ("descr" in attr_norm or attr_norm == "titulo") and len(folded) < 12:
        return True
    if "descr" in attr_norm and _looks_like_application_only(text):
        return True
    if ("id" == attr_norm or "codigo" in attr_norm) and _is_suspicious_code(text):
        return True
    if ("aplic" in attr_norm or "application" in attr_norm) and folded in {"todos", "todas", "geral"}:
        return True
    if "material" in attr_norm and folded in {"todos", "todas", "geral"}:
        return True
    return False


_RELEVANCE_STOPWORDS = {
    "de",
    "da",
    "do",
    "das",
    "dos",
    "para",
    "com",
    "sem",
    "em",
    "ate",
    "até",
    "todos",
    "todas",
    "lado",
    "peca",
    "peça",
    "pecas",
    "peças",
}


def _tokens_for_relevance(value: Any) -> List[str]:
    base = _fold_text(value)
    if not base:
        return []
    tokens = [t for t in base.split(" ") if len(t) >= 3 and t not in _RELEVANCE_STOPWORDS]
    return tokens


def _extract_code_tokens(*values: Any) -> List[str]:
    combined = " ".join(str(v or "") for v in values)
    upper = unicodedata.normalize("NFKD", combined).encode("ascii", "ignore").decode("ascii").upper()
    tokens = re.findall(r"[A-Z0-9][A-Z0-9./-]{3,}", upper)
    cleaned = []
    for token in tokens:
        tok = token.strip("./-")
        if len(tok) < 4:
            continue
        if re.fullmatch(r"[A-Z]+", tok):
            continue
        cleaned.append(tok)
    return list(dict.fromkeys(cleaned))


def _is_source_relevant_for_product(
    db_produto_obj: models.Produto,
    *,
    source_name: Any,
    source_desc: Any,
    source_url: str,
) -> bool:
    ref_parts = [db_produto_obj.nome_base, db_produto_obj.marca, db_produto_obj.sku, db_produto_obj.ean]
    if isinstance(db_produto_obj.dados_brutos_web, dict):
        ref_parts.append(db_produto_obj.dados_brutos_web.get("codigo_original"))
        ref_parts.append(db_produto_obj.dados_brutos_web.get("sku_original"))

    ref_tokens = _tokens_for_relevance(" ".join(str(x or "") for x in ref_parts))
    if not ref_tokens:
        return True

    source_text = " ".join(
        str(x or "") for x in [source_name, source_desc, source_url]
    )
    src_tokens = set(_tokens_for_relevance(source_text))
    overlap = [t for t in ref_tokens if t in src_tokens]

    code_tokens = _extract_code_tokens(*ref_parts)
    src_compact = re.sub(r"[^A-Z0-9]", "", str(source_text).upper())
    code_hit = any(re.sub(r"[^A-Z0-9]", "", token) in src_compact for token in code_tokens)

    if code_tokens and not code_hit and len(overlap) < 3:
        return False

    if len(ref_tokens) <= 4:
        return bool(overlap) or code_hit

    return len(overlap) >= 2 or code_hit


_URL_TRACKING_HINTS = (
    "ad_domain=",
    "ad_provider=",
    "click_metadata=",
    "msclkid=",
    "utm_",
    "vqd=",
)
_URL_HOST_LOW_SIGNAL = (
    "duckduckgo.com",
    "bing.com",
    "google.com",
    "facebook.com",
    "instagram.com",
    "linkedin.com",
    "youtube.com",
    "tiktok.com",
)
_URL_HOST_HIGH_SIGNAL = (
    "mercadolivre.",
    "amazon.",
    "shopee.",
    "magazineluiza.",
    "casasbahia.",
    "jocar.",
    "dipecarr.",
    "dana.",
    "jacto",
    "minner.",
    "mundodocaminhao.",
    "essentra",
)


def _extrair_dominio_fornecedor(site_url: Any) -> str:
    try:
        parsed = urlparse(str(site_url or "").strip())
        if parsed.netloc:
            return parsed.netloc.lower()
        raw = str(site_url or "").strip().lower()
        return raw.split("//")[-1].split("/")[0]
    except Exception:
        return ""


def _score_url_para_produto(
    db_produto_obj: models.Produto,
    candidate_url: str,
    fornecedor_domain: str = "",
) -> int:
    parsed = urlparse(str(candidate_url or "").strip())
    host = (parsed.netloc or "").lower()
    path = (parsed.path or "").lower()
    query = (parsed.query or "").lower()
    if not host:
        return -999

    score = 0
    if fornecedor_domain and fornecedor_domain in host:
        score += 45
    if any(h in host for h in _URL_HOST_HIGH_SIGNAL):
        score += 18
    if any(h in host for h in _URL_HOST_LOW_SIGNAL):
        score -= 20
    if path.endswith(".pdf"):
        score -= 10
    if path in {"/y.js", "/redirect", "/search"}:
        score -= 40
    if any(h in query for h in _URL_TRACKING_HINTS):
        score -= 35
    if len(query) > 280:
        score -= 10

    ref_text = " ".join(
        str(x or "")
        for x in [db_produto_obj.nome_base, db_produto_obj.sku, db_produto_obj.ean, db_produto_obj.marca]
    )
    ref_tokens = set(_tokens_for_relevance(ref_text))
    src_tokens = set(_tokens_for_relevance(f"{host} {path} {query}"))
    overlap = len(ref_tokens.intersection(src_tokens))
    score += min(overlap * 6, 24)

    return score


def _priorizar_urls_para_enriquecimento(
    db_produto_obj: models.Produto,
    urls_candidatas: List[str],
    fornecedor_domain: str = "",
    max_urls: int = 4,
) -> Tuple[List[str], List[Tuple[str, int]]]:
    deduped = [u for u in dict.fromkeys(urls_candidatas or []) if u]
    scored: List[Tuple[str, int]] = []
    for url in deduped:
        score = _score_url_para_produto(db_produto_obj, url, fornecedor_domain=fornecedor_domain)
        if score <= -25:
            continue
        scored.append((url, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return [url for url, _ in scored[: max(1, max_urls)]], scored


_LOW_QUALITY_CONTENT_MARKERS = (
    "errors edgesuite net",
    "access denied",
    "attention required",
    "captcha",
    "temporarily unavailable",
    "service unavailable",
    "bad request",
)


def _is_meaningful_extracted_text(value: Any) -> bool:
    text = _fold_text(value)
    if not text:
        return False
    if re.search(r"\breference\s*#?\s*[0-9a-z.]{6,}\b", text):
        return False
    if any(marker in text for marker in _LOW_QUALITY_CONTENT_MARKERS):
        return False
    if len(text) < 80:
        return False
    words = [w for w in text.split() if len(w) >= 3]
    if len(words) < 12:
        return False
    letters = sum(1 for ch in text if ch.isalpha())
    return letters >= 50


def _metadata_has_minimum_signal(metadata: Dict[str, Any]) -> bool:
    if not metadata:
        return False
    nome = _as_text(metadata.get("nome"))
    descricao = _as_text(metadata.get("descricao_curta"))
    sku = _as_text(metadata.get("sku"))
    marca = _as_text(metadata.get("marca"))
    image = _as_text(metadata.get("imagem_url"))
    if not any([nome, descricao, sku, marca, image]):
        return False
    joined = " ".join(part for part in [nome, descricao] if part)
    if joined and any(marker in _fold_text(joined) for marker in _LOW_QUALITY_CONTENT_MARKERS):
        return False
    if nome and len(nome) >= 8:
        return True
    return bool(sku and (descricao or marca or image))


def _build_payload_enriquecimento_visivel(
    db_produto_obj: models.Produto,
    dados_extraidos_agregados: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[str], List[str]]:
    """Converte dados extraidos da web em campos visiveis no modal de produto."""
    update_fields: Dict[str, Any] = {}
    notes: List[str] = []
    ignored_notes: List[str] = []

    nome_web = _as_text(
        _first_non_empty(
            dados_extraidos_agregados.get("nome_sugerido_seo"),
            dados_extraidos_agregados.get("nome"),
        ),
        max_len=255,
    )
    descricao_web = _as_text(
        _first_non_empty(
            dados_extraidos_agregados.get("descricao_detalhada_seo"),
            dados_extraidos_agregados.get("descricao_curta"),
            dados_extraidos_agregados.get("texto_relevante_coletado"),
        ),
        max_len=10000,
    )
    imagem_url_web = _as_text(dados_extraidos_agregados.get("imagem_url"), max_len=2000)
    marca_web = _as_text(dados_extraidos_agregados.get("marca"), max_len=100)
    sku_web = _as_text(dados_extraidos_agregados.get("sku"), max_len=100)
    preco_web = _parse_price(dados_extraidos_agregados.get("preco"))
    disponibilidade_web = _as_text(dados_extraidos_agregados.get("disponibilidade"), max_len=120)
    moeda_preco_web = _as_text(dados_extraidos_agregados.get("moeda_preco"), max_len=12)

    # Extrai pistas tecnicas adicionais da descricao quando possivel.
    extracted_signals = _extract_signals_from_description(descricao_web)
    for key, value in extracted_signals.items():
        if _is_empty(dados_extraidos_agregados.get(key)):
            dados_extraidos_agregados[key] = value

    codigo_original_web = _sanitize_code_value(
        _first_non_empty(
            dados_extraidos_agregados.get("codigo_original"),
            dados_extraidos_agregados.get("sku_original"),
            sku_web,
        )
    )
    if codigo_original_web and dados_extraidos_agregados.get("codigo_original") != codigo_original_web:
        dados_extraidos_agregados["codigo_original"] = codigo_original_web
    material_web = _as_text(dados_extraidos_agregados.get("material"), max_len=120)
    aplicacao_web = _as_text(dados_extraidos_agregados.get("aplicacao"), max_len=400)

    def _apply_if_empty_or_weak(
        field_name: str,
        current_value: Any,
        new_value: Any,
        *,
        allow_replace_weak: bool = False,
    ) -> None:
        if _is_empty(new_value):
            return
        if _is_empty(current_value):
            update_fields[field_name] = new_value
            notes.append(field_name)
        elif (
            allow_replace_weak
            and _is_weak_existing_field(field_name, current_value)
            and not _is_weak_existing_field(field_name, new_value)
        ):
            update_fields[field_name] = new_value
            notes.append(f"{field_name}:substituido_valor_fraco")
        else:
            ignored_notes.append(f"{field_name}:mantido_valor_existente")

    _apply_if_empty_or_weak(
        "nome_chat_api",
        db_produto_obj.nome_chat_api,
        nome_web,
        allow_replace_weak=True,
    )
    _apply_if_empty_or_weak(
        "descricao_original",
        db_produto_obj.descricao_original,
        descricao_web,
        allow_replace_weak=True,
    )
    _apply_if_empty_or_weak(
        "descricao_chat_api",
        db_produto_obj.descricao_chat_api,
        descricao_web,
        allow_replace_weak=True,
    )
    _apply_if_empty_or_weak(
        "imagem_principal_url",
        db_produto_obj.imagem_principal_url,
        imagem_url_web,
    )
    _apply_if_empty_or_weak(
        "marca",
        db_produto_obj.marca,
        marca_web,
        allow_replace_weak=True,
    )
    # Evita conflitos de unique com SKU atual: preenche apenas quando vazio.
    _apply_if_empty_or_weak("sku", db_produto_obj.sku, sku_web)

    if preco_web is not None:
        if db_produto_obj.preco_venda is None:
            update_fields["preco_venda"] = preco_web
            notes.append("preco_venda")
        else:
            ignored_notes.append("preco_venda:mantido_valor_existente")

    dynamic_current = (
        dict(db_produto_obj.dynamic_attributes)
        if isinstance(db_produto_obj.dynamic_attributes, dict)
        else {}
    )
    dynamic_before = dict(dynamic_current)

    normalized_key_to_real: Dict[str, str] = {}
    for current_key in dynamic_current.keys():
        normalized_key_to_real[_fold_text(current_key)] = current_key

    if db_produto_obj.product_type and db_produto_obj.product_type.attribute_templates:
        for tpl in db_produto_obj.product_type.attribute_templates:
            attr_key = getattr(tpl, "attribute_key", None)
            if attr_key:
                normalized_key_to_real[_fold_text(attr_key)] = attr_key
            # Labels do template costumam representar o nome funcional (ex.: "ID"),
            # mesmo quando a chave técnica é sufixada (ex.: "id_auto").
            label = getattr(tpl, "label", None)
            if attr_key and label:
                normalized_key_to_real[_fold_text(label)] = attr_key

    dynamic_ignored: List[str] = []

    def _set_dynamic_if_empty(
        candidates: List[str],
        value: Any,
        *,
        allow_replace_suspicious: bool = False,
        allow_replace_weak: bool = False,
    ) -> Optional[str]:
        text_value = _as_text(value)
        # Se o valor novo vier vazio, tenta reaproveitar aliases antigos já existentes
        # (ex.: "titulo" -> "titulo_auto") para não perder dados em migrações.
        if not text_value:
            for candidate in candidates:
                candidate_norm = _fold_text(candidate)
                for current_key, current_val in dynamic_current.items():
                    current_norm = _fold_text(current_key)
                    if candidate_norm == current_norm or candidate_norm in current_norm:
                        maybe_value = _as_text(current_val)
                        if maybe_value:
                            text_value = maybe_value
                            break
                if text_value:
                    break
        if not text_value:
            return None
        target_key = None
        for candidate in candidates:
            candidate_norm = _fold_text(candidate)
            if candidate_norm in normalized_key_to_real:
                target_key = normalized_key_to_real[candidate_norm]
                break
            # Fallback: compatibiliza aliases com chaves/labels estendidas
            # (ex.: "id" -> "id auto", "descricao" -> "desc auto").
            for known_norm, known_key in normalized_key_to_real.items():
                if not known_norm:
                    continue
                if candidate_norm and (
                    candidate_norm in known_norm
                    or known_norm in candidate_norm
                    or (candidate_norm == "descricao" and "desc" in known_norm)
                ):
                    target_key = known_key
                    break
            if target_key:
                break
        if not target_key:
            target_key = candidates[0]
        if _is_empty(dynamic_current.get(target_key)):
            dynamic_current[target_key] = text_value
            return target_key
        if allow_replace_suspicious and _is_suspicious_code(dynamic_current.get(target_key)):
            dynamic_current[target_key] = text_value
            return target_key
        if (
            allow_replace_weak
            and _is_weak_dynamic_value(target_key, dynamic_current.get(target_key))
            and not _is_weak_dynamic_value(target_key, text_value)
        ):
            dynamic_current[target_key] = text_value
            return target_key
        dynamic_ignored.append(str(target_key))
        return None

    dynamic_filled: List[str] = []
    for aliases, value in [
        (["titulo", "title", "nome"], nome_web),
        (["descricao", "description", "desc"], descricao_web),
        (
            [
                "id",
                "codigo_original",
                "codigo",
                "cod",
                "referencia_original",
                "referencia",
                "ref",
            ],
            codigo_original_web,
        ),
        (["material"], material_web),
        (["aplicacao", "application"], aplicacao_web),
        (["disponibilidade"], disponibilidade_web),
        (["moeda_preco", "moeda"], moeda_preco_web),
        (["marca"], marca_web),
    ]:
        target = _set_dynamic_if_empty(
            aliases,
            value,
            allow_replace_suspicious=(aliases[0] in {"id", "codigo_original"}),
            allow_replace_weak=(aliases[0] in {"titulo", "descricao", "material", "aplicacao", "marca"}),
        )
        if target:
            dynamic_filled.append(target)

    specs = dados_extraidos_agregados.get("especificacoes_tecnicas_dict")
    if isinstance(specs, dict):
        for key, value in specs.items():
            if _is_empty(key):
                continue
            target = _set_dynamic_if_empty([str(key)], value)
            if target:
                dynamic_filled.append(target)

    if dynamic_current != dynamic_before:
        update_fields["dynamic_attributes"] = dynamic_current
        if dynamic_filled:
            unique_dynamic = []
            seen = set()
            for item in dynamic_filled:
                if item not in seen:
                    seen.add(item)
                    unique_dynamic.append(item)
            notes.append(f"dynamic_attributes={','.join(unique_dynamic)}")
    if dynamic_ignored:
        unique_ignored = []
        seen_ignored = set()
        for item in dynamic_ignored:
            if item not in seen_ignored:
                seen_ignored.add(item)
                unique_ignored.append(item)
        ignored_notes.append(f"dynamic_attributes={','.join(unique_ignored)}")

    return update_fields, notes, ignored_notes

async def _tarefa_enriquecer_produto_web(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None
):
    db: Optional[Session] = None
    log_mensagens: List[str] = [
        f"INICIANDO tarefa de enriquecimento web para produto ID: {produto_id}."
    ]
    
    db_produto_obj: Optional[models.Produto] = None
    status_original_do_produto_no_inicio_da_tarefa: models.StatusEnriquecimentoEnum = (
        models.StatusEnriquecimentoEnum.PENDENTE
    )

    try:
        db = db_session_factory()
        query = db.query(models.Produto).filter(models.Produto.id == produto_id)
        engine = db.get_bind()
        dialect_name = engine.dialect.name if engine and engine.dialect else None
        if dialect_name == "sqlite":
            db_produto_obj = query.first()
        else:
            db_produto_obj = query.with_for_update().first()
        if not db_produto_obj:
            log_mensagens.append(f"ERRO FATAL PRECOCE: Produto ID {produto_id} não encontrado.")
            logger.error(log_mensagens[-1])
            return
        
        status_original_do_produto_no_inicio_da_tarefa = db_produto_obj.status_enriquecimento_web
        # Não mudamos o status para EM_PROGRESSO aqui ainda.

    except SQLAlchemyError as e_sql_load:
        log_mensagens.append(
            f"ERRO SQL ao carregar produto ID {produto_id}: {e_sql_load}"
        )
        logger.error(log_mensagens[-1])
        return

    # Esta será a variável que controlará o status a ser salvo no final.
    # Inicializa com o status que o produto tinha antes da tarefa começar,
    # ou FALHOU se algo der muito errado antes mesmo de verificarmos as APIs.
    status_para_salvar_no_final: models.StatusEnriquecimentoEnum = status_original_do_produto_no_inicio_da_tarefa
    
    # Se o status original já era EM_PROGRESSO por algum motivo (ex: tarefa anterior falhou ao limpar),
    # é melhor considerá-lo como PENDENTE para esta nova execução ou FALHOU para evitar loops.
    # Para simplificar, se estava EM_PROGRESSO, vamos reverter para PENDENTE como base para esta tentativa.
    if status_original_do_produto_no_inicio_da_tarefa == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
        log_mensagens.append(f"AVISO: Produto {produto_id} encontrado como EM_PROGRESSO no início. Considerando como PENDENTE para esta execução.")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.PENDENTE


    dados_extraidos_agregados: Dict[str, Any] = db_produto_obj.dados_brutos_web.copy() if isinstance(db_produto_obj.dados_brutos_web, dict) else {}
    
    try:
        user = crud_users.get_user(db, user_id)
        if not user:
            log_mensagens.append(f"ERRO FATAL: Usuário ID {user_id} não encontrado.")
            # Define um status de falha se o usuário não for encontrado.
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
            return # O finally cuidará da atualização do produto

        # Verifica configurações críticas ANTES de mudar para EM_PROGRESSO
        openai_user_configurada = bool(user.chave_openai_pessoal)
        openai_system_configurada = bool(settings.OPENAI_API_KEY)
        openai_api_configurada = bool(openai_user_configurada or openai_system_configurada)
        google_api_configurada = bool(settings.GOOGLE_CSE_API_KEY and settings.GOOGLE_CSE_ID)
        busca_publica_fallback = bool(getattr(web_extractor, "busca_publica_disponivel", lambda: False)())
        busca_web_disponivel = google_api_configurada or busca_publica_fallback
        log_mensagens.append(
            "Config API: "
            f"openai_user={'sim' if openai_user_configurada else 'nao'}, "
            f"openai_sistema={'sim' if openai_system_configurada else 'nao'}, "
            f"google_cse={'sim' if google_api_configurada else 'nao'}, "
            f"busca_publica={'sim' if busca_publica_fallback else 'nao'}."
        )

        # Sem OpenAI e sem mecanismo de busca web, não há como enriquecer.
        if not openai_api_configurada and not busca_web_disponivel:
            log_mensagens.append(
                "AVISO CRITICO: Sem OpenAI e sem mecanismo de busca web disponivel. "
                "Configure OPENAI_API_KEY (ou chave pessoal do usuário) e/ou Google CSE."
            )
            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            # Opcional: Registrar uso da IA para falha de configuração
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A",
                    resposta_ia="Falha: Configurações de API externas ausentes.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            return # Vai para o finally para salvar este status

        if not google_api_configurada and busca_publica_fallback:
            log_mensagens.append(
                "Google CSE não configurado. Usando fallback de busca pública sem API key."
            )

        # Se especificamente a OpenAI não está configurada, mas a Google pode estar.
        # O enriquecimento LLM não será possível, mas a busca e extração de metadados sim.
        if not openai_api_configurada:
            log_mensagens.append("AVISO: Chave API OpenAI não configurada. Enriquecimento via LLM será pulado. Outras coletas de dados (Google, metadados) tentarão prosseguir.")
            # Não definimos status_para_salvar_no_final como FALHA_CONFIGURACAO_API_EXTERNA ainda,
            # pois a busca Google e extração de metadados podem funcionar.
            # O status final dependerá se essas outras etapas coletam algo.
            crud.create_registro_uso_ia(
                db=db,
                registro_uso=schemas.RegistroUsoIACreate(
                    user_id=user.id,
                    produto_id=produto_id,
                    tipo_acao=models.TipoAcaoEnum.ENRIQUECIMENTO_WEB_PRODUTO,
                    modelo_ia="N/A",
                    provedor_ia=None,
                    prompt_utilizado="N/A - Config OpenAI pendente para LLM",
                    resposta_ia="Falha Parcial: Chave API OpenAI não configurada para LLM.",
                    creditos_consumidos=0,
                    status="FALHA",
                ),
            )
            # A tarefa continua para tentar coletar dados de outras fontes

        # ----- AGORA, definimos o status para EM_PROGRESSO no banco -----
        # Isso sinaliza que as verificações iniciais passaram e o trabalho real começou.
        log_mensagens.append(f"Definindo status do produto ID {produto_id} para EM_PROGRESSO no banco.")
        db_produto_obj.status_enriquecimento_web = models.StatusEnriquecimentoEnum.EM_PROGRESSO
        db_produto_obj.log_enriquecimento_web = {"historico_mensagens": log_mensagens} # Salva o log inicial
        db.commit()
        db.refresh(db_produto_obj)
        
        # O status_para_salvar_no_final será o que resultar do processamento.
        # Se tudo correr bem, será CONCLUIDO_SUCESSO. Se houver problemas, será outro.
        # Por default, se nada mudar, consideramos uma falha genérica ao final do try.
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        
        # ----- Início do Processamento Principal -----
        query_parts = [db_produto_obj.nome_base]
        if db_produto_obj.sku:
            query_parts.append(db_produto_obj.sku)
        ean_raw = str(db_produto_obj.ean or "").strip()
        ean_digits = re.sub(r"\D", "", ean_raw)
        if ean_digits and 8 <= len(ean_digits) <= 14:
            query_parts.append(ean_digits)

        query_base = " ".join([str(part).strip() for part in query_parts if str(part).strip()])

        query_candidates: List[str] = []
        if termos_busca_override:
            query_candidates.append(termos_busca_override.strip())
        else:
            nome_base_clean = str(db_produto_obj.nome_base or "").strip()
            fornecedor_nome = (
                str(db_produto_obj.fornecedor.nome or "").strip()
                if db_produto_obj.fornecedor and db_produto_obj.fornecedor.nome
                else ""
            )
            codigo_original = ""
            if isinstance(db_produto_obj.dados_brutos_web, dict):
                codigo_original = str(
                    db_produto_obj.dados_brutos_web.get("codigo_original")
                    or db_produto_obj.dados_brutos_web.get("sku_original")
                    or ""
                ).strip()

            if query_base:
                query_candidates.append(f"{query_base} especificacoes tecnicas detalhadas")
                query_candidates.append(f"{query_base} ficha tecnica")
            if nome_base_clean:
                query_candidates.append(f"{nome_base_clean} especificacoes tecnicas")
                query_candidates.append(nome_base_clean)
                if fornecedor_nome:
                    query_candidates.append(f"{nome_base_clean} {fornecedor_nome}")
                if codigo_original:
                    query_candidates.append(f"{nome_base_clean} {codigo_original}")
                    query_candidates.append(codigo_original)

        # Deduplicar preservando ordem.
        query_candidates = [q for q in dict.fromkeys(q for q in query_candidates if q)]

        urls_encontradas_brutas: List[str] = []
        if busca_web_disponivel:
            for query in query_candidates[:4]:
                log_mensagens.append(f"Termo de busca web: '{query}'")
                urls_tentativa = await web_extractor.buscar_urls_google(query=query, num_results=3)
                log_mensagens.append(
                    f"Busca web retornou {len(urls_tentativa)} URL(s) para '{query}'."
                )
                if urls_tentativa:
                    urls_encontradas_brutas = urls_tentativa
                    break

            if not urls_encontradas_brutas:
                if query_candidates:
                    log_mensagens.append(
                        f"Nenhuma URL encontrada para os termos testados ({len(query_candidates)} tentativa(s))."
                    )
                else:
                    log_mensagens.append(
                        "Nenhum termo de busca valido pode ser montado para este produto."
                    )
        else:
            log_mensagens.append("Busca web pulada: nenhum provedor de busca disponivel.")
        fornecedor_domain = _extrair_dominio_fornecedor(
            db_produto_obj.fornecedor.site_url
            if db_produto_obj.fornecedor and db_produto_obj.fornecedor.site_url
            else ""
        )
        urls_a_processar, urls_scored = _priorizar_urls_para_enriquecimento(
            db_produto_obj=db_produto_obj,
            urls_candidatas=urls_encontradas_brutas,
            fornecedor_domain=fornecedor_domain,
            max_urls=4,
        )
        if urls_scored:
            ranking_log = ", ".join([f"{score}:{url}" for url, score in urls_scored[:6]])
            log_mensagens.append(f"Ranking de URLs por relevância: {ranking_log}")
        elif urls_encontradas_brutas:
            log_mensagens.append(
                "URLs encontradas, mas descartadas por baixa relevância/sinal de tracking."
            )
        dados_coletados_de_fontes_web = False # Flag para saber se algo foi coletado da web

        if not urls_a_processar and not busca_web_disponivel:
            log_mensagens.append("Nenhuma URL para processar (busca web indisponível e sem override).")
            # Sem busca web, o LLM ainda pode tentar com dados brutos.
        elif not urls_a_processar and busca_web_disponivel:
            log_mensagens.append("Nenhuma URL encontrada ou selecionada para processar.")
            # Mesmo sem URLs, o LLM ainda pode tentar com dados brutos.

        for i, url_processar in enumerate(urls_a_processar):
            log_mensagens.append(f"Processando URL {i+1}/{len(urls_a_processar)}: {url_processar}")
            html_content = await web_extractor.coletar_conteudo_pagina_playwright(url_processar)
            if not html_content:
                log_mensagens.append(f"Não foi possível obter conteúdo HTML da URL: {url_processar}")
                continue # Tenta a próxima URL

            texto_principal = web_extractor.extrair_texto_principal_com_trafilatura(html_content)
            metadados_extruct = web_extractor.extrair_metadados_estruturados(html_content, url_processar)
            metadados_normalizados_pagina = web_extractor._normalizar_dados_de_metadados(metadados_extruct)

            if texto_principal and not _is_meaningful_extracted_text(texto_principal):
                log_mensagens.append(
                    f"Texto descartado por baixa qualidade/erro de pagina para URL: {url_processar}"
                )
                texto_principal = None

            if metadados_normalizados_pagina and not _metadata_has_minimum_signal(metadados_normalizados_pagina):
                log_mensagens.append(
                    f"Metadados descartados por baixa qualidade para URL: {url_processar}"
                )
                metadados_normalizados_pagina = {}

            nome_fonte = metadados_normalizados_pagina.get("nome")
            descricao_fonte = metadados_normalizados_pagina.get("descricao_curta") or (texto_principal[:600] if texto_principal else "")
            if not _is_source_relevant_for_product(
                db_produto_obj,
                source_name=nome_fonte,
                source_desc=descricao_fonte,
                source_url=url_processar,
            ):
                log_mensagens.append(
                    f"URL descartada por baixa relevancia para o produto: {url_processar}"
                )
                continue

            if metadados_normalizados_pagina:
                log_mensagens.append(f"Metadados normalizados extraídos da URL {url_processar}: {json.dumps(metadados_normalizados_pagina, indent=2, ensure_ascii=False)}")
                dados_extraidos_agregados.update(metadados_normalizados_pagina) # Atualiza com prioridade para novos dados
                dados_coletados_de_fontes_web = True
            
            if texto_principal:
                log_mensagens.append(f"Texto principal extraído da URL {url_processar} (primeiros 300 chars): {texto_principal[:300]}")
                # Guarda o texto da primeira página processada com sucesso para possível uso pelo LLM
                if "texto_relevante_coletado" not in dados_extraidos_agregados:
                    dados_extraidos_agregados["texto_relevante_coletado"] = texto_principal
                dados_coletados_de_fontes_web = True
            
            # Se já temos dados suficientes de metadados e texto, podemos parar antes
            if metadados_normalizados_pagina.get("nome") and metadados_normalizados_pagina.get("descricao_curta"):
                log_mensagens.append(f"Dados chave (nome, descrição) encontrados em {url_processar}. Considerando suficiente desta URL.")
                break 
        
        # Etapa de enriquecimento com LLM, se configurado
        if openai_api_configurada:
            campos_desejados_llm = [
                "nome_sugerido_seo", "descricao_detalhada_seo", "lista_caracteristicas_beneficios_bullets",
                "especificacoes_tecnicas_dict", "palavras_chave_seo_relevantes_lista"
            ]
            texto_para_llm = dados_extraidos_agregados.get("texto_relevante_coletado") # Usa o texto coletado
            if not texto_para_llm and isinstance(db_produto_obj.dados_brutos_web, dict): # Fallback para dados brutos se nenhum texto web
                texto_para_llm = json.dumps(db_produto_obj.dados_brutos_web.get("dados_brutos_originais", db_produto_obj.dados_brutos_web), ensure_ascii=False)
            
            metadados_para_llm = {k: v for k, v in dados_extraidos_agregados.items() if k != "texto_relevante_coletado"}

            if texto_para_llm or metadados_para_llm:
                log_mensagens.append("Iniciando extração/geração com LLM.")
                dados_do_llm = await web_extractor.extrair_dados_produto_com_llm(
                    texto_pagina=texto_para_llm,
                    metadados_normalizados=metadados_para_llm,
                    campos_desejados=campos_desejados_llm,
                    produto_nome_base=db_produto_obj.nome_base,
                    user=user
                )
                if dados_do_llm:
                    log_mensagens.append(f"Dados recebidos do LLM: {json.dumps(dados_do_llm, indent=2, ensure_ascii=False)}")
                    if "erro_llm" in dados_do_llm or "erro_llm_inesperado" in dados_do_llm:
                        log_mensagens.append(f"ERRO do LLM: {dados_do_llm.get('erro_llm') or dados_do_llm.get('erro_llm_inesperado')}")
                        # Não necessariamente uma falha total do enriquecimento se outros dados foram coletados
                        if not dados_coletados_de_fontes_web: # Se LLM era a única esperança e falhou
                            status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_API_EXTERNA
                    else:
                        dados_extraidos_agregados.update(dados_do_llm)
                        dados_coletados_de_fontes_web = True # Se o LLM produziu algo, consideramos coleta
                else:
                    log_mensagens.append("LLM não retornou dados ou ocorreu erro não capturado explicitamente.")
            else:
                log_mensagens.append("Nenhum texto ou metadado suficiente para enviar ao LLM.")
        else: # openai_api_configurada é False
            log_mensagens.append("LLM não foi chamado pois a API OpenAI não está configurada.")

        # Determinação do status final com base no que foi coletado
        if status_para_salvar_no_final == models.StatusEnriquecimentoEnum.EM_PROGRESSO or status_para_salvar_no_final == models.StatusEnriquecimentoEnum.FALHOU : # Se não houve falha crítica antes
            if dados_coletados_de_fontes_web:
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.CONCLUIDO_SUCESSO
                if not openai_api_configurada: # Se coletou dados web mas LLM não rodou por config
                    status_para_salvar_no_final = models.StatusEnriquecimentoEnum.CONCLUIDO_COM_DADOS_PARCIAIS # Ou um novo status como "CONCLUIDO_SEM_LLM"
            elif urls_a_processar: # Tentou processar URLs mas nada foi efetivamente coletado
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            elif busca_web_disponivel and not urls_a_processar:
                # Busca disponivel, mas nenhum link elegivel foi retornado.
                status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            elif not busca_web_disponivel and not openai_api_configurada: # Se nenhuma API/fallback estava ativa e não havia URLs override
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHA_CONFIGURACAO_API_EXTERNA
            elif not busca_web_disponivel and openai_api_configurada and not dados_coletados_de_fontes_web: # Busca off, OpenAI on mas não produziu nada
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.NENHUMA_FONTE_ENCONTRADA
            else: # Caso geral se não se encaixar acima, mas o processo "correu"
                 status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU

        log_mensagens.append(f"Processamento principal concluído. Status determinado internamente: {status_para_salvar_no_final.value}")

    except Exception as e_main_try:
        import traceback
        error_full = traceback.format_exc()
        log_mensagens.append(f"ERRO CRITICO INESPERADO NO PROCESSO: {str(e_main_try)}. Trace: {error_full}")
        status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU 
        logger.error(
            "ERRO CRITICO INESPERADO na tarefa de enriquecimento para produto ID %s: %s",
            produto_id,
            error_full,
        )
    
    finally:
        if db_produto_obj:
            try:
                # O status atual no db_produto_obj pode ser EM_PROGRESSO se chegou a commitar.
                # status_para_salvar_no_final contém o status que REALMENTE deve ser salvo.
                
                # Se o status no banco ainda é EM_PROGRESSO (porque foi commitado),
                # mas o status_para_salvar_no_final também ficou EM_PROGRESSO (indicando que talvez a lógica de determinação final não pegou todos os casos),
                # então forçamos para FALHOU para não deixar o produto preso em EM_PROGRESSO.
                if db_produto_obj.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO and \
                   status_para_salvar_no_final == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
                    status_para_salvar_no_final = models.StatusEnriquecimentoEnum.FALHOU
                    log_mensagens.append("ALERTA FINALLY: Status final e do DB eram EM_PROGRESSO, forçando para FALHOU.")
                
                status_valor_str = status_para_salvar_no_final.value

                (
                    campos_visiveis_update,
                    notas_campos,
                    notas_ignoradas,
                ) = _build_payload_enriquecimento_visivel(
                    db_produto_obj=db_produto_obj,
                    dados_extraidos_agregados=dados_extraidos_agregados,
                )
                if notas_campos:
                    log_mensagens.append(
                        "Campos preenchidos no produto a partir do enriquecimento: "
                        + ", ".join(notas_campos)
                    )
                else:
                    log_mensagens.append(
                        "Enriquecimento finalizado sem novos campos visiveis para preencher no produto."
                    )
                if notas_ignoradas:
                    log_mensagens.append(
                        "Campos ignorados (mantidos os valores atuais): "
                        + ", ".join(notas_ignoradas)
                    )

                resumo_aplicacao = {
                    "aplicados": notas_campos,
                    "ignorados": notas_ignoradas,
                }

                payload_final_update = schemas.ProdutoUpdate(
                    **campos_visiveis_update,
                    dados_brutos_web=dados_extraidos_agregados,
                    status_enriquecimento_web=status_valor_str, # Passa a string (valor do enum)
                    log_enriquecimento_web={
                        "historico_mensagens": log_mensagens,
                        "resumo_aplicacao": resumo_aplicacao,
                    }
                )
                crud_produtos.update_produto(db, db_produto=db_produto_obj, produto_update=payload_final_update)
                log_mensagens.append(f"Produto ID {produto_id} FINALMENTE atualizado com status: {status_valor_str}.")
                logger.info(
                    "INFO (web_enrichment.py _finally_): Produto ID %s status ATUALIZADO PARA %s.",
                    produto_id,
                    status_valor_str,
                )
            except Exception as e_final_update:
                logger.error(
                    "ERRO CRITICO ao tentar atualizacao final do produto %s no finally: %s",
                    produto_id,
                    e_final_update,
                )
        
        final_status_value_print = status_para_salvar_no_final.value
        logger.info(
            "Finalizando tarefa de enriquecimento para produto ID: %s. Status determinado para gravação: %s",
            produto_id,
            final_status_value_print,
        )
        
        if db:
            db.close()

@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(None, description="Opcional: Termos de busca específicos para o Google Search."),
):
    db_temp = SessionLocal()
    try:
        db_produto_check = crud_produtos.get_produto(db_temp, produto_id=produto_id)
        if not db_produto_check:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
        if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a enriquecer este produto")
        
        if db_produto_check.status_enriquecimento_web == models.StatusEnriquecimentoEnum.EM_PROGRESSO:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Processo de enriquecimento já está em andamento para este produto.")
    finally:
        db_temp.close()

    background_tasks.add_task(
        _tarefa_enriquecer_produto_web,
        db_session_factory=SessionLocal,
        produto_id=produto_id,
        user_id=current_user.id,
        termos_busca_override=termos_busca_override
    )
    return {"msg": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."}


router.add_api_route(
    "/produto/{produto_id}/",
    iniciar_enriquecimento_produto_web_endpoint,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.Msg,
    include_in_schema=False,
)
