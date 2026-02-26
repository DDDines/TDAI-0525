# catalogai_project/Backend/routers/web_enrichment.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError # Para capturar exceções do SQLAlchemy
from typing import List, Dict, Any, Optional, Tuple
import asyncio
import json
import re
import unicodedata

from Backend import crud_users
from Backend import crud_produtos
from Backend import crud
from Backend import models
from Backend import schemas
from Backend.application.contracts.pipeline_commands import WebEnrichmentStartCommand
from Backend.application.orchestrators.web_enrichment import (
    WebEnrichmentPipelineOrchestrator,
)
from Backend.application.services import (
    PipelineDispatcher,
    WebEnrichmentRelevanceService,
)
from Backend.application.services.web_enrichment_task_service import (
    WebEnrichmentTaskService,
)
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
relevance_service = WebEnrichmentRelevanceService()
_web_enrichment_task_service: Optional[WebEnrichmentTaskService] = None


def _encoding_marker_count(candidate: str) -> int:
    return sum(1 for ch in candidate if ch in {"Ã", "Â", "\ufffd"})


def _normalize_human_text(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""

    def _has_markers(candidate: str) -> bool:
        return _encoding_marker_count(candidate) > 0 or "??" in candidate

    for _ in range(4):
        if not _has_markers(text):
            break
        try:
            decoded = bytes((ord(ch) & 0xFF for ch in text)).decode("utf-8")
        except Exception:
            break
        if not decoded or decoded == text:
            break
        if _encoding_marker_count(decoded) <= _encoding_marker_count(text):
            text = decoded
            continue
        break

    replacements = {
        "n??o": "não",
        "N??o": "Não",
        "p??de": "pôde",
        "P??gina": "Página",
        "p??gina": "página",
        "descri??o": "descrição",
        "Descri??o": "Descrição",
        "conte??do": "conteúdo",
        "extra??o": "extração",
        "extra??vel": "extraível",
        "situa??o": "situação",
        "configura??o": "configuração",
        "Configura??o": "Configuração",
        "nÃ£o": "não",
        "NÃ£o": "Não",
        "pÃ´de": "pôde",
        "pÃ¡gina": "página",
        "PÃ¡gina": "Página",
        "descriÃ§Ã£o": "descrição",
        "DescriÃ§Ã£o": "Descrição",
        "conteÃºdo": "conteúdo",
        "extraÃ§Ã£o": "extração",
        "extraÃ­vel": "extraível",
        "situaÃ§Ã£o": "situação",
        "configuraÃ§Ã£o": "configuração",
        "ConfiguraÃ§Ã£o": "Configuração",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)

    return re.sub(r"\s+", " ", text).strip()


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
    "não informado",
    "não informada",
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



def _tokens_for_relevance(value: Any) -> List[str]:
    return relevance_service.tokens_for_relevance(value)


def _extract_code_tokens(*values: Any) -> List[str]:
    return relevance_service.extract_code_tokens(*values)


def _is_source_relevant_for_product(
    db_produto_obj: models.Produto,
    *,
    source_name: Any,
    source_desc: Any,
    source_url: str,
) -> bool:
    return relevance_service.is_source_relevant_for_product(
        db_produto_obj,
        source_name=source_name,
        source_desc=source_desc,
        source_url=source_url,
    )



def _extrair_dominio_fornecedor(site_url: Any) -> str:
    return relevance_service.extract_supplier_domain(site_url)


def _score_url_para_produto(
    db_produto_obj: models.Produto,
    candidate_url: str,
    fornecedor_domain: str = "",
) -> int:
    return relevance_service.score_url_for_product(
        db_produto_obj,
        candidate_url,
        fornecedor_domain=fornecedor_domain,
    )


def _priorizar_urls_para_enriquecimento(
    db_produto_obj: models.Produto,
    urls_candidatas: List[str],
    fornecedor_domain: str = "",
    max_urls: int = 4,
) -> Tuple[List[str], List[Tuple[str, int]]]:
    return relevance_service.prioritize_urls_for_enrichment(
        db_produto_obj,
        urls_candidatas,
        fornecedor_domain=fornecedor_domain,
        max_urls=max_urls,
    )


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
        value_from_existing = False
        # Se o valor novo vier vazio, tenta reaproveitar aliases antigos ja existentes
        # (ex.: "titulo" -> "titulo_auto") para nao perder dados em migracoes.
        if not text_value:
            for candidate in candidates:
                candidate_norm = _fold_text(candidate)
                for current_key, current_val in dynamic_current.items():
                    current_norm = _fold_text(current_key)
                    if candidate_norm == current_norm or candidate_norm in current_norm:
                        maybe_value = _as_text(current_val)
                        if maybe_value:
                            text_value = maybe_value
                            value_from_existing = True
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
                if not candidate_norm:
                    continue
                if candidate_norm == known_norm:
                    target_key = known_key
                    break
                if candidate_norm == "descricao" and "desc" in known_norm:
                    target_key = known_key
                    break
                # Evita matches por substring muito curta (ex.: "id" em "disponibilidade").
                if len(candidate_norm) >= 4 and len(known_norm) >= 4 and (
                    candidate_norm in known_norm or known_norm in candidate_norm
                ):
                    target_key = known_key
                    break
            if target_key:
                break
        if not target_key:
            target_key = candidates[0]
        current_value = dynamic_current.get(target_key)
        current_text = _as_text(current_value)
        if _is_empty(current_value):
            dynamic_current[target_key] = text_value
            return target_key
        # Reaproveitamento de alias sem alteracao efetiva nao deve virar "ignored".
        if value_from_existing and current_text == text_value:
            return None
        if allow_replace_suspicious and _is_suspicious_code(current_value):
            dynamic_current[target_key] = text_value
            return target_key
        if (
            allow_replace_weak
            and _is_weak_dynamic_value(target_key, current_value)
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


def _get_web_enrichment_task_service() -> WebEnrichmentTaskService:
    global _web_enrichment_task_service
    if _web_enrichment_task_service is None:
        _web_enrichment_task_service = WebEnrichmentTaskService(
            logger=logger,
            SQLAlchemyError=SQLAlchemyError,
            crud_users=crud_users,
            crud_produtos=crud_produtos,
            crud=crud,
            models=models,
            schemas=schemas,
            web_extractor=web_extractor,
            settings=settings,
            json=json,
            re=re,
            normalize_human_text=_normalize_human_text,
            build_payload_enriquecimento_visivel=_build_payload_enriquecimento_visivel,
            extrair_dominio_fornecedor=_extrair_dominio_fornecedor,
            priorizar_urls_para_enriquecimento=_priorizar_urls_para_enriquecimento,
            is_meaningful_extracted_text=_is_meaningful_extracted_text,
            metadata_has_minimum_signal=_metadata_has_minimum_signal,
            is_source_relevant_for_product=_is_source_relevant_for_product,
        )
    return _web_enrichment_task_service

async def _tarefa_enriquecer_produto_web(
    db_session_factory,
    produto_id: int,
    user_id: int,
    termos_busca_override: Optional[str] = None
):
    await _get_web_enrichment_task_service().execute(
        db_session_factory=db_session_factory,
        produto_id=produto_id,
        user_id=user_id,
        termos_busca_override=termos_busca_override,
    )


async def _oop_tarefa_enriquecer_produto_web(**task_kwargs):
    """Executor OOP dedicado (modo oop), separado do legado para comparacao futura."""
    await _get_web_enrichment_task_service().execute(**task_kwargs)

@router.post("/produto/{produto_id}", status_code=status.HTTP_202_ACCEPTED, response_model=schemas.Msg)
async def iniciar_enriquecimento_produto_web_endpoint(
    produto_id: int,
    background_tasks: BackgroundTasks,
    current_user: models.User = Depends(get_current_active_user),
    termos_busca_override: Optional[str] = Query(None, description="Opcional: termos de busca específicos para o Google Search."),
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

    orchestrator = WebEnrichmentPipelineOrchestrator(
        legacy_executor=_tarefa_enriquecer_produto_web,
        oop_executor=_oop_tarefa_enriquecer_produto_web,
    )
    command = WebEnrichmentStartCommand(
        produto_id=produto_id,
        user_id=current_user.id,
        termos_busca_override=termos_busca_override,
    )
    selected_plan = orchestrator.select_start_plan(
        db_session_factory=SessionLocal,
        command=command,
    )
    PipelineDispatcher.dispatch_background(background_tasks, selected_plan)
    return {"msg": f"Processo de enriquecimento web para o produto ID {produto_id} iniciado em segundo plano."}


router.add_api_route(
    "/produto/{produto_id}/",
    iniciar_enriquecimento_produto_web_endpoint,
    methods=["POST"],
    status_code=status.HTTP_202_ACCEPTED,
    response_model=schemas.Msg,
    include_in_schema=False,
)


