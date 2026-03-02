"""Module web enrichment payload service.

Contains backend logic related to web enrichment payload service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import re


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

    def __init__(self, *, normalization_service: Any) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._normalization = normalization_service

    def _contains_part_hint(self, text_folded: str) -> bool:
        """Run contains part hint in this workflow."""
        return any(hint in text_folded for hint in self._PART_NAME_HINTS)

    def _looks_like_application_only(self, value: Any) -> bool:
        """Run looks like application only in this workflow."""
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
        """Run is weak existing field in this workflow."""
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
            return False

        if field_name in {"descricao_original", "descricao_chat_api"}:
            if len(folded) < 20:
                return True
            if self._looks_like_application_only(text):
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

    def _is_weak_dynamic_value(self, attr_key: str, value: Any) -> bool:
        """Run is weak dynamic value in this workflow."""
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
        if ("id" == attr_norm or "codigo" in attr_norm) and self._normalization.is_suspicious_code(text):
            return True
        if ("aplic" in attr_norm or "application" in attr_norm) and folded in {"todos", "todas", "geral"}:
            return True
        if "material" in attr_norm and folded in {"todos", "todas", "geral"}:
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
        """Run apply if empty or weak in this workflow."""
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
        """Run set dynamic if empty in this workflow."""
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
                if candidate_norm == known_norm:
                    target_key = known_key
                    break
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
            self._normalization.first_non_empty([
                dados_extraidos_agregados.get("descricao_detalhada_seo"),
                dados_extraidos_agregados.get("descricao_curta"),
                dados_extraidos_agregados.get("texto_relevante_coletado"),
            ]),
            max_len=10000,
        )
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
            field_name="descricao_chat_api",
            current_value=db_produto_obj.descricao_chat_api,
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

        specs = dados_extraidos_agregados.get("especificacoes_tecnicas_dict")
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
