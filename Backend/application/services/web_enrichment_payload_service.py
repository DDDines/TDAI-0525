"""Document web enrichment payload service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re

from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)


class WebEnrichmentPayloadService:
    """Constroi payload visivel de enriquecimento mantendo regras de qualidade."""

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
    _COMPANY_ENTITY_HINT_PATTERN = re.compile(
        r"\b(?:empresa|marca|fabricante|industria|loja|grupo|nos|nossa|historia|tradicao|mercado)\b",
        re.IGNORECASE,
    )
    _PROMOTIONAL_TEXT_PATTERN = re.compile(
        r"\b(?:garanta|aproveite|compre|compra\s+online|clique\s+aqui|criptografia|"
        r"seguran[cç]a|tranquilidade|satisfa[cç][aã]o|politica\s+de\s+(?:troca|devolu[cç][aã]o)|"
        r"devolu[cç][aã]o|whatsapp|telefone|atendimento|parcelamento|sem\s+juros)\b",
        re.IGNORECASE,
    )
    _SELLER_BRAND_PATTERN = re.compile(
        r"\b(?:loja|com[eé]rcio|auto\s*pe[cç]as|atendimento|oficial|mercado|shop|store)\b",
        re.IGNORECASE,
    )
    _SELLER_BRAND_SUBSTRINGS = (
        "mercad",
        "pecas",
        "peças",
        "autop",
        "autopec",
        "roche",
    )

    _GENERIC_REFERENCE_TOKENS = {
        "tool",
        "tools",
        "toolkit",
        "kit",
        "kits",
        "set",
        "jogo",
        "jogos",
        "combo",
        "pack",
        "item",
        "itens",
        "produto",
        "produtos",
        "acessorio",
        "acessorios",
        "linha",
        "parts",
        "part",
        "geral",
        "gerais",
        "modelo",
    }
    _AUTOMOTIVE_MISMATCH_HINTS = (
        "estribo",
        "strada",
        "cabine",
        "dupla",
        "simples",
        "veiculo",
        "veiculos",
        "dianteiro",
        "traseiro",
        "lateral",
        "automotivo",
        "automotiva",
        "carro",
        "caminhao",
        "ford",
        "fiat",
        "iveco",
        "mercedes",
        "scania",
        "volks",
        "volvo",
        "pickup",
    )

    def __init__(
        self,
        *,
        normalization_service: Any,
        relevance_service: Any | None = None,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Web Enrichment Payload Service."""
        self._normalization = normalization_service
        self._relevance = relevance_service or WebEnrichmentRelevanceService()

    def _contains_part_hint(self, text_folded: str) -> bool:
        """Execute contains part hint as part of this module workflow."""
        return any(hint in text_folded for hint in self._PART_NAME_HINTS)

    def _candidate_tokens(self, value: Any) -> List[str]:
        """Normalize free text into compact validation tokens."""
        folded = self._normalization.fold_text(value)
        if not folded:
            return []
        return [token for token in folded.split() if len(token) >= 3]

    def _strong_seed_tokens(self, db_produto_obj: Any) -> List[str]:
        """Keep only the product-name tokens that truly anchor the seed identity."""
        nome_base = self._normalization.as_text(
            getattr(db_produto_obj, "nome_base", None),
            max_len=255,
        )
        marca = self._normalization.as_text(
            getattr(db_produto_obj, "marca", None),
            max_len=120,
        )
        brand_tokens = set(self._candidate_tokens(marca))
        strong_tokens: List[str] = []
        for token in self._candidate_tokens(nome_base):
            if token in brand_tokens:
                continue
            if token in self._GENERIC_REFERENCE_TOKENS:
                continue
            strong_tokens.append(token)
        return list(dict.fromkeys(strong_tokens))

    def _brand_tokens(self, db_produto_obj: Any) -> List[str]:
        """Extract brand tokens used to validate generic product seeds."""
        return list(
            dict.fromkeys(
                self._candidate_tokens(
                    self._normalization.as_text(
                        getattr(db_produto_obj, "marca", None),
                        max_len=120,
                    )
                )
            )
        )

    def _candidate_brand_text(self, value: Any) -> str:
        """Normalize candidate brand names for strict mismatch checks."""
        return self._normalization.fold_text(
            self._normalization.as_text(value, max_len=120)
        )

    @staticmethod
    def _count_hint_hits(text_folded: str, hints: Tuple[str, ...]) -> int:
        """Count how many distinct domain hints appear in the candidate text."""
        if not text_folded:
            return 0
        return sum(1 for hint in hints if hint in text_folded)

    def _build_payload_validation_text(
        self,
        *,
        nome_web: Optional[str],
        descricao_web: Optional[str],
        marca_web: Optional[str],
        sku_web: Optional[str],
        codigo_original_web: Optional[str],
        material_web: Optional[str],
        aplicacao_web: Optional[str],
        specs: Any,
    ) -> str:
        """Compose only the promotable payload fragments used to validate relevance."""
        parts: List[str] = [
            str(nome_web or ""),
            str(descricao_web or ""),
            str(marca_web or ""),
            str(sku_web or ""),
            str(codigo_original_web or ""),
            str(material_web or ""),
            str(aplicacao_web or ""),
        ]
        if isinstance(specs, dict):
            for key, value in list(specs.items())[:12]:
                parts.append(f"{key}: {value}")
        return " ".join(part for part in parts if str(part or "").strip())

    def _validate_payload_relevance(
        self,
        *,
        db_produto_obj: Any,
        nome_web: Optional[str],
        descricao_web: Optional[str],
        marca_web: Optional[str],
        sku_web: Optional[str],
        codigo_original_web: Optional[str],
        material_web: Optional[str],
        aplicacao_web: Optional[str],
        specs: Any,
    ) -> Tuple[bool, List[str]]:
        """Reject web payloads that clearly do not match the original product seed."""
        candidate_text = self._build_payload_validation_text(
            nome_web=nome_web,
            descricao_web=descricao_web,
            marca_web=marca_web,
            sku_web=sku_web,
            codigo_original_web=codigo_original_web,
            material_web=material_web,
            aplicacao_web=aplicacao_web,
            specs=specs,
        )
        if not candidate_text.strip():
            return True, []

        candidate_tokens = set(self._candidate_tokens(candidate_text))
        candidate_brand = self._candidate_brand_text(marca_web)
        candidate_folded = self._normalization.fold_text(candidate_text)
        candidate_compact = re.sub(r"[^A-Z0-9]", "", candidate_text.upper())

        seed_name_text = self._normalization.as_text(
            getattr(db_produto_obj, "nome_base", None),
            max_len=255,
        )
        seed_brand_tokens = self._brand_tokens(db_produto_obj)
        seed_brand_text = self._candidate_brand_text(
            getattr(db_produto_obj, "marca", None)
        )
        strong_seed_tokens = self._strong_seed_tokens(db_produto_obj)

        dados_brutos_web = getattr(db_produto_obj, "dados_brutos_web", None)
        seed_codes: List[Any] = [
            getattr(db_produto_obj, "sku", None),
            getattr(db_produto_obj, "ean", None),
            getattr(db_produto_obj, "nome_base", None),
        ]
        if isinstance(dados_brutos_web, dict):
            seed_codes.extend(
                [
                    dados_brutos_web.get("codigo_original"),
                    dados_brutos_web.get("sku_original"),
                ]
            )
        ref_code_tokens = self._relevance.extract_code_tokens(seed_codes)
        code_hit = any(
            re.sub(r"[^A-Z0-9]", "", token) in candidate_compact for token in ref_code_tokens
        )
        brand_hit = bool(
            seed_brand_text
            and (
                candidate_brand == seed_brand_text
                or any(token in candidate_tokens for token in seed_brand_tokens)
            )
        )
        strong_overlap = len([token for token in strong_seed_tokens if token in candidate_tokens])

        automotive_hits = self._count_hint_hits(
            candidate_folded,
            self._AUTOMOTIVE_MISMATCH_HINTS,
        )
        seed_folded = self._normalization.fold_text(
            self._normalization.as_text(getattr(db_produto_obj, "nome_base", None), max_len=255)
        )
        seed_automotive = self._count_hint_hits(
            seed_folded,
            self._AUTOMOTIVE_MISMATCH_HINTS,
        ) >= 2

        if not seed_name_text and not strong_seed_tokens and not ref_code_tokens:
            return True, []

        rejection_reasons: List[str] = []
        if (
            seed_name_text
            and seed_brand_text
            and candidate_brand
            and candidate_brand != seed_brand_text
            and not code_hit
        ):
            rejection_reasons.append("marca divergente da referencia do produto")

        if (
            seed_name_text
            and not strong_seed_tokens
            and seed_brand_tokens
            and not brand_hit
            and not code_hit
            and not candidate_brand
            and automotive_hits >= 3
        ):
            rejection_reasons.append("conteudo sem a marca de referencia do produto")

        if strong_seed_tokens:
            required_overlap = 1 if len(strong_seed_tokens) == 1 else 2
            if strong_overlap < required_overlap and not brand_hit and not code_hit:
                rejection_reasons.append(
                    "conteudo sem correspondencia suficiente com o nome base"
                )

        if automotive_hits >= 3 and not seed_automotive and not brand_hit and not code_hit:
            rejection_reasons.append("conteudo indica outra categoria/produto")

        return len(rejection_reasons) == 0, rejection_reasons

    def _looks_like_company_timeline_claim(self, value: Any) -> bool:
        """Detect unsupported company-history snippets for product descriptions."""
        text = self._normalization.as_text(value, max_len=2500)
        folded = self._normalization.fold_text(text)
        if not folded:
            return False
        if any(hint in folded for hint in self._COMPANY_TIMELINE_HINTS):
            return True
        if not self._COMPANY_TIMELINE_PATTERN.search(text):
            return False
        return bool(self._COMPANY_ENTITY_HINT_PATTERN.search(text))

    def _sanitize_description_text(self, value: Any, *, max_len: int = 10000) -> str:
        """Remove company-history claims from description-like fields."""
        text = self._normalization.as_text(value, max_len=max_len)
        if not text:
            return ""
        parts = re.split(r"(?<=[.!?])\s+|[\n\r]+", text)
        filtered_parts: List[str] = []
        for part in parts:
            chunk = self._normalization.as_text(part, max_len=max_len)
            if not chunk:
                continue
            if self._looks_like_company_timeline_claim(chunk):
                continue
            filtered_parts.append(chunk)
        if filtered_parts:
            return self._normalization.as_text(" ".join(filtered_parts), max_len=max_len)
        return text

    def _looks_like_promotional_or_store_text(self, value: Any) -> bool:
        """Detect marketplace/promotional text that should not survive as product identity."""
        text = self._normalization.as_text(value, max_len=2500)
        if not text:
            return False
        folded = self._normalization.fold_text(text)
        if not folded:
            return False
        if self._PROMOTIONAL_TEXT_PATTERN.search(text):
            return True
        if self._SELLER_BRAND_PATTERN.search(text):
            return True
        if len(folded.split()) <= 6 and any(marker in folded for marker in self._SELLER_BRAND_SUBSTRINGS):
            return True
        return False

    def _select_visible_description(self, dados_extraidos_agregados: Dict[str, Any]) -> str:
        """Prefer concise grounded descriptions over heuristic SEO dumps for visible product fields."""
        descricao_curta = self._normalization.as_text(
            dados_extraidos_agregados.get("descricao_curta"),
            max_len=1000,
        )
        descricao_detalhada = self._normalization.as_text(
            dados_extraidos_agregados.get("descricao_detalhada_seo"),
            max_len=10000,
        )
        texto_relevante = self._normalization.as_text(
            dados_extraidos_agregados.get("texto_relevante_coletado"),
            max_len=10000,
        )

        if descricao_detalhada:
            lowered = self._normalization.fold_text(descricao_detalhada)
            if (
                dados_extraidos_agregados.get("fonte_principal_fornecedor")
                and (
                    "url da fonte" in lowered
                    or "controle sua privacidade" in lowered
                    or "destaques:" in lowered
                    or "especificacoes:" in lowered
                )
            ):
                descricao_detalhada = ""

        return self._normalization.first_non_empty(
            [
                descricao_curta,
                descricao_detalhada,
                texto_relevante,
            ]
        )

    def _looks_like_structured_dump(self, value: Any) -> bool:
        """Detect label-heavy raw dumps that should not be surfaced verbatim to users."""
        text = self._normalization.as_text(value, max_len=4000)
        if not text:
            return False
        lowered = self._normalization.fold_text(text)
        if (
            "url da fonte" in lowered
            or "controle sua privacidade" in lowered
            or "esse site utiliza cookies" in lowered
            or "destaques:" in lowered
            or "especificacoes:" in lowered
        ):
            return True
        label_hits = re.findall(
            r"\b(?:codigo|referencia|aplicacao|material|conteudo|caminho do catalogo|url da fonte)\s*[:\-]",
            lowered,
        )
        return len(label_hits) >= 3

    def _looks_like_application_only(self, value: Any) -> bool:
        """Execute looks like application only as part of this module workflow."""
        text = self._normalization.as_text(value, max_len=500)
        if not text:
            return False
        folded = self._normalization.fold_text(text)
        if not folded:
            return False
        has_application_hint = any(hint in folded for hint in self._APPLICATION_HINTS)
        has_year = bool(re.search(r"\b(19|20)\d{2}\b", folded))
        has_range = bool(re.search(r"\b\d{4}\s*-\s*\d{4}\b", text))
        few_words = len(folded.split()) <= 10
        return has_application_hint and (has_year or has_range) and few_words and not self._contains_part_hint(folded)

    def _is_weak_existing_field(self, field_name: str, value: Any) -> bool:
        """Execute is weak existing field as part of this module workflow."""
        text = self._normalization.as_text(value, max_len=2500)
        if not text:
            return True
        folded = self._normalization.fold_text(text)
        if not folded:
            return True
        if folded in self._PLACEHOLDER_HINTS:
            return True

        if field_name == "nome_chat_api":
            if len(folded) < 8:
                return True
            if re.fullmatch(r"[0-9./\-\s]+", text):
                return True
            if self._looks_like_application_only(text):
                return True
            if self._looks_like_promotional_or_store_text(text):
                return True
            return False

        if field_name == "descricao_original":
            if len(folded) < 20:
                return True
            if self._looks_like_application_only(text):
                return True
            if "anotac" in folded or "observac" in folded:
                return True
            if self._looks_like_structured_dump(text):
                return True
            if self._looks_like_promotional_or_store_text(text):
                return True
            return False

        if field_name == "marca":
            if len(folded) < 3:
                return True
            if folded in {"sm", "s m", "sem marca", "generico"}:
                return True
            if self._looks_like_promotional_or_store_text(text):
                return True
            return False

        return False

    def _is_weak_dynamic_value(self, attr_key: str, value: Any) -> bool:
        """Execute is weak dynamic value as part of this module workflow."""
        text = self._normalization.as_text(value, max_len=1500)
        if not text:
            return True
        folded = self._normalization.fold_text(text)
        if not folded:
            return True
        if folded in self._PLACEHOLDER_HINTS:
            return True

        attr_norm = self._normalization.fold_text(attr_key)
        if ("descr" in attr_norm or attr_norm == "titulo") and len(folded) < 12:
            return True
        if "descr" in attr_norm and self._looks_like_application_only(text):
            return True
        if ("descr" in attr_norm or "desc" in attr_norm) and self._looks_like_structured_dump(text):
            return True
        if ("descr" in attr_norm or "desc" in attr_norm or "titulo" in attr_norm or "marca" in attr_norm) and self._looks_like_promotional_or_store_text(text):
            return True
        if ("titulo" in attr_norm or "marca" in attr_norm) and any(marker in folded for marker in self._SELLER_BRAND_SUBSTRINGS):
            return True
        if ("id" == attr_norm or "codigo" in attr_norm) and self._normalization.is_suspicious_code(text):
            return True
        return False

    def _apply_if_empty_or_weak(
        self,
        *,
        field_name: str,
        current_value: Any,
        new_value: Any,
        update_fields: Dict[str, Any],
        notes: List[str],
        ignored_notes: List[str],
        allow_replace_weak: bool = False,
    ) -> None:
        """Apply if empty or weak."""
        if self._normalization.is_empty(new_value):
            return
        if self._normalization.is_empty(current_value):
            update_fields[field_name] = new_value
            notes.append(field_name)
            return
        if (
            allow_replace_weak
            and self._is_weak_existing_field(field_name, current_value)
            and not self._is_weak_existing_field(field_name, new_value)
        ):
            update_fields[field_name] = new_value
            notes.append(f"{field_name}:substituido_valor_fraco")
            return
        ignored_notes.append(f"{field_name}:mantido_valor_existente")

    def _set_dynamic_if_empty(
        self,
        *,
        candidates: List[str],
        value: Any,
        dynamic_current: Dict[str, Any],
        normalized_key_to_real: Dict[str, str],
        dynamic_ignored: List[str],
        allow_replace_suspicious: bool = False,
        allow_replace_weak: bool = False,
    ) -> Optional[str]:
        """Execute set dynamic if empty as part of this module workflow."""
        text_value = self._normalization.as_text(value)
        value_from_existing = False
        if not text_value:
            for candidate in candidates:
                candidate_norm = self._normalization.fold_text(candidate)
                for current_key, current_val in dynamic_current.items():
                    current_norm = self._normalization.fold_text(current_key)
                    if candidate_norm == current_norm or candidate_norm in current_norm:
                        maybe_value = self._normalization.as_text(current_val)
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
            candidate_norm = self._normalization.fold_text(candidate)
            if candidate_norm in normalized_key_to_real:
                target_key = normalized_key_to_real[candidate_norm]
                break
            for known_norm, known_key in normalized_key_to_real.items():
                if not known_norm or not candidate_norm:
                    continue
                if candidate_norm == "descricao" and "desc" in known_norm:
                    target_key = known_key
                    break
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
        current_text = self._normalization.as_text(current_value)
        if self._normalization.is_empty(current_value):
            dynamic_current[target_key] = text_value
            return target_key
        if value_from_existing and current_text == text_value:
            return None
        if allow_replace_suspicious and self._normalization.is_suspicious_code(current_value):
            dynamic_current[target_key] = text_value
            return target_key
        if (
            allow_replace_weak
            and self._is_weak_dynamic_value(target_key, current_value)
            and not self._is_weak_dynamic_value(target_key, text_value)
        ):
            dynamic_current[target_key] = text_value
            return target_key

        dynamic_ignored.append(str(target_key))
        return None

    def build_payload_enriquecimento_visivel(
        self,
        db_produto_obj: Any,
        dados_extraidos_agregados: Dict[str, Any],
    ) -> Tuple[Dict[str, Any], List[str], List[str]]:
        """Converte dados extraidos da web em campos visiveis no modal de produto."""
        update_fields: Dict[str, Any] = {}
        notes: List[str] = []
        ignored_notes: List[str] = []

        nome_web = self._normalization.as_text(
            self._normalization.first_non_empty([
                dados_extraidos_agregados.get("nome_sugerido_seo"),
                dados_extraidos_agregados.get("nome"),
            ]),
            max_len=255,
        )
        descricao_web = self._normalization.as_text(
            self._select_visible_description(dados_extraidos_agregados),
            max_len=10000,
        )
        descricao_web = self._sanitize_description_text(descricao_web, max_len=10000)
        imagem_url_web = self._normalization.as_text(
            dados_extraidos_agregados.get("imagem_url"),
            max_len=2000,
        )
        marca_web = self._normalization.as_text(
            dados_extraidos_agregados.get("marca"),
            max_len=100,
        )
        sku_web = self._normalization.as_text(dados_extraidos_agregados.get("sku"), max_len=100)
        preco_web = self._normalization.parse_price(dados_extraidos_agregados.get("preco"))
        disponibilidade_web = self._normalization.as_text(
            dados_extraidos_agregados.get("disponibilidade"),
            max_len=120,
        )
        moeda_preco_web = self._normalization.as_text(
            dados_extraidos_agregados.get("moeda_preco"),
            max_len=12,
        )

        extracted_signals = self._normalization.extract_signals_from_description(descricao_web)
        for key, value in extracted_signals.items():
            if self._normalization.is_empty(dados_extraidos_agregados.get(key)):
                dados_extraidos_agregados[key] = value

        codigo_original_web = self._normalization.sanitize_code_value(
            self._normalization.first_non_empty([
                dados_extraidos_agregados.get("codigo_original"),
                dados_extraidos_agregados.get("sku_original"),
                sku_web,
            ])
        )
        if (
            codigo_original_web
            and dados_extraidos_agregados.get("codigo_original") != codigo_original_web
        ):
            dados_extraidos_agregados["codigo_original"] = codigo_original_web

        material_web = self._normalization.as_text(
            dados_extraidos_agregados.get("material"),
            max_len=120,
        )
        aplicacao_web = self._normalization.as_text(
            dados_extraidos_agregados.get("aplicacao"),
            max_len=400,
        )
        specs = dados_extraidos_agregados.get("especificacoes_tecnicas_dict")

        payload_relevante, payload_rejection_reasons = self._validate_payload_relevance(
            db_produto_obj=db_produto_obj,
            nome_web=nome_web,
            descricao_web=descricao_web,
            marca_web=marca_web,
            sku_web=sku_web,
            codigo_original_web=codigo_original_web,
            material_web=material_web,
            aplicacao_web=aplicacao_web,
            specs=specs,
        )
        dados_extraidos_agregados["validacao_relevancia_payload"] = {
            "aprovado": payload_relevante,
            "motivos": payload_rejection_reasons,
        }
        if not payload_relevante:
            ignored_notes.append(
                "validacao_relevancia="
                + "; ".join(payload_rejection_reasons)
            )
            return update_fields, notes, ignored_notes

        self._apply_if_empty_or_weak(
            field_name="nome_chat_api",
            current_value=db_produto_obj.nome_chat_api,
            new_value=nome_web,
            update_fields=update_fields,
            notes=notes,
            ignored_notes=ignored_notes,
            allow_replace_weak=True,
        )
        self._apply_if_empty_or_weak(
            field_name="descricao_original",
            current_value=db_produto_obj.descricao_original,
            new_value=descricao_web,
            update_fields=update_fields,
            notes=notes,
            ignored_notes=ignored_notes,
            allow_replace_weak=True,
        )
        self._apply_if_empty_or_weak(
            field_name="imagem_principal_url",
            current_value=db_produto_obj.imagem_principal_url,
            new_value=imagem_url_web,
            update_fields=update_fields,
            notes=notes,
            ignored_notes=ignored_notes,
        )
        self._apply_if_empty_or_weak(
            field_name="marca",
            current_value=db_produto_obj.marca,
            new_value=marca_web,
            update_fields=update_fields,
            notes=notes,
            ignored_notes=ignored_notes,
            allow_replace_weak=True,
        )
        self._apply_if_empty_or_weak(
            field_name="sku",
            current_value=db_produto_obj.sku,
            new_value=sku_web,
            update_fields=update_fields,
            notes=notes,
            ignored_notes=ignored_notes,
        )

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
            normalized_key_to_real[self._normalization.fold_text(current_key)] = current_key

        if db_produto_obj.product_type and db_produto_obj.product_type.attribute_templates:
            for tpl in db_produto_obj.product_type.attribute_templates:
                attr_key = getattr(tpl, "attribute_key", None)
                if attr_key:
                    normalized_key_to_real[self._normalization.fold_text(attr_key)] = attr_key
                label = getattr(tpl, "label", None)
                if attr_key and label:
                    normalized_key_to_real[self._normalization.fold_text(label)] = attr_key

        dynamic_ignored: List[str] = []

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
            target = self._set_dynamic_if_empty(
                candidates=aliases,
                value=value,
                dynamic_current=dynamic_current,
                normalized_key_to_real=normalized_key_to_real,
                dynamic_ignored=dynamic_ignored,
                allow_replace_suspicious=(aliases[0] in {"id", "codigo_original"}),
                allow_replace_weak=(
                    aliases[0] in {"titulo", "descricao", "material", "aplicacao", "marca"}
                ),
            )
            if target:
                dynamic_filled.append(target)

        if isinstance(specs, dict):
            for key, value in specs.items():
                if self._normalization.is_empty(key):
                    continue
                target = self._set_dynamic_if_empty(
                    candidates=[str(key)],
                    value=value,
                    dynamic_current=dynamic_current,
                    normalized_key_to_real=normalized_key_to_real,
                    dynamic_ignored=dynamic_ignored,
                )
                if target:
                    dynamic_filled.append(target)

        if dynamic_current != dynamic_before:
            update_fields["dynamic_attributes"] = dynamic_current
            unique_dynamic = list(dict.fromkeys(dynamic_filled))
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
