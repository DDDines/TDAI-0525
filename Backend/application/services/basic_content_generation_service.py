"""Servicos de geracao basica de conteudo para modo sem IA externa."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, List

from fastapi import HTTPException, status

from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.infrastructure.repositories.product_repository import ProductRepository


class BasicContentGenerationService:
    """Gera titulos e descricoes basicas usando apenas dados internos do produto."""

    _HUMAN_TEXT_NORMALIZER = WebEnrichmentNormalizationService()

    _DEFAULT_TITLE_TEMPLATE = "{titulo_base}"
    _DEFAULT_DESCRIPTION_TEMPLATE = (
        "{nome_base}\n\n"
        "Resumo tecnico:\n{technical_summary}\n\n"
        "Aplicacao:\n{application}\n\n"
        "Referencia:\n{reference}\n\n"
        "Material:\n{material}\n\n"
        "Conteudo da embalagem:\n{content}\n\n"
        "Especificacoes tecnicas:\n{specs}\n\n"
        "Destaques tecnicos:\n{bullets}"
    )
    _TEMPLATE_FIELD_PATTERN = re.compile(r"\{([A-Za-z0-9_]+)\}")
    _GENERIC_OBJECT_SUMMARY_HINTS = {
        "frame": "Moldura decorativa para fotos, lembrancas ou composicoes tematicas.",
        "display": "Expositor para organizacao e apresentacao visual de itens em balcoes, mesas ou vitrines.",
        "displayer": "Expositor para organizacao e apresentacao visual de itens em balcoes, mesas ou vitrines.",
    }
    _KEYWORD_STOPWORDS = {
        "com",
        "para",
        "sem",
        "dos",
        "das",
        "nos",
        "nas",
        "uma",
        "uns",
        "umas",
        "que",
        "por",
        "mais",
        "menos",
        "sobre",
        "produto",
        "produtos",
        "peca",
        "pecas",
        "item",
        "itens",
        "tecnica",
        "tecnicas",
        "ficha",
    }
    _WEAK_KEYWORD_TERMS = {
        "aqui",
        "agora",
        "alta",
        "aplica",
        "atende",
        "atendimento",
        "caminh",
        "clicando",
        "clique",
        "compra",
        "compras",
        "confira",
        "contato",
        "criptografia",
        "digo",
        "devolva",
        "duvida",
        "duvidas",
        "favorito",
        "favoritos",
        "garante",
        "garantia",
        "garantias",
        "garantir",
        "loja",
        "nossa",
        "nossas",
        "nosso",
        "nossos",
        "online",
        "pagamento",
        "pagamentos",
        "parcelamento",
        "politica",
        "politicas",
        "preocupa",
        "preocupacoes",
        "preocupacao",
        "protegida",
        "protegido",
        "qualidade",
        "seguranca",
        "sua",
        "suas",
        "satisfacao",
        "seu",
        "seus",
        "tranquilidade",
        "troca",
        "trocas",
        "total",
        "venda",
        "vendas",
        "voce",
        "voces",
        "whatsapp",
        "alto",
    }
    _WEAK_KEYWORD_PREFIXES = (
        "atend",
        "aplic",
        "caminh",
        "clic",
        "compr",
        "confer",
        "contat",
        "criptograf",
        "devolu",
        "duvid",
        "favorit",
        "garant",
        "pag",
        "parcel",
        "perform",
        "politic",
        "preocup",
        "proteg",
        "qualidad",
        "satisf",
        "seguran",
        "tranquil",
        "troc",
        "whats",
    )
    _BLOCKED_SPEC_KEYS = {
        "desc_auto",
        "descricao",
        "description",
        "disponibilidade",
        "id_auto",
        "marca",
        "moeda_preco",
        "name",
        "nome",
        "titulo",
        "titulo_auto",
        "url",
        "url_da_fonte",
        "caminho_do_catalogo",
        "fonte_principal",
    }
    _CANONICAL_SPEC_LABELS = {
        "aplicacao": "Aplicacao",
        "categoria": "Categoria",
        "conteudo": "Conteudo da embalagem",
        "conteudo_da_embalagem": "Conteudo da embalagem",
        "ean": "EAN",
        "material": "Material",
        "montadora": "Montadora",
        "posicao": "Posicao",
        "referencia": "Referencia",
        "sku": "SKU",
        "temperatura_cor": "Temperatura Cor",
        "voltagem": "Voltagem",
    }
    _COMPANY_TIMELINE_HINTS = (
        "iniciou suas atividades",
        "iniciou as atividades",
        "fundada em",
        "fundado em",
        "anos de mercado",
        "no mercado desde",
        "atuando desde",
        "historia da empresa",
    )
    _COMPANY_TIMELINE_PATTERN = re.compile(
        r"\b(?:fundad[oa]\s+em\s+(?:19|20)\d{2}|desde\s+(?:19|20)\d{2}|iniciou\s+suas?\s+atividades(?:\s+no?\s+ano\s+de\s+(?:19|20)\d{2})?)\b",
        re.IGNORECASE,
    )
    _PROMOTIONAL_BOILERPLATE_HINTS = (
        "atendemos pelo whatsapp",
        "chamei no whatsapp",
        "compra online protegida",
        "confira nossas politicas",
        "confira nossas polÃ­ticas",
        "criptografia e seguranca",
        "criptografia e seguranÃ§a",
        "devolva",
        "entre em contato",
        "fale com nosso suporte",
        "garantia legal",
        "garantimos sua satisfacao",
        "garantimos sua satisfaÃ§Ã£o",
        "imagens meramente ilustrativas",
        "nosso time esta pronto",
        "nosso time estÃ¡ pronto",
        "parcelamento em ate",
        "parcelamento em atÃ©",
        "pague sem preocupacoes",
        "pague sem preocupaÃ§Ãµes",
        "peca ideal",
        "politica de troca",
        "politica de devolucao",
        "polÃ­tica de troca",
        "polÃ­tica de devoluÃ§Ã£o",
        "recomendo",
        "sem juros",
        "sua compra online",
    )
    _ENGLISH_SOURCE_MARKERS = {
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "home",
        "in",
        "including",
        "into",
        "item",
        "its",
        "landscapes",
        "nature",
        "of",
        "palette",
        "playful",
        "represents",
        "scene",
        "soft",
        "sprinkled",
        "the",
        "this",
        "with",
        "winter",
    }
    _PORTUGUESE_SOURCE_MARKERS = {
        "acabamento",
        "aplicacao",
        "apresentacao",
        "com",
        "conteudo",
        "decorativo",
        "descricao",
        "embalagem",
        "especificacoes",
        "item",
        "linha",
        "para",
        "produto",
        "resumo",
        "tecnico",
        "uso",
    }
    _PROMOTIONAL_BOILERPLATE_PATTERN = re.compile(
        r"\b(?:contato|telefone|whatsapp|sac|atendimento|parcelamento|sem\s+juros|"
        r"politica\s+de\s+(?:troca|devolu[cÃ§][aÃ£]o)|criptografia|compra\s+online\s+protegida|"
        r"confira|devolva|preocupa[cÃ§][aÃ£]o(?:es)?|garantia\s+legal|imagens?\s+meramente\s+ilustrativas|"
        r"nosso\s+time\s+est[aÃ¡]\s+pronto|fale\s+com\s+nosso\s+suporte|recomendo)\b",
        re.IGNORECASE,
    )
    _COMPANY_ENTITY_HINT_PATTERN = re.compile(
        r"\b(?:empresa|marca|fabricante|industria|loja|grupo|nos|nossa|historia|tradicao|mercado)\b",
        re.IGNORECASE,
    )
    _TITLE_CONTACT_MARKER_PATTERN = re.compile(
        r"\b(?:comercio|com[eÃ©]rcio|eletronico|eletr[oÃ´]nico|loja|empresa|atendimento|contato|telefone|whatsapp|sac|site)\b",
        re.IGNORECASE,
    )
    _PHONE_OR_ID_BLOCK_PATTERN = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")
    _EMAIL_PATTERN = re.compile(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        re.IGNORECASE,
    )
    _URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
    _SELLER_BRAND_PATTERN = re.compile(
        r"\b(?:loja|com[eé]rcio|pe[cç]as?\s+para|auto\s*pe[cç]as|caminh[oõ]es?|suporte|atendimento|oficial)\b",
        re.IGNORECASE,
    )
    _GENERIC_BRAND_TOKENS = {
        "aco",
        "aluminio",
        "alumínio",
        "central",
        "frontal",
        "grade",
        "metalico",
        "metálico",
        "painel",
        "porta",
        "superior",
        "tela",
        "vidro",
    }
    _REFERENCE_PATTERN = re.compile(
        r"\b(?:codigo\s+original|digo\s+original|referencia\b|ref\b\.?)\s*[:#-]?\s*([A-Za-z0-9./-]{4,})",
        re.IGNORECASE,
    )
    _APPLICATION_PATTERN = re.compile(
        r"\baplicacao\s*:\s*([^\n.;]{4,120}?)(?=\b(?:material|conteudo|referencia|montadora)\s*:|$)",
        re.IGNORECASE,
    )
    _CONTENT_PATTERN = re.compile(
        r"\bconteudo\s*:\s*([^\n.;]{2,80}?)(?=\b(?:material|aplicacao|referencia|montadora)\s*:|$)",
        re.IGNORECASE,
    )
    _MATERIAL_PATTERN = re.compile(
        r"\bmaterial\s*:\s*([^\n.;]{2,80}?)(?=\b(?:conteudo|aplicacao|referencia|montadora)\s*:|$)",
        re.IGNORECASE,
    )
    _INSTALLMENT_PATTERN = re.compile(
        r"\b\d+\s*x\s+de\s*r\$\s*\d[\d.,]*\b|\btotal\s+r\$\s*\d[\d.,]*\b",
        re.IGNORECASE,
    )
    _KNOWN_VEHICLE_MAKES = (
        "mercedes-benz",
        "volkswagen",
        "scania",
        "volvo",
        "iveco",
        "mercedes",
        "ford",
        "vw",
        "man",
        "daf",
        "renault",
    )
    _KNOWN_MATERIAL_TOKENS = (
        "vidro",
        "metalico",
        "plastico",
        "borracha",
        "aco",
        "aluminio",
    )

    def __init__(self, *, product_repository_factory: Any = ProductRepository) -> None:
        """Initialize injected dependencies and runtime configuration for Basic Content Generation Service."""
        self._product_repository_factory = product_repository_factory

    @staticmethod
    def _normalize_space(value: Any) -> str:
        """Normalize spacing and coerce arbitrary values to safe strings."""
        normalized = BasicContentGenerationService._HUMAN_TEXT_NORMALIZER.normalize_human_text(value)
        return " ".join(str(normalized or "").strip().split())

    @staticmethod
    def _fold_text(value: Any) -> str:
        """Fold accents and normalize unicode text to a simpler comparable form."""
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        return "".join(char for char in normalized if not unicodedata.combining(char))

    @classmethod
    def _sanitize_title_fragment(
        cls,
        value: Any,
        *,
        cut_on_contact_marker: bool = False,
        max_len: int = 120,
    ) -> str:
        """Remove contact/company noise from title fragments while preserving product identity."""
        text = cls._normalize_space(value)
        if not text:
            return ""

        text = cls._URL_PATTERN.sub(" ", text)
        text = cls._EMAIL_PATTERN.sub(" ", text)
        text = cls._PHONE_OR_ID_BLOCK_PATTERN.sub(" ", text)

        if cut_on_contact_marker:
            marker_match = cls._TITLE_CONTACT_MARKER_PATTERN.search(text)
            if marker_match:
                text = text[: marker_match.start()]

        text = cls._TITLE_CONTACT_MARKER_PATTERN.sub(" ", text)
        text = re.sub(r"\b(?:tel|telefone|whatsapp|contato|atendimento|sac)\b[:\-]?", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\bfone\b(?=\s*[:\-]?\s*\d)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" -|,;:/")
        if not text:
            return ""

        if sum(char.isdigit() for char in text) >= max(6, len(text) // 2):
            return ""

        return text[:max_len]

    @classmethod
    def _is_noisy_title_fragment(cls, value: Any) -> bool:
        """Identify fragments that look like contact/company metadata instead of product content."""
        text = cls._normalize_space(value)
        if not text:
            return True
        if cls._URL_PATTERN.search(text) or cls._EMAIL_PATTERN.search(text):
            return True
        if cls._TITLE_CONTACT_MARKER_PATTERN.search(text):
            return True
        if cls._PHONE_OR_ID_BLOCK_PATTERN.search(text):
            return True
        return False

    @classmethod
    def _is_weak_keyword(cls, value: Any) -> bool:
        """Detect weak promotional or pronoun-like keywords that should not drive titles."""
        text = cls._normalize_space(value)
        if not text:
            return True
        if cls._is_noisy_title_fragment(text):
            return True

        folded = cls._fold_text(text).lower()
        parts = re.findall(r"[a-z0-9]+", folded)
        if not parts:
            return True

        useful_parts = 0
        for part in parts:
            if len(part) < 4:
                continue
            if part in cls._KEYWORD_STOPWORDS:
                continue
            if part in cls._WEAK_KEYWORD_TERMS:
                continue
            if any(part.startswith(prefix) for prefix in cls._WEAK_KEYWORD_PREFIXES):
                continue
            useful_parts += 1
        return useful_parts == 0

    @classmethod
    def _extract_brand_hint_from_generated_name(
        cls,
        value: Any,
        *,
        identity_parts: List[Any],
    ) -> str:
        """Recover a likely manufacturer token from generated/product title text."""
        text = cls._sanitize_title_fragment(
            value,
            cut_on_contact_marker=True,
            max_len=160,
        )
        if not text or cls._is_noisy_title_fragment(text):
            return ""

        identity_tokens = set()
        for identity_part in identity_parts:
            identity_tokens.update(
                part
                for part in re.findall(
                    r"[a-z0-9]+",
                    cls._fold_text(identity_part).lower(),
                )
                if len(part) >= 4
            )

        folded_text_for_tokens = cls._fold_text(text)
        for token in re.findall(r"[A-Za-z][A-Za-z0-9./-]{2,}", folded_text_for_tokens):
            token_clean = cls._sanitize_title_fragment(
                token,
                cut_on_contact_marker=True,
                max_len=60,
            )
            folded = cls._fold_text(token_clean).lower()
            if len(folded) < 4:
                continue
            if any(char.isdigit() for char in folded):
                continue
            if folded in identity_tokens:
                continue
            if folded in cls._KEYWORD_STOPWORDS:
                continue
            if folded in cls._GENERIC_BRAND_TOKENS:
                continue
            if cls._is_weak_keyword(folded):
                continue
            return token_clean

        return ""

    @classmethod
    def _looks_like_seller_brand(cls, value: Any) -> bool:
        """Detect seller/store labels that should not be treated as manufacturer brand."""
        text = cls._sanitize_title_fragment(value, cut_on_contact_marker=True, max_len=120)
        if not text:
            return False
        return bool(cls._SELLER_BRAND_PATTERN.search(text))

    @classmethod
    def _clean_structured_fact(cls, value: Any, *, max_len: int = 90) -> str:
        """Normalize extracted technical fact fragments."""
        text = cls._sanitize_title_fragment(value, cut_on_contact_marker=True, max_len=max_len)
        if not text:
            return ""
        text = cls._INSTALLMENT_PATTERN.sub(" ", text)
        text = re.sub(r"\b(?:montadora|aplicacao|aplica[cç][aã]o|referencia|ref\.?|codigo\s+original|digo\s+original|conteudo|material)\s*:\s*", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\s+", " ", text).strip(" -|,;:/")
        if not text or cls._looks_like_promotional_boilerplate(text):
            return ""
        return text[:max_len]

    @classmethod
    def _clean_direct_reference_value(cls, value: Any, *, max_len: int = 60) -> str:
        """Preserve full structured reference codes before falling back to text inference."""
        text = cls._normalize_space(value)
        if not text:
            return ""
        text = re.sub(
            r"^(?:referencia\s+original/similar|referencia|ref\.?|codigo\s+original|codigo)\s*[:\-]?\s*",
            "",
            text,
            flags=re.IGNORECASE,
        ).strip(" -|,;:/")
        if not text:
            return ""
        compact = re.sub(r"[^A-Za-z0-9]", "", text)
        if len(compact) < 5 or not any(ch.isdigit() for ch in compact):
            return ""
        return text[:max_len]

    @classmethod
    def _normalize_structured_key(cls, value: Any) -> str:
        """Normalize structured keys so duplicates can be merged reliably."""
        return re.sub(r"[^a-z0-9]+", "_", cls._fold_text(value).lower()).strip("_")

    @classmethod
    def _canonicalize_spec_key(cls, value: Any) -> str:
        """Render structured spec keys with stable user-facing labels."""
        key_clean = cls._sanitize_title_fragment(
            value,
            cut_on_contact_marker=True,
            max_len=60,
        )
        if not key_clean:
            return ""
        normalized_key = cls._normalize_structured_key(key_clean)
        if normalized_key in cls._CANONICAL_SPEC_LABELS:
            return cls._CANONICAL_SPEC_LABELS[normalized_key]
        humanized = re.sub(r"[_\s]+", " ", key_clean).strip()
        return humanized[:1].upper() + humanized[1:] if humanized else ""

    @classmethod
    def _choose_richer_fact_value(cls, current_value: Any, candidate_value: Any) -> str:
        """Prefer the most specific fact when multiple structured candidates exist."""
        current_clean = cls._clean_structured_fact(current_value, max_len=100)
        candidate_clean = cls._clean_structured_fact(candidate_value, max_len=100)
        if not current_clean:
            return candidate_clean
        if not candidate_clean:
            return current_clean

        folded_current = cls._fold_text(current_clean).lower()
        folded_candidate = cls._fold_text(candidate_clean).lower()
        if folded_current == folded_candidate:
            return current_clean
        if folded_current in folded_candidate and len(candidate_clean) > len(current_clean):
            return candidate_clean
        if folded_candidate in folded_current and len(current_clean) >= len(candidate_clean):
            return current_clean

        generic_values = {"aco", "metal", "plastico", "borracha"}
        if folded_current in generic_values and len(candidate_clean.split()) > 1:
            return candidate_clean
        if folded_candidate in generic_values and len(current_clean.split()) > 1:
            return current_clean
        return candidate_clean if len(candidate_clean) > len(current_clean) + 8 else current_clean

    @classmethod
    def _append_spec_entry(
        cls,
        entries: List[tuple[str, str]],
        *,
        key: Any,
        value: Any,
        max_entries: int | None = None,
    ) -> None:
        """Append one spec entry or merge it with an existing canonical key."""
        key_clean = cls._canonicalize_spec_key(key)
        normalized_key = cls._normalize_structured_key(key_clean)
        raw_value_clean = cls._normalize_space(value)
        if normalized_key in {"ean", "sku"}:
            value_clean = raw_value_clean[:100]
        elif normalized_key == "referencia":
            value_clean = cls._clean_direct_reference_value(value, max_len=100) or cls._clean_structured_fact(value, max_len=100)
        else:
            value_clean = cls._clean_structured_fact(value, max_len=100)
        if not key_clean or not value_clean:
            return

        if normalized_key in cls._BLOCKED_SPEC_KEYS:
            return
        for index, (existing_key, existing_value) in enumerate(entries):
            if cls._normalize_structured_key(existing_key) != normalized_key:
                continue
            preferred_value = cls._choose_richer_fact_value(existing_value, value_clean)
            if cls._fold_text(preferred_value).lower() == cls._fold_text(existing_value).lower():
                return
            entries[index] = (key_clean, preferred_value)
            return

        if max_entries is not None and len(entries) >= max_entries:
            return
        entries.append((key_clean, value_clean))

    @classmethod
    def _looks_like_placeholder_reference_value(cls, value: Any) -> bool:
        """Reject internal/demo identifiers so they do not become customer-facing references."""
        text = cls._normalize_space(value)
        if not text:
            return False
        folded = cls._fold_text(text).lower()
        return bool(re.search(r"\b(?:llm|smoke|test|teste|demo|sample|tmp|temp)\b", folded))

    @classmethod
    def _build_reference_title_fragment(cls, value: Any) -> str:
        """Return a title-safe compact reference token."""
        text = cls._normalize_space(value)
        if not text:
            return ""
        compact_digits = re.sub(r"\D", "", text)
        if 5 <= len(compact_digits) <= 10:
            return f"Ref {compact_digits}"
        for token in re.findall(r"[A-Za-z0-9./-]{4,}", text):
            clean_token = cls._sanitize_title_fragment(token, cut_on_contact_marker=False, max_len=24)
            if not clean_token:
                continue
            if sum(ch.isdigit() for ch in clean_token) < 4:
                continue
            return f"Ref {clean_token}"
        return ""

    @classmethod
    def _detect_vehicle_make(cls, value: Any) -> str:
        """Find known vehicle makes using token boundaries to avoid substring false positives."""
        lowered = cls._fold_text(value).lower()
        if not lowered:
            return ""
        for make in cls._KNOWN_VEHICLE_MAKES:
            pattern = rf"(?<![a-z0-9]){re.escape(make)}(?![a-z0-9])"
            if not re.search(pattern, lowered):
                continue
            return make.upper() if make == "vw" else make.title().replace("-Benz", "-Benz")
        return ""

    @classmethod
    def _extract_technical_facts(cls, *, produto: Any, web_context: Dict[str, Any]) -> Dict[str, str]:
        """Extract structured technical hints from noisy web/product context."""
        raw = getattr(produto, "dados_brutos_web", None)
        dynamic_attributes = getattr(produto, "dynamic_attributes", None)
        raw_specs = cls._coerce_dict(raw.get("especificacoes_tecnicas_dict")) if isinstance(raw, dict) else {}
        dynamic_specs = cls._coerce_dict(dynamic_attributes) if isinstance(dynamic_attributes, dict) else {}

        text_sources: List[str] = [
            cls._normalize_space(getattr(produto, "nome_base", "")),
            cls._normalize_space(getattr(produto, "nome_chat_api", "")),
            cls._normalize_space(getattr(produto, "descricao_original", "")),
            cls._normalize_space(web_context.get("descricao")),
            cls._normalize_space(web_context.get("nome")),
        ]
        if isinstance(raw, dict):
            text_sources.extend(
                [
                    cls._normalize_space(raw.get("descricao_curta")),
                    cls._normalize_space(raw.get("descricao_detalhada_seo")),
                    cls._normalize_space(raw.get("texto_relevante_coletado")),
                ]
            )
        text_sources.extend(cls._coerce_list(web_context.get("bullets")))
        text_sources.extend(raw_specs.values())
        text_sources.extend(dynamic_specs.values())
        text_sources = [text for text in text_sources if text]

        application = ""
        material = ""
        content = ""
        references: List[str] = []
        vehicle_make = ""

        direct_application_values = [
            dynamic_specs.get("Aplicacao"),
            dynamic_specs.get("aplicacao"),
            raw_specs.get("Aplicacao"),
            raw_specs.get("aplicacao"),
        ]
        for candidate in direct_application_values:
            clean_candidate = cls._clean_structured_fact(candidate, max_len=100)
            if clean_candidate and cls._fold_text(clean_candidate).lower() != cls._fold_text(getattr(produto, "nome_base", "")).lower():
                application = clean_candidate
                break

        for specs_source in (dynamic_specs, raw_specs):
            for raw_key, raw_value in specs_source.items():
                normalized_key = cls._normalize_structured_key(raw_key)
                if normalized_key == "material":
                    material = cls._choose_richer_fact_value(material, raw_value)
                elif normalized_key in {"conteudo", "conteudo_da_embalagem"}:
                    content = cls._choose_richer_fact_value(content, raw_value)

        if content:
            content = re.split(
                r"\b(?:compativel|de\s+forma|rapida|pratica|segura)\b",
                content,
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0].strip(" -|,;:/")

        direct_reference_values = [
            raw.get("codigo_original") if isinstance(raw, dict) else None,
            raw.get("sku_original") if isinstance(raw, dict) else None,
            dynamic_specs.get("Referencia original/similar"),
            dynamic_specs.get("referencia original/similar"),
            dynamic_specs.get("Referencia"),
            dynamic_specs.get("referencia"),
            raw_specs.get("Referencia original/similar"),
            raw_specs.get("referencia original/similar"),
            raw_specs.get("Referencia"),
            raw_specs.get("referencia"),
            getattr(produto, "modelo", None),
        ]
        reference_hint_sources = [
            getattr(produto, "descricao_original", None),
            getattr(produto, "nome_chat_api", None),
            web_context.get("descricao"),
            raw.get("descricao_curta") if isinstance(raw, dict) else None,
            raw.get("descricao_detalhada_seo") if isinstance(raw, dict) else None,
        ]
        for source_text in reference_hint_sources:
            normalized_source = cls._normalize_space(source_text)
            if not normalized_source:
                continue
            hinted_ref = re.search(
                r"(?:refer[eê]ncia|ref\.?|codigo(?:\s+original)?|digo\s+original)[^0-9]{0,20}([A-Za-z0-9./-]{4,})",
                normalized_source,
                flags=re.IGNORECASE,
            )
            if hinted_ref:
                direct_reference_values.append(hinted_ref.group(1))
        direct_reference_values.append(getattr(produto, "sku", None))
        for candidate in direct_reference_values:
            clean_candidate = cls._clean_direct_reference_value(candidate, max_len=60)
            if not clean_candidate:
                continue
            compact_candidate = re.sub(r"[^A-Za-z0-9]", "", clean_candidate)
            if len(compact_candidate) < 5:
                continue
            if not any(ch.isdigit() for ch in compact_candidate):
                continue
            if compact_candidate.lower() in {"originalsimilar"}:
                continue
            if cls._looks_like_placeholder_reference_value(clean_candidate):
                continue
            references.append(clean_candidate)
            break

        for text in text_sources:
            folded_text = cls._fold_text(text)
            if not application:
                match = cls._APPLICATION_PATTERN.search(folded_text)
                if match:
                    application = cls._clean_structured_fact(match.group(1), max_len=100)
            if not material:
                match = cls._MATERIAL_PATTERN.search(folded_text)
                if match:
                    material = cls._clean_structured_fact(match.group(1), max_len=80)
            if not content:
                match = cls._CONTENT_PATTERN.search(folded_text)
                if match:
                    content = cls._clean_structured_fact(match.group(1), max_len=60)
                    content = re.split(r"\b(?:compativel|de\s+forma|rapida|pratica|segura)\b", content, maxsplit=1, flags=re.IGNORECASE)[0].strip(" -|,;:/")
            for ref_match in cls._REFERENCE_PATTERN.findall(folded_text):
                clean_ref = cls._clean_structured_fact(ref_match, max_len=40)
                if clean_ref and clean_ref not in references:
                    references.append(clean_ref)
            lowered = folded_text.lower()
            if not references and any(hint in lowered for hint in ("refer", "ref", "digo", "codigo")):
                hinted_ref = re.search(r"(?:ref|refer|digo|codigo)[^0-9]{0,20}(\d{4,})", lowered)
                if hinted_ref and len(hinted_ref.group(1)) < 12:
                    references.append(hinted_ref.group(1))
            if not vehicle_make:
                vehicle_make = cls._detect_vehicle_make(folded_text)

        summary_parts: List[str] = []
        primary_title = getattr(produto, "nome_base", "")
        for chunk in re.split(r"(?<=[.!?])\s+|[\r\n]+|;\s*", " ".join(text_sources)):
            clean_chunk = cls._sanitize_description_context(chunk)
            if not clean_chunk:
                continue
            folded = cls._fold_text(clean_chunk).lower()
            if len(clean_chunk) < 24:
                continue
            if not summary_parts:
                if not cls._summary_preserves_primary_identity(clean_chunk, primary_title=primary_title):
                    continue
            elif not (
                cls._summary_preserves_primary_identity(clean_chunk, primary_title=primary_title)
                or cls._summary_fragment_is_safe_followup(clean_chunk)
            ):
                continue
            if summary_parts and clean_chunk.lower() in {item.lower() for item in summary_parts}:
                continue
            if any(hint in folded for hint in ("grade", "painel", "frontal", "encaixe", "ventil", "aplica", "scania", "serie", "conteudo", "material")):
                summary_parts.append(clean_chunk)
            if len(summary_parts) >= 2:
                break

        if not references:
            raw_reference_candidates = []
            raw_reference_candidates.extend(re.findall(r"[A-Za-z0-9./-]{4,}", cls._normalize_space(getattr(produto, "nome_chat_api", ""))))
            raw_reference_candidates.extend(re.findall(r"[A-Za-z0-9./-]{4,}", cls._normalize_space(getattr(produto, "modelo", ""))))
            raw_reference_candidates.extend(re.findall(r"[A-Za-z0-9./-]{4,}", cls._normalize_space(getattr(produto, "sku", ""))))
            raw_reference_candidates.extend(re.findall(r"[A-Za-z0-9./-]{4,}", cls._normalize_space(getattr(produto, "ean", ""))))
            raw_reference_candidates = sorted(
                raw_reference_candidates,
                key=lambda token: (
                    any(char.isalpha() for char in token),
                    "/" in token or "-" in token,
                    len(token),
                ),
                reverse=True,
            )
            for raw_candidate in raw_reference_candidates:
                clean_ref = cls._clean_structured_fact(raw_candidate, max_len=40)
                if not clean_ref:
                    continue
                if cls._looks_like_placeholder_reference_value(clean_ref):
                    continue
                digit_count = sum(char.isdigit() for char in clean_ref)
                if digit_count < 4:
                    continue
                if clean_ref.isdigit() and len(clean_ref) >= 12:
                    continue
                references.append(clean_ref)
                break

        if not material:
            for text in text_sources:
                lowered = cls._fold_text(text).lower()
                for token in cls._KNOWN_MATERIAL_TOKENS:
                    if re.search(rf"\b{re.escape(cls._fold_text(token).lower())}\b", lowered):
                        material = token.title()
                        break
                if material:
                    break
        elif (
            len(material.split()) == 1
            and cls._normalize_structured_key(material)
            in {
                cls._normalize_structured_key(token)
                for token in cls._KNOWN_MATERIAL_TOKENS
            }
        ):
            material = material.title()

        return {
            "application": application,
            "material": material,
            "content": content,
            "reference": references[0] if references else "",
            "vehicle_make": vehicle_make,
            "technical_summary": " ".join(summary_parts[:2]).strip(),
        }
    def _resolve_generation_brand(
        self,
        *,
        produto: Any,
        web_context: Dict[str, Any] | None = None,
    ) -> str:
        """Prefer a manufacturer hint from generated names when stored brand looks like store noise."""
        web_context = web_context or {}
        marca = self._sanitize_title_fragment(
            getattr(produto, "marca", ""),
            cut_on_contact_marker=True,
            max_len=80,
        )
        if self._looks_like_seller_brand(marca):
            marca = ""
        nome_base = self._sanitize_title_fragment(
            getattr(produto, "nome_base", "") or web_context.get("nome"),
            cut_on_contact_marker=True,
            max_len=120,
        )
        modelo = self._sanitize_title_fragment(
            getattr(produto, "modelo", ""),
            cut_on_contact_marker=True,
            max_len=80,
        )
        categoria = self._sanitize_title_fragment(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", ""),
            cut_on_contact_marker=True,
            max_len=80,
        )
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        identity_parts = [nome_base, modelo, categoria, sku, ean, marca]

        candidate_texts = [getattr(produto, "nome_chat_api", None)]
        dynamic_attributes = getattr(produto, "dynamic_attributes", None)
        if isinstance(dynamic_attributes, dict):
            candidate_texts.extend(
                [
                    dynamic_attributes.get("titulo_auto"),
                    dynamic_attributes.get("Titulo_Auto"),
                    dynamic_attributes.get("marca"),
                    dynamic_attributes.get("Marca"),
                ]
            )
        candidate_texts.append(web_context.get("nome"))

        folded_brand = self._fold_text(marca).lower() if marca else ""
        for candidate_text in candidate_texts:
            hint = self._extract_brand_hint_from_generated_name(
                candidate_text,
                identity_parts=identity_parts,
            )
            if not hint:
                continue
            if not marca:
                return hint
            if self._fold_text(hint).lower() == folded_brand:
                return marca
            candidate_folded = self._fold_text(candidate_text).lower()
            if folded_brand and folded_brand in candidate_folded:
                return marca
            return hint

        return marca

    @classmethod
    def _sanitize_spec_pair(cls, key: Any, value: Any) -> tuple[str, str] | None:
        """Normalize specs and drop internal or promotional entries before rendering output."""
        key_clean = cls._canonicalize_spec_key(key)
        value_clean = cls._sanitize_title_fragment(
            value,
            cut_on_contact_marker=True,
            max_len=100,
        )
        if not key_clean or not value_clean:
            return None

        folded_key = cls._normalize_structured_key(key_clean)
        if folded_key in cls._BLOCKED_SPEC_KEYS:
            return None
        if key_clean.isdigit():
            return None
        if cls._looks_like_english_source_fragment(value_clean):
            return None
        if re.search(r"\burl da fonte\b", value_clean, flags=re.IGNORECASE):
            return None
        if re.search(
            r"\b(?:aplicacao|montadora|conteudo|material|digo\s+original|referencia)\s*:",
            value_clean,
            flags=re.IGNORECASE,
        ):
            return None
        normalized_key = cls._fold_text(key_clean).lower()
        if cls._is_weak_keyword(value_clean):
            return None
        if (
            cls._is_weak_keyword(key_clean)
            and normalized_key not in {"aplicacao", "material", "conteudo", "referencia", "montadora"}
        ):
            return None
        return key_clean, value_clean

    @classmethod
    def _is_redundant_keyword(cls, value: Any, *, identity_parts: List[Any]) -> bool:
        """Detect keywords that only repeat tokens already present in product identity."""
        if cls._is_weak_keyword(value):
            return True

        keyword_parts = [
            part
            for part in re.findall(r"[a-z0-9]+", cls._fold_text(value).lower())
            if len(part) >= 4
        ]

        identity_tokens = set()
        for identity_part in identity_parts:
            identity_tokens.update(
                part
                for part in re.findall(
                    r"[a-z0-9]+",
                    cls._fold_text(identity_part).lower(),
                )
                if len(part) >= 4
            )
        return all(
            any(
                part == identity_token
                or identity_token.startswith(part)
                or part.startswith(identity_token)
                for identity_token in identity_tokens
            )
            for part in keyword_parts
        )

    @classmethod
    def _tokenize_title_identity(cls, value: Any) -> List[str]:
        """Split a title into identity tokens used for overlap checks."""
        cleaned = cls._sanitize_title_fragment(value, cut_on_contact_marker=True, max_len=120)
        if not cleaned:
            return []
        return [
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_text(cleaned).lower())
            if len(token) >= 4 and token not in cls._KEYWORD_STOPWORDS
        ]

    @classmethod
    def _preserves_primary_title_identity(cls, candidate: Any, *, primary_title: Any) -> bool:
        """Reject title variants that drift too far from the primary imported identity."""
        primary_tokens = set(cls._tokenize_title_identity(primary_title))
        if len(primary_tokens) < 2:
            return True
        candidate_tokens = set(cls._tokenize_title_identity(candidate))
        if not candidate_tokens:
            return False
        overlap = len(primary_tokens & candidate_tokens)
        return overlap >= min(2, len(primary_tokens))

    @classmethod
    def _summary_preserves_primary_identity(cls, summary: Any, *, primary_title: Any) -> bool:
        """Allow freeform summaries only when they still clearly describe the imported product identity."""
        text = cls._sanitize_description_context(summary)
        if not text:
            return False
        primary_tokens = set(cls._tokenize_title_identity(primary_title))
        if len(primary_tokens) < 2:
            return True

        summary_tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", cls._fold_text(text).lower())
            if len(token) >= 4 and token not in cls._KEYWORD_STOPWORDS
        }
        if not summary_tokens:
            return False

        overlap = len(primary_tokens & summary_tokens)
        return overlap >= 1

    @classmethod
    def _summary_fragment_is_safe_followup(cls, summary: Any) -> bool:
        """Allow continuation fragments only when they start like technical continuation, not a new product identity."""
        text = cls._sanitize_description_context(summary)
        if not text:
            return False
        folded = cls._fold_text(text).lower()
        return bool(
            re.match(
                r"^(?:referencia|ref\.?|aplicacao|material|conteudo|peca|peça|atua|instalad[ao]|compativel|compatível|encaixe|sistema)\b",
                folded,
            )
        )

    @classmethod
    def _build_factual_technical_summary(
        cls,
        *,
        nome_base: Any,
        technical_facts: Dict[str, Any],
        categoria: Any,
    ) -> str:
        """Build a safe technical summary grounded on structured facts instead of noisy scraped prose."""
        product_name = cls._sanitize_title_fragment(nome_base, cut_on_contact_marker=True, max_len=140) or "Produto"
        material = cls._clean_structured_fact(technical_facts.get("material"), max_len=60)
        application = cls._clean_structured_fact(technical_facts.get("application"), max_len=100)
        reference = cls._clean_structured_fact(technical_facts.get("reference"), max_len=40)
        vehicle_make = cls._clean_structured_fact(technical_facts.get("vehicle_make"), max_len=40)
        categoria_clean = cls._sanitize_description_context(categoria)
        generic_object_hint = cls._build_generic_object_summary_hint(product_name)

        summary = product_name
        application_hint = application or vehicle_make
        if generic_object_hint and not material and not application_hint:
            summary = generic_object_hint
            if categoria_clean and cls._fold_text(categoria_clean).lower() not in cls._fold_text(summary).lower():
                summary = f"{summary.rstrip('.')} para {categoria_clean.lower()}."
            if reference:
                summary = f"{summary.rstrip('.')} Referencia {reference} para identificacao tecnica."
            return summary.strip()

        if material and cls._fold_text(material).lower() not in cls._fold_text(product_name).lower():
            summary = f"{summary} em {material.lower()}"

        if application_hint:
            summary = f"{summary} com aplicacao em {application_hint}"
        elif categoria_clean:
            summary = f"{summary} para {categoria_clean.lower()}"

        summary = summary.rstrip(".") + "."
        if reference:
            summary = f"{summary} Referencia {reference} para identificacao tecnica."
        return summary.strip()

    @classmethod
    def _build_generic_object_summary_hint(cls, nome_base: Any) -> str:
        """Return a neutral summary hint for short non-technical retail object names."""
        product_name = cls._sanitize_title_fragment(nome_base, cut_on_contact_marker=True, max_len=140)
        if not product_name:
            return ""

        folded_name = cls._fold_text(product_name).lower()
        tokens = re.findall(r"[a-z0-9]+", folded_name)
        if not tokens:
            return ""

        object_hint = ""
        if "displayer" in tokens or "display" in tokens:
            object_hint = cls._GENERIC_OBJECT_SUMMARY_HINTS["displayer"]
            if "tier" in tokens:
                object_hint = "Expositor em camadas para organizacao e apresentacao visual de itens."
        elif "frame" in tokens:
            object_hint = cls._GENERIC_OBJECT_SUMMARY_HINTS["frame"]

        return object_hint.strip()

    @staticmethod
    def _unique_keep_order(values: List[str]) -> List[str]:
        """Deduplicate candidate values while preserving their original order."""
        seen = set()
        unique_values: List[str] = []
        for value in values:
            normalized = value.lower()
            if not value or normalized in seen:
                continue
            seen.add(normalized)
            unique_values.append(value)
        return unique_values

    @staticmethod
    def _coerce_list(value: Any) -> List[str]:
        """Normalize scalar/list payloads into a compact string list."""
        if isinstance(value, list):
            iterable = value
        elif value is None:
            iterable = []
        else:
            iterable = [value]
        normalized: List[str] = []
        for item in iterable:
            clean = " ".join(str(item or "").strip().split())
            if clean:
                normalized.append(clean)
        return normalized

    @staticmethod
    def _coerce_dict(value: Any) -> Dict[str, str]:
        """Normalize dict payload with string keys and values."""
        if not isinstance(value, dict):
            return {}
        parsed: Dict[str, str] = {}
        for key, raw_value in value.items():
            key_clean = " ".join(str(key or "").strip().split())
            value_clean = " ".join(str(raw_value or "").strip().split())
            if key_clean and value_clean:
                parsed[key_clean] = value_clean
        return parsed

    @staticmethod
    def _safe_template(template: Any, *, default_template: str) -> str:
        """Normalize custom templates and fallback to built-in defaults."""
        raw = str(template or "").replace("\r\n", "\n").strip()
        if not raw:
            return default_template
        return raw[:2000]

    def _render_template(self, *, template: str, context: Dict[str, Any]) -> str:
        """Render a lightweight placeholder template with normalized values."""

        def _normalize_value(value: Any) -> str:
            """Normalize template values into compact printable strings."""
            if value is None:
                return ""
            if isinstance(value, dict):
                pairs = [
                    f"{self._normalize_space(k)}: {self._normalize_space(v)}"
                    for k, v in value.items()
                    if self._normalize_space(k) and self._normalize_space(v)
                ]
                return "; ".join(pairs)
            if isinstance(value, list):
                items = [self._normalize_space(item) for item in value if self._normalize_space(item)]
                return ", ".join(items)
            if isinstance(value, str) and "\n" in value:
                return "\n".join(
                    " ".join(line.strip().split())
                    for line in value.splitlines()
                    if line.strip()
                )
            return self._normalize_space(value)

        def _replace(match: re.Match[str]) -> str:
            """Replace placeholder matches using the provided render context."""
            key = match.group(1)
            return _normalize_value(context.get(key))

        rendered = self._TEMPLATE_FIELD_PATTERN.sub(_replace, template)
        rendered = re.sub(r"[ \t]+\n", "\n", rendered)
        rendered = re.sub(r"\n{3,}", "\n\n", rendered)
        rendered = re.sub(r"[ \t]{2,}", " ", rendered)
        rendered = "\n".join(line.strip() for line in rendered.splitlines())
        rendered = "\n".join(line for line in rendered.splitlines() if line.strip())
        return rendered.strip()

    @staticmethod
    def _format_list_for_template(
        values: List[str],
        *,
        bullet_prefix: str = "- ",
        empty_fallback: str = "Nao informado.",
    ) -> str:
        """Format list values to a deterministic multiline template fragment."""
        normalized = [str(value or "").strip() for value in values if str(value or "").strip()]
        if not normalized:
            return empty_fallback
        return "\n".join(f"{bullet_prefix}{item}" for item in normalized)

    def _extract_keywords_from_texts(self, *, texts: List[str], limit: int = 8) -> List[str]:
        """Generate compact keyword hints from text snippets."""
        scores: Dict[str, int] = {}
        for text in texts:
            normalized_text = self._fold_text(text or "")
            clean_tokens: List[str] = []
            for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9./-]{2,}", normalized_text):
                token_clean = token.strip(".,;:()[]{}<>\"'").lower()
                if len(token_clean) < 3:
                    continue
                if token_clean in self._KEYWORD_STOPWORDS:
                    continue
                if token_clean.startswith("http"):
                    continue
                if token_clean.isdigit() and len(token_clean) < 4:
                    continue
                if self._is_weak_keyword(token_clean):
                    continue
                scores[token_clean] = scores.get(token_clean, 0) + 1
                clean_tokens.append(token_clean)
            for left, right in zip(clean_tokens, clean_tokens[1:]):
                phrase = f"{left} {right}"
                if self._is_weak_keyword(phrase):
                    continue
                scores[phrase] = scores.get(phrase, 0) + 2
        ranked = sorted(scores.items(), key=lambda item: (-item[1], -len(item[0]), item[0]))
        return [token for token, _ in ranked[:limit]]

    @classmethod
    def _looks_like_company_timeline_claim(cls, text: str) -> bool:
        """Detect company-history claims that should not be inferred from web snippets."""
        compact = " ".join(str(text or "").strip().split())
        if not compact:
            return False

        lowered = compact.lower()
        if any(hint in lowered for hint in cls._COMPANY_TIMELINE_HINTS):
            return True

        if not cls._COMPANY_TIMELINE_PATTERN.search(compact):
            return False

        return bool(cls._COMPANY_ENTITY_HINT_PATTERN.search(compact))

    @classmethod
    def _looks_like_promotional_boilerplate(cls, text: str) -> bool:
        """Detect support/payment/return-policy boilerplate that should not compose product copy."""
        compact = " ".join(str(text or "").strip().split())
        if not compact:
            return False
        lowered = cls._fold_text(compact).lower()
        if cls._URL_PATTERN.search(compact) or cls._EMAIL_PATTERN.search(compact):
            return True
        if cls._PHONE_OR_ID_BLOCK_PATTERN.search(compact):
            return True
        if cls._PROMOTIONAL_BOILERPLATE_PATTERN.search(compact):
            return True
        if cls._INSTALLMENT_PATTERN.search(compact):
            return True
        return any(hint in lowered for hint in cls._PROMOTIONAL_BOILERPLATE_HINTS)

    @classmethod
    def _looks_like_english_source_fragment(cls, text: Any) -> bool:
        """Reject obvious raw English scrape fragments before they become visible copy."""
        raw_text = str(text or "")
        compact = cls._normalize_space(raw_text)
        if not compact:
            return False

        if re.search(r"%[0-9A-Fa-f]{2}", raw_text):
            return True

        folded = cls._fold_text(compact).lower()
        if any(
            phrase in folded
            for phrase in (
                "this collection",
                "including the",
                "represents winter",
                "soft palette",
                "playful details of nature",
            )
        ):
            return True

        tokens = re.findall(r"[a-z]+", folded)
        if len(tokens) < 6:
            return False
        english_hits = sum(token in cls._ENGLISH_SOURCE_MARKERS for token in tokens)
        portuguese_hits = sum(token in cls._PORTUGUESE_SOURCE_MARKERS for token in tokens)
        return english_hits >= 3 and english_hits > max(1, portuguese_hits * 2)

    @classmethod
    def _sanitize_description_context(cls, raw_text: Any) -> str:
        """Drop unsupported company timeline and commercial boilerplate from source descriptions."""
        text = cls._normalize_space(raw_text)
        if not text:
            return ""

        text = cls._INSTALLMENT_PATTERN.sub(" ", text)
        text = re.sub(
            r",?\s*marca\s*:?\s*(?:vidro|metalico|met[aá]lico|plastico|pl[aá]stico|borracha|aco|aço|aluminio|alum[ií]nio)\b\.?",
            ". ",
            text,
            flags=re.IGNORECASE,
        )
        text = re.sub(r"\b(?:destaques?|especificacoes?)\s*:\s*", ". ", text, flags=re.IGNORECASE)
        chunks = re.split(r"(?<=[.!?])\s+|[\r\n]+|;\s*", text)
        filtered_chunks: List[str] = []
        seen = set()
        for chunk in chunks:
            normalized_chunk = " ".join(str(chunk or "").strip().split())
            normalized_chunk = cls._INSTALLMENT_PATTERN.sub(" ", normalized_chunk)
            normalized_chunk = re.sub(r"\s+", " ", normalized_chunk).strip(" -|,;:/~")
            normalized_chunk = re.sub(r"\s+([,.;:!?])", r"\1", normalized_chunk)
            if not normalized_chunk:
                continue
            if len(normalized_chunk) < 12:
                continue
            if not re.search(r"[A-Za-z0-9]", normalized_chunk):
                continue
            if cls._looks_like_company_timeline_claim(normalized_chunk):
                continue
            if cls._looks_like_promotional_boilerplate(normalized_chunk):
                continue
            if cls._looks_like_english_source_fragment(normalized_chunk):
                continue
            folded = cls._fold_text(normalized_chunk).lower()
            if folded in seen:
                continue
            seen.add(folded)
            filtered_chunks.append(normalized_chunk)

        if filtered_chunks:
            return " ".join(filtered_chunks).strip()
        return ""

    def _extract_web_context(self, *, produto: Any) -> Dict[str, Any]:
        """Read normalized web enrichment context from dados_brutos_web."""
        raw = getattr(produto, "dados_brutos_web", None)
        if not isinstance(raw, dict):
            return {
                "nome": "",
                "descricao": "",
                "bullets": [],
                "keywords": [],
                "specs": {},
            }

        nome = self._normalize_space(
            raw.get("nome_sugerido_seo") or raw.get("nome")
        )
        descricao = self._normalize_space(
            raw.get("descricao_detalhada_seo")
            or raw.get("descricao_curta")
            or raw.get("texto_relevante_coletado")
        )
        bullets = self._coerce_list(raw.get("lista_caracteristicas_beneficios_bullets"))
        keywords = self._coerce_list(raw.get("palavras_chave_seo_relevantes_lista"))
        raw_specs = self._coerce_dict(raw.get("especificacoes_tecnicas_dict"))
        spec_entries: List[tuple[str, str]] = []
        for raw_key, raw_value in raw_specs.items():
            self._append_spec_entry(
                spec_entries,
                key=raw_key,
                value=raw_value,
            )
        specs: Dict[str, str] = {key: value for key, value in spec_entries}
        nome = self._sanitize_title_fragment(nome, cut_on_contact_marker=True, max_len=120)

        if not descricao:
            fontes = raw.get("fontes_web_coletadas")
            if isinstance(fontes, list):
                desc_parts = []
                for source in fontes:
                    if not isinstance(source, dict):
                        continue
                    source_desc = self._normalize_space(source.get("descricao_curta"))
                    if source_desc and not self._looks_like_company_timeline_claim(source_desc):
                        desc_parts.append(source_desc)
                descricao = self._normalize_space(" ".join(desc_parts))

        descricao = self._sanitize_description_context(descricao)
        bullets = [
            item
            for item in bullets
            if not self._looks_like_company_timeline_claim(item)
            and not self._looks_like_promotional_boilerplate(item)
        ]

        if not keywords:
            keywords = self._extract_keywords_from_texts(
                texts=[
                    nome,
                    descricao,
                    " ".join(bullets),
                    " ".join(f"{key} {value}" for key, value in specs.items()),
                ],
                limit=8,
            )
        keywords = [
            self._sanitize_title_fragment(item, cut_on_contact_marker=True, max_len=60)
            for item in keywords
        ]
        keywords = [
            item
            for item in keywords
            if item and not self._is_weak_keyword(item)
        ]
        keywords = self._unique_keep_order(keywords)
        if len(keywords) < 4:
            fallback_keywords = self._extract_keywords_from_texts(
                texts=[
                    nome,
                    descricao,
                    " ".join(bullets),
                    " ".join(f"{key} {value}" for key, value in specs.items()),
                ],
                limit=12,
            )
            for token in fallback_keywords:
                token_clean = self._sanitize_title_fragment(
                    token,
                    cut_on_contact_marker=True,
                    max_len=60,
                )
                if not token_clean or self._is_weak_keyword(token_clean):
                    continue
                if token_clean.lower() in {item.lower() for item in keywords}:
                    continue
                keywords.append(token_clean)
                if len(keywords) >= 8:
                    break

        return {
            "nome": nome,
            "descricao": descricao,
            "bullets": bullets[:6],
            "keywords": keywords[:8],
            "specs": specs,
        }

    def _ensure_minimum_title_candidates(
        self,
        *,
        candidates: List[str],
        produto: Any,
        minimum_count: int,
        web_context: Dict[str, Any],
    ) -> List[str]:
        """Ensure enough fallback titles for downstream generators."""
        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or self._normalize_space(
            web_context.get("nome")
        ) or "Produto"
        nome_base = self._sanitize_title_fragment(nome_base, cut_on_contact_marker=True) or "Produto"
        marca = self._resolve_generation_brand(produto=produto, web_context=web_context)
        sku = self._normalize_space(getattr(produto, "sku", ""))
        modelo = self._sanitize_title_fragment(getattr(produto, "modelo", ""), cut_on_contact_marker=True, max_len=80)
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )
        categoria = self._sanitize_title_fragment(categoria, cut_on_contact_marker=True, max_len=80)
        technical_facts = self._extract_technical_facts(produto=produto, web_context=web_context)
        reference_fragment = self._build_reference_title_fragment(technical_facts.get("reference"))
        keyword_seed = self._coerce_list(web_context.get("keywords"))
        keyword_identity_parts = [
            nome_base,
            marca,
            modelo,
            categoria,
            sku,
            technical_facts.get("vehicle_make"),
            technical_facts.get("application"),
            technical_facts.get("reference"),
        ]

        patterns = [
            self._normalize_space(" ".join(part for part in [nome_base, marca] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("vehicle_make", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("application", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, reference_fragment] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("vehicle_make", ""), reference_fragment] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("material", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria] if part)),
            self._normalize_space(" ".join(part for part in [marca, nome_base, modelo] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, sku] if part and len(sku) <= 24)),
        ]
        for keyword in keyword_seed[:4]:
            if self._is_redundant_keyword(keyword, identity_parts=keyword_identity_parts):
                continue
            patterns.append(
                self._normalize_space(" ".join(part for part in [nome_base, keyword] if part))
            )

        combined = [
            self._sanitize_title_fragment(item, cut_on_contact_marker=True)
            for item in [*candidates, *patterns]
        ]
        combined = [
            item
            for item in combined
            if item
            and not self._is_noisy_title_fragment(item)
            and self._preserves_primary_title_identity(item, primary_title=nome_base)
        ]
        combined = self._unique_keep_order(combined)
        while len(combined) < minimum_count:
            option_index = len(combined) + 1
            fallback_tokens = [nome_base, technical_facts.get("vehicle_make", ""), technical_facts.get("reference", ""), categoria, marca, modelo]
            fallback = self._normalize_space(" ".join(part for part in fallback_tokens if part)) or nome_base
            fallback = self._sanitize_title_fragment(fallback, cut_on_contact_marker=True)
            if fallback and fallback.lower() not in {item.lower() for item in combined}:
                combined.append(fallback)
                continue
            combined.append(self._normalize_space(f"{nome_base} variante {option_index}"))
            combined = self._unique_keep_order(combined)
        return combined

    def _load_produto(self, *, session: Any, produto_id: int) -> Any:
        """Load and validate product existence for basic content generation."""
        product_repository = self._product_repository_factory(session)
        produto = product_repository.get_produto(produto_id=produto_id)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado",
            )
        return produto

    def _build_title_candidates(
        self,
        *,
        produto: Any,
        web_context: Dict[str, Any] | None = None,
    ) -> List[str]:
        """Build title candidates from product identity and technical hints."""
        web_context = web_context or self._extract_web_context(produto=produto)
        technical_facts = self._extract_technical_facts(produto=produto, web_context=web_context)

        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or self._normalize_space(
            web_context.get("nome")
        )
        nome_base = self._sanitize_title_fragment(nome_base, cut_on_contact_marker=True)
        marca = self._resolve_generation_brand(produto=produto, web_context=web_context)
        modelo = self._sanitize_title_fragment(getattr(produto, "modelo", ""), cut_on_contact_marker=True, max_len=80)
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )
        categoria = self._sanitize_title_fragment(categoria, cut_on_contact_marker=True, max_len=80)

        keywords = self._coerce_list(web_context.get("keywords"))
        specs = self._coerce_dict(web_context.get("specs"))
        nome_web = self._sanitize_title_fragment(
            web_context.get("nome"),
            cut_on_contact_marker=True,
            max_len=120,
        )
        reference_fragment = f"Ref {technical_facts['reference']}" if technical_facts.get("reference") else ""
        keyword_identity_parts = [
            nome_base,
            marca,
            modelo,
            categoria,
            nome_web,
            sku,
            ean,
            technical_facts.get("vehicle_make"),
            technical_facts.get("application"),
            technical_facts.get("reference"),
        ]

        candidates: List[str] = [
            nome_base,
            self._normalize_space(" ".join(part for part in [nome_base, marca] if part)),
            self._normalize_space(" ".join(part for part in [nome_web] if part and self._fold_text(nome_web).lower() != self._fold_text(nome_base).lower())),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("vehicle_make", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("application", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, reference_fragment] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("vehicle_make", ""), reference_fragment] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, technical_facts.get("material", "")] if part)),
            self._normalize_space(" ".join(part for part in [nome_base, categoria] if part)),
        ]

        for keyword in keywords[:4]:
            if self._is_redundant_keyword(keyword, identity_parts=keyword_identity_parts):
                continue
            candidates.append(
                self._normalize_space(" ".join(part for part in [nome_base, keyword] if part))
            )
        for spec_key, spec_value in list(specs.items())[:4]:
            sanitized_pair = self._sanitize_spec_pair(spec_key, spec_value)
            if not sanitized_pair:
                continue
            _, spec_clean = sanitized_pair
            if self._is_redundant_keyword(spec_clean, identity_parts=keyword_identity_parts):
                continue
            candidates.append(
                self._normalize_space(" ".join(part for part in [nome_base, spec_clean] if part))
            )

        candidates = [
            self._sanitize_title_fragment(item, cut_on_contact_marker=True, max_len=120)
            for item in candidates
        ]
        candidates = [
            item
            for item in self._unique_keep_order(candidates)
            if item
            and not self._is_noisy_title_fragment(item)
            and self._preserves_primary_title_identity(item, primary_title=nome_base)
        ]
        candidates = self._ensure_minimum_title_candidates(
            candidates=candidates,
            produto=produto,
            minimum_count=5,
            web_context=web_context,
        )
        if candidates:
            return candidates
        fallback = self._normalize_space(f"Produto {getattr(produto, 'id', '')}")
        return [fallback or "Produto"]

    def _build_titles_with_template(
        self,
        *,
        produto: Any,
        template_titulo: str,
        web_context: Dict[str, Any],
        base_candidates: List[str],
        max_titles: int,
    ) -> List[str]:
        """Render optional title templates and merge with deterministic fallbacks."""
        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or "Produto"
        nome_base = self._sanitize_title_fragment(nome_base, cut_on_contact_marker=True) or "Produto"
        marca = self._resolve_generation_brand(produto=produto, web_context=web_context)
        modelo = self._sanitize_title_fragment(getattr(produto, "modelo", ""), cut_on_contact_marker=True, max_len=80)
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )
        categoria = self._sanitize_title_fragment(categoria, cut_on_contact_marker=True, max_len=80)
        fornecedor = getattr(produto, "fornecedor", None)
        fornecedor_nome = self._sanitize_title_fragment(
            getattr(fornecedor, "nome", "") if fornecedor else "",
            cut_on_contact_marker=True,
            max_len=80,
        )
        web_nome = self._sanitize_title_fragment(web_context.get("nome"), cut_on_contact_marker=True, max_len=120)
        web_descricao = self._normalize_space(web_context.get("descricao"))
        technical_facts = self._extract_technical_facts(produto=produto, web_context=web_context)

        keywords = [
            self._sanitize_title_fragment(item, cut_on_contact_marker=True, max_len=60)
            for item in self._coerce_list(web_context.get("keywords"))
        ]
        keyword_identity_parts = [nome_base, marca, modelo, categoria, fornecedor_nome, web_nome, sku, ean]
        keywords = [
            item
            for item in keywords
            if item and not self._is_redundant_keyword(item, identity_parts=keyword_identity_parts)
        ]
        spec_items = list(self._coerce_dict(web_context.get("specs")).items())
        rendered_titles: List[str] = []
        upper_bound = max(10, max_titles * 4)

        for index in range(upper_bound):
            keyword = keywords[index % len(keywords)] if keywords else ""
            spec_key = ""
            spec_value = ""
            if spec_items:
                spec_key, spec_value = spec_items[index % len(spec_items)]

            title_base = base_candidates[index % len(base_candidates)] if base_candidates else ""
            context = {
                "nome_base": nome_base,
                "marca": marca,
                "modelo": modelo,
                "sku": sku,
                "ean": ean,
                "categoria": categoria,
                "fornecedor": fornecedor_nome,
                "nome_web": web_nome,
                "descricao_web": web_descricao,
                "keyword": keyword,
                "spec_key": self._normalize_space(spec_key),
                "spec_value": self._normalize_space(spec_value),
                "titulo_base": title_base,
                "indice": str(index + 1),
                "application": technical_facts.get("application", ""),
                "reference": technical_facts.get("reference", ""),
                "material": technical_facts.get("material", ""),
                "content": technical_facts.get("content", ""),
                "vehicle_make": technical_facts.get("vehicle_make", ""),
                "technical_summary": technical_facts.get("technical_summary", ""),
            }
            rendered = self._render_template(template=template_titulo, context=context)
            rendered = self._sanitize_title_fragment(
                rendered,
                cut_on_contact_marker=True,
                max_len=120,
            )
            if rendered and not self._is_noisy_title_fragment(rendered):
                rendered_titles.append(rendered)
            if len(self._unique_keep_order(rendered_titles)) >= max_titles:
                break

        return self._unique_keep_order(rendered_titles)

    def _build_basic_description(
        self,
        *,
        produto: Any,
        tamanho_palavras: int,
        template_descricao: str,
    ) -> str:
        """Compose a concise structured basic description from product and technical attributes."""
        web_context = self._extract_web_context(produto=produto)
        technical_facts = self._extract_technical_facts(produto=produto, web_context=web_context)
        nome_base = self._normalize_space(getattr(produto, "nome_base", "")) or "Produto"
        marca = self._resolve_generation_brand(produto=produto, web_context=web_context)
        modelo = self._normalize_space(getattr(produto, "modelo", ""))
        sku = self._normalize_space(getattr(produto, "sku", ""))
        ean = self._normalize_space(getattr(produto, "ean", ""))
        categoria = self._normalize_space(
            getattr(produto, "categoria_mapeada", "")
            or getattr(produto, "categoria_original", "")
        )

        descricao_web = self._normalize_space(web_context.get("descricao"))
        summary_fragments: List[str] = []
        for fragment in re.split(r"(?<=[.!?])\s+", descricao_web):
            clean_fragment = self._sanitize_description_context(fragment)
            if not clean_fragment:
                continue
            folded_fragment = self._fold_text(clean_fragment).lower()
            if any(
                hint in folded_fragment
                for hint in (
                    "digo original",
                    "montadora",
                    "conteudo",
                    "compativel",
                    "de forma rapida",
                    "pratica e segura",
                    "nosso time",
                )
            ):
                continue
            if not summary_fragments:
                if not self._summary_preserves_primary_identity(clean_fragment, primary_title=nome_base):
                    continue
            elif not (
                self._summary_preserves_primary_identity(clean_fragment, primary_title=nome_base)
                or self._summary_fragment_is_safe_followup(clean_fragment)
            ):
                continue
            summary_fragments.append(clean_fragment.rstrip(".") + ".")
            if len(summary_fragments) >= 2:
                break
        summary_from_web = " ".join(summary_fragments).strip()
        summary_candidates = []
        for candidate in [summary_from_web, technical_facts.get("technical_summary", "")]:
            if not candidate:
                continue
            if self._summary_preserves_primary_identity(candidate, primary_title=nome_base):
                summary_candidates.append(candidate)

        summary_candidates.append(
            self._build_factual_technical_summary(
                nome_base=nome_base,
                technical_facts=technical_facts,
                categoria=categoria,
            )
        )
        if technical_facts.get("vehicle_make") and technical_facts.get("application"):
            summary_candidates.append(
                f"{nome_base} com aplicacao em {technical_facts['application']} da linha {technical_facts['vehicle_make']}."
            )
        if categoria:
            summary_candidates.append(f"{nome_base} para {categoria.lower()}.")
        technical_summary = next((item for item in summary_candidates if item), "Descricao tecnica nao informada.")
        if marca and marca.lower() not in technical_summary.lower():
            technical_summary = f"{technical_summary} Fabricante: {marca}." if technical_summary else f"Fabricante: {marca}."

        spec_entries: List[tuple[str, str]] = []
        if sku:
            self._append_spec_entry(spec_entries, key="SKU", value=sku)
        if ean:
            self._append_spec_entry(spec_entries, key="EAN", value=ean)
        if technical_facts.get("reference"):
            self._append_spec_entry(
                spec_entries,
                key="Referencia",
                value=technical_facts["reference"],
            )
        if technical_facts.get("vehicle_make"):
            self._append_spec_entry(
                spec_entries,
                key="Montadora",
                value=technical_facts["vehicle_make"],
            )
        if technical_facts.get("application"):
            self._append_spec_entry(
                spec_entries,
                key="Aplicacao",
                value=technical_facts["application"],
            )
        if technical_facts.get("material"):
            self._append_spec_entry(
                spec_entries,
                key="Material",
                value=technical_facts["material"],
            )
        if technical_facts.get("content"):
            self._append_spec_entry(
                spec_entries,
                key="Conteudo da embalagem",
                value=technical_facts["content"],
            )

        dynamic_attributes = getattr(produto, "dynamic_attributes", None)
        if isinstance(dynamic_attributes, dict):
            for key, value in dynamic_attributes.items():
                sanitized_pair = self._sanitize_spec_pair(key, value)
                if sanitized_pair:
                    key_clean, value_clean = sanitized_pair
                    folded_key = self._fold_text(key_clean).lower()
                    folded_value = self._fold_text(value_clean).lower()
                    if folded_key == "aplicacao" and folded_value == self._fold_text(nome_base).lower():
                        continue
                    if folded_key == "material" and ("serie" in folded_value or "~~" in value_clean):
                        continue
                    self._append_spec_entry(
                        spec_entries,
                        key=key_clean,
                        value=value_clean,
                        max_entries=12,
                    )
                if len(spec_entries) >= 12:
                    break

        web_specs = self._coerce_dict(web_context.get("specs"))
        if web_specs:
            for key, value in list(web_specs.items())[:8]:
                sanitized_pair = self._sanitize_spec_pair(key, value)
                if not sanitized_pair:
                    continue
                key_clean, value_clean = sanitized_pair
                folded_key = self._fold_text(key_clean).lower()
                folded_value = self._fold_text(value_clean).lower()
                if folded_key == "aplicacao" and folded_value == self._fold_text(nome_base).lower():
                    continue
                if folded_key == "material" and ("serie" in folded_value or "~~" in value_clean):
                    continue
                self._append_spec_entry(
                    spec_entries,
                    key=key_clean,
                    value=value_clean,
                    max_entries=12,
                )

        specs = [f"{key}: {value}" for key, value in spec_entries]

        bullets = [self._sanitize_description_context(item) for item in self._coerce_list(web_context.get("bullets"))]
        bullets = [item for item in bullets if item]
        if (
            technical_facts.get("technical_summary")
            and self._summary_preserves_primary_identity(
                technical_facts["technical_summary"],
                primary_title=nome_base,
            )
            and technical_facts["technical_summary"].lower() not in {item.lower() for item in bullets}
        ):
            bullets.insert(0, technical_facts["technical_summary"])
        elif technical_summary and technical_summary.lower() not in {item.lower() for item in bullets}:
            bullets.insert(0, technical_summary)
        bullets = self._unique_keep_order(bullets)[:5]

        application_text = technical_facts.get("application") or technical_facts.get("vehicle_make") or categoria or "Nao informado."
        reference_text = technical_facts.get("reference") or sku or "Nao informado."
        material_text = technical_facts.get("material") or "Nao informado."
        content_text = technical_facts.get("content") or "Nao informado."

        template_context = {
            "intro": nome_base,
            "nome_base": nome_base,
            "marca": marca,
            "modelo": modelo,
            "sku": sku,
            "ean": ean,
            "categoria": categoria,
            "descricao_web": descricao_web or "Descricao complementar indisponivel.",
            "technical_summary": technical_summary,
            "application": application_text,
            "reference": reference_text,
            "material": material_text,
            "content": content_text,
            "vehicle_make": technical_facts.get("vehicle_make", ""),
            "specs": self._format_list_for_template(
                specs,
                bullet_prefix="- ",
                empty_fallback="- Sem especificacoes tecnicas adicionais.",
            ),
            "bullets": self._format_list_for_template(
                bullets,
                bullet_prefix="- ",
                empty_fallback="- Sem destaques tecnicos adicionais.",
            ),
            "keywords": ", ".join(self._coerce_list(web_context.get("keywords"))) or "Sem palavras-chave relevantes.",
            "keywords_list": self._coerce_list(web_context.get("keywords")),
            "specs_list": specs,
            "bullets_list": bullets,
        }

        descricao = self._render_template(
            template=template_descricao,
            context=template_context,
        )
        if not descricao:
            descricao = (
                f"{nome_base}."
                if technical_summary == "Descricao tecnica nao informada."
                else technical_summary
            )

        max_words = max(60, int(tamanho_palavras or 180))
        words = descricao.split()
        if len(words) <= max_words:
            return descricao
        return " ".join(words[:max_words]).strip()

    async def gerar_titulos_basicos(
        self,
        *,
        session: Any,
        produto_id: int,
        user: Any,
        num_titulos: int = 5,
        template_titulo: str | None = None,
    ) -> List[str]:
        """Generate title suggestions without external IA providers."""
        _ = user
        produto = self._load_produto(session=session, produto_id=produto_id)
        max_titles = max(1, min(int(num_titulos or 5), 10))
        web_context = self._extract_web_context(produto=produto)
        fallback_candidates = self._build_title_candidates(
            produto=produto,
            web_context=web_context,
        )
        safe_template = self._safe_template(
            template_titulo,
            default_template=self._DEFAULT_TITLE_TEMPLATE,
        )
        templated_candidates = self._build_titles_with_template(
            produto=produto,
            template_titulo=safe_template,
            web_context=web_context,
            base_candidates=fallback_candidates,
            max_titles=max_titles,
        )
        merged_candidates = self._unique_keep_order([*templated_candidates, *fallback_candidates])
        merged_candidates = self._ensure_minimum_title_candidates(
            candidates=merged_candidates,
            produto=produto,
            minimum_count=max_titles,
            web_context=web_context,
        )
        return merged_candidates[:max_titles]

    async def gerar_descricao_basica(
        self,
        *,
        session: Any,
        produto_id: int,
        user: Any,
        tamanho_palavras: int = 150,
        template_descricao: str | None = None,
    ) -> str:
        """Generate a basic product description without external IA providers."""
        _ = user
        produto = self._load_produto(session=session, produto_id=produto_id)
        safe_template = self._safe_template(
            template_descricao,
            default_template=self._DEFAULT_DESCRIPTION_TEMPLATE,
        )
        return self._build_basic_description(
            produto=produto,
            tamanho_palavras=tamanho_palavras,
            template_descricao=safe_template,
        )

    # ------------------------------------------------------------------
    # Public facade — allows external services to call without accessing
    # private symbols (architecture boundary compliance)
    # ------------------------------------------------------------------

    def build_basic_description(self, *, produto: Any, tamanho_palavras: int, template_descricao: str) -> str:
        """Public facade for cross-service usage of build_basic_description."""
        return self._build_basic_description(produto=produto, tamanho_palavras=tamanho_palavras, template_descricao=template_descricao)

    @classmethod
    def sanitize_description_context(cls, raw_text: Any) -> str:
        """Public facade for cross-service usage of sanitize_description_context."""
        return cls._sanitize_description_context(raw_text)

    @classmethod
    def fold_text(cls, value: Any) -> str:
        """Public facade for cross-service usage of fold_text."""
        return cls._fold_text(value)

    @classmethod
    def looks_like_english_source_fragment(cls, text: Any) -> bool:
        """Public facade for cross-service usage of looks_like_english_source_fragment."""
        return cls._looks_like_english_source_fragment(text)






