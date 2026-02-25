from __future__ import annotations

import re
import unicodedata
from typing import Any, Dict, Optional


class CatalogImportQualityService:
    """Heuristicas de qualidade para linhas extraidas de catalogo."""

    _PART_KEYWORDS = (
        "paralama",
        "para choque",
        "parachoque",
        "estrib",
        "ponteira",
        "cobertura",
        "porta",
        "grade",
        "tampa",
        "defletor",
        "farol",
        "mascara",
        "revest",
        "painel",
        "capo",
        "pisante",
        "suporte",
        "acabamento",
        "saia",
        "chapa",
        "moldura",
        "sinaleira",
        "lanterna",
        "painel",
        "grade frontal",
    )

    _APPLICATION_KEYWORDS = (
        "actros",
        "axor",
        "cargo",
        "volvo",
        "scania",
        "iveco",
        "mercedes",
        "facchini",
        "randon",
        "serie",
        "apos",
        "ate",
        "acima",
    )

    @staticmethod
    def alnum_len(value: Any) -> int:
        return len(re.sub(r"[^0-9A-Za-z]", "", str(value or "")))

    def text_has_context(self, value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        if self.alnum_len(text) < 4:
            return False
        if not re.search(r"[^\W\d_]", text, flags=re.UNICODE):
            return False
        if re.fullmatch(r"[-_=|./\s0-9]+", text):
            return False
        return True

    @staticmethod
    def fold_ascii_text(value: Any) -> str:
        folded = (
            unicodedata.normalize("NFKD", str(value or ""))
            .encode("ascii", errors="ignore")
            .decode("ascii")
            .lower()
        )
        folded = re.sub(r"[^a-z0-9]+", " ", folded)
        return re.sub(r"\s+", " ", folded).strip()

    def text_looks_like_part_name(self, value: Any) -> bool:
        text = self.fold_ascii_text(value)
        if not text:
            return False
        return any(keyword in text for keyword in self._PART_KEYWORDS)

    def text_looks_like_vehicle_application(self, value: Any) -> bool:
        text = self.fold_ascii_text(value)
        if not text:
            return False
        has_model = any(keyword in text for keyword in self._APPLICATION_KEYWORDS)
        has_year = bool(re.search(r"\b(?:19|20)\d{2}\b", text))
        has_part = self.text_looks_like_part_name(text)
        return (has_model or has_year) and not has_part

    @staticmethod
    def text_looks_like_part_code(value: Any) -> bool:
        text = str(value or "").strip()
        if not text:
            return False

        compact = re.sub(r"[^0-9A-Za-z]", "", text)
        if not compact:
            return False

        tokens = re.findall(r"[0-9A-Za-z./-]+", text)
        if not tokens or len(tokens) > 6:
            return False

        digit_ratio = sum(ch.isdigit() for ch in compact) / len(compact)
        has_lower = any(ch.isalpha() and ch.islower() for ch in text)

        code_tokens = 0
        for tok in tokens:
            tok_u = tok.upper()
            if not re.fullmatch(r"[0-9A-Z./-]+", tok_u):
                continue
            digits = sum(ch.isdigit() for ch in tok_u)
            letters = sum(ch.isalpha() for ch in tok_u)
            if digits >= 2:
                code_tokens += 1
                continue
            if digits >= 1 and letters >= 1:
                code_tokens += 1
                continue
            if tok_u in {"D", "E", "LD", "LE", "RH", "LH", "DIR", "ESQ"}:
                code_tokens += 1

        mostly_code_tokens = code_tokens >= max(1, len(tokens) - 1)
        if mostly_code_tokens and not has_lower and digit_ratio >= 0.35:
            return True
        if compact.isdigit() and len(compact) >= 3:
            return True
        return False

    def name_looks_like_annotation_header(self, value: Any) -> bool:
        text = self.fold_ascii_text(value)
        if not text:
            return False
        compact = re.sub(r"\s+", "", text)
        if compact in {"obs", "observacao", "observacoes", "anotacao", "anotacoes"}:
            return True
        if compact.startswith(("anotac", "anotag", "observac", "coment")):
            return True
        if compact.startswith("anota") and len(compact) <= 14 and not re.search(r"\d{2,}", compact):
            return True
        if compact.startswith("nota") and len(compact) <= 10:
            return True
        return False

    def name_looks_like_ocr_noise(self, value: Any) -> bool:
        text = self.fold_ascii_text(value)
        if not text:
            return False
        if self.text_looks_like_part_name(text) or self.name_looks_like_annotation_header(text):
            return False

        tokens = [tok for tok in text.split(" ") if tok]
        if not tokens:
            return False

        meaningful_alpha = [tok for tok in tokens if tok.isalpha() and len(tok) >= 4]
        if meaningful_alpha:
            return False

        numeric_tokens = [tok for tok in tokens if tok.isdigit()]
        short_alpha_tokens = [tok for tok in tokens if tok.isalpha() and len(tok) <= 3]
        mixed_tokens = [tok for tok in tokens if re.search(r"[a-z]", tok) and re.search(r"\d", tok)]

        if len(tokens) <= 3 and (short_alpha_tokens or mixed_tokens):
            if numeric_tokens or mixed_tokens:
                return True
            if sum(len(tok) for tok in tokens) <= 8:
                return True

        compact = "".join(tokens)
        if compact:
            letters = sum(ch.isalpha() for ch in compact)
            digits = sum(ch.isdigit() for ch in compact)
            if len(compact) <= 7 and letters <= 3 and digits >= 2:
                return True

        return False

    def evaluate_product_row_quality(self, data: Dict[str, Any]) -> Optional[str]:
        if not isinstance(data, dict):
            return "Linha descartada por baixa qualidade: formato invalido"

        nome = str(data.get("nome_base") or "").strip()
        sku = str(data.get("sku_original") or "").strip()
        ean = str(data.get("ean_original") or "").strip()
        descricao = str(data.get("descricao_original") or "").strip()
        marca = str(data.get("marca") or "").strip()
        categoria = str(data.get("categoria_original") or "").strip()
        dynamic_attributes = data.get("dynamic_attributes") or {}
        has_dynamic = isinstance(dynamic_attributes, dict) and any(
            self.text_has_context(v) for v in dynamic_attributes.values()
        )
        dynamic_part_context = isinstance(dynamic_attributes, dict) and any(
            self.text_looks_like_part_name(v) for v in dynamic_attributes.values()
        )
        has_context = any(
            (
                self.text_has_context(descricao),
                self.text_has_context(marca),
                self.text_has_context(categoria),
                has_dynamic,
            )
        )
        descricao_tem_contexto = self.text_has_context(descricao)
        categoria_tem_contexto = self.text_has_context(categoria)
        descricao_peca = self.text_looks_like_part_name(descricao)
        categoria_peca = self.text_looks_like_part_name(categoria)
        has_part_context = descricao_peca or categoria_peca or dynamic_part_context
        descricao_aplicacao = self.text_looks_like_vehicle_application(descricao)
        categoria_aplicacao = self.text_looks_like_vehicle_application(categoria)

        nome_alnum = self.alnum_len(nome)
        sku_alnum = self.alnum_len(sku)
        nome_compacto = re.sub(r"[^0-9A-Za-z]", "", nome).lower()
        sku_compacto = re.sub(r"[^0-9A-Za-z]", "", sku).lower()
        nome_numerico = bool(nome_compacto) and nome_compacto.isdigit()
        nome_codigo_peca = self.text_looks_like_part_code(nome)
        nome_ruido_ocr = self.name_looks_like_ocr_noise(nome)

        if self.name_looks_like_annotation_header(nome):
            return "Linha descartada por baixa qualidade: cabecalho de anotacoes"
        if nome_ruido_ocr and not has_part_context:
            if descricao_aplicacao or categoria_aplicacao or not has_context:
                return "Linha descartada por baixa qualidade: nome com padrao de ruido OCR"

        if not sku and not ean:
            if nome_ruido_ocr and not has_part_context:
                return "Linha descartada por baixa qualidade: nome com padrao de ruido OCR"
            if nome_codigo_peca and not has_part_context:
                if descricao_aplicacao or categoria_aplicacao:
                    return "Linha descartada por baixa qualidade: codigo sem descricao de peca"
            if nome_alnum < 3:
                return "Linha descartada por baixa qualidade: nome fraco sem SKU/EAN"
            tokens_nome = re.findall(r"[0-9A-Za-z]+", nome)
            alpha_tokens = [tok for tok in tokens_nome if re.search(r"[A-Za-z]", tok)]
            strong_alpha = any(len(re.sub(r"[^A-Za-z]", "", tok)) >= 4 for tok in alpha_tokens)
            if not has_context and not strong_alpha:
                return "Linha descartada por baixa qualidade: nome sem termo forte sem SKU/EAN"
            if nome_compacto:
                digits_ratio_nome = sum(ch.isdigit() for ch in nome_compacto) / len(nome_compacto)
                if digits_ratio_nome >= 0.55 and not has_context and len(tokens_nome) <= 5:
                    return "Linha descartada por baixa qualidade: nome numerico sem contexto sem SKU/EAN"
            if len(tokens_nome) == 1 and len(tokens_nome[0]) <= 2:
                return "Linha descartada por baixa qualidade: nome curto isolado"
            if len(tokens_nome) == 1 and not has_context:
                return "Linha descartada por baixa qualidade: nome isolado sem contexto"
            if not has_context and nome_alnum < 6:
                return "Linha descartada por baixa qualidade: nome curto sem contexto"
            if not has_context and nome and nome.upper() == nome and len(tokens_nome) <= 2:
                return "Linha descartada por baixa qualidade: nome em caixa alta sem contexto"

        if sku and sku_alnum <= 2 and not any(ch.isdigit() for ch in sku):
            return "Linha descartada por baixa qualidade: SKU sem digitos"
        if sku and nome and sku_compacto and sku_compacto == nome_compacto and not has_part_context:
            return "Linha descartada por baixa qualidade: SKU duplicado em nome sem descricao"
        if sku and nome_ruido_ocr and not has_part_context:
            if descricao_aplicacao or categoria_aplicacao or not has_context:
                return "Linha descartada por baixa qualidade: SKU com nome fraco sem descricao de peca"
        if sku and nome_numerico and not has_part_context:
            return "Linha descartada por baixa qualidade: nome numerico sem contexto"
        if sku and nome_numerico and sku_compacto == nome_compacto and not has_part_context:
            return "Linha descartada por baixa qualidade: nome numerico igual ao SKU sem descricao"
        if sku and not nome and not has_part_context:
            return "Linha descartada por baixa qualidade: SKU sem nome/descricao confiavel"
        if sku and nome_codigo_peca and not has_part_context:
            if descricao_aplicacao or categoria_aplicacao:
                return "Linha descartada por baixa qualidade: SKU com codigo e apenas aplicacao"
            if not has_context:
                return "Linha descartada por baixa qualidade: SKU com codigo sem descricao confiavel"
        if sku and not nome and not has_context:
            return "Linha descartada por baixa qualidade: SKU sem contexto"

        if nome:
            if nome_alnum < 2:
                return "Linha descartada por baixa qualidade: nome sem conteudo"
            tokens_nome = re.findall(r"[0-9A-Za-z]+", nome)
            if len(tokens_nome) == 1 and len(tokens_nome[0]) <= 1 and not sku:
                return "Linha descartada por baixa qualidade: nome muito curto"
            if nome_compacto:
                digits_ratio = sum(ch.isdigit() for ch in nome_compacto) / len(nome_compacto)
                if digits_ratio >= 0.85 and not has_context and (not sku or sku_compacto == nome_compacto):
                    return "Linha descartada por baixa qualidade: nome numerico sem contexto"
                if nome_numerico and len(nome_compacto) <= 6 and not descricao_tem_contexto:
                    return "Linha descartada por baixa qualidade: nome apenas numerico sem descricao"
                if nome_codigo_peca and not has_part_context and digits_ratio >= 0.45:
                    if descricao_aplicacao or categoria_aplicacao or not has_context:
                        return "Linha descartada por baixa qualidade: nome em formato de codigo sem contexto"

        return None

    def score_product_row_quality(self, data: Dict[str, Any]) -> int:
        if not isinstance(data, dict):
            return 0

        nome = str(data.get("nome_base") or "").strip()
        sku = str(data.get("sku_original") or "").strip()
        descricao = str(data.get("descricao_original") or "").strip()
        categoria = str(data.get("categoria_original") or "").strip()
        dynamic_attributes = data.get("dynamic_attributes") or {}

        nome_compacto = re.sub(r"[^0-9A-Za-z]", "", nome).lower()
        sku_compacto = re.sub(r"[^0-9A-Za-z]", "", sku).lower()
        nome_numerico = bool(nome_compacto) and nome_compacto.isdigit()
        nome_igual_sku = bool(nome_compacto and sku_compacto and nome_compacto == sku_compacto)
        nome_codigo_peca = self.text_looks_like_part_code(nome)

        score = 35
        if sku and any(ch.isdigit() for ch in sku):
            score += 20
        if sku and self.alnum_len(sku) >= 8:
            score += 5

        if self.text_has_context(nome):
            score += 20
        elif nome:
            score += 8

        if self.text_has_context(descricao):
            score += 14
        if self.text_has_context(categoria):
            score += 6

        if isinstance(dynamic_attributes, dict):
            dynamic_hits = sum(1 for v in dynamic_attributes.values() if self.text_has_context(v))
            score += min(dynamic_hits * 4, 12)

        if self.text_looks_like_part_name(descricao):
            score += 8
        if self.text_looks_like_part_name(categoria):
            score += 8

        if nome_igual_sku:
            score -= 28
        if nome_numerico:
            score -= 18
        if nome_codigo_peca:
            score -= 12
        if not self.text_has_context(nome) and sku:
            score -= 10
        if self.text_looks_like_vehicle_application(descricao):
            score -= 8
        if self.text_looks_like_vehicle_application(categoria):
            score -= 6

        return max(0, min(100, int(score)))

    def classify_product_row_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        strict_reason = self.evaluate_product_row_quality(data)
        score = self.score_product_row_quality(data)

        if strict_reason:
            return {
                "decision": "discard",
                "score": score,
                "reason": strict_reason,
            }

        nome = str(data.get("nome_base") or "").strip()
        sku = str(data.get("sku_original") or "").strip()
        descricao = str(data.get("descricao_original") or "").strip()
        categoria = str(data.get("categoria_original") or "").strip()

        nome_compacto = re.sub(r"[^0-9A-Za-z]", "", nome).lower()
        sku_compacto = re.sub(r"[^0-9A-Za-z]", "", sku).lower()
        nome_igual_sku = bool(nome_compacto and sku_compacto and nome_compacto == sku_compacto)
        nome_numerico = bool(nome_compacto) and nome_compacto.isdigit()
        nome_codigo_peca = self.text_looks_like_part_code(nome)
        nome_ruido_ocr = self.name_looks_like_ocr_noise(nome)

        descricao_peca = self.text_looks_like_part_name(descricao)
        categoria_peca = self.text_looks_like_part_name(categoria)
        descricao_aplicacao = self.text_looks_like_vehicle_application(descricao)
        categoria_aplicacao = self.text_looks_like_vehicle_application(categoria)

        if nome_ruido_ocr and not descricao_peca and not categoria_peca:
            reason = "Linha em quarentena: nome com padrao de ruido OCR"
            if descricao_aplicacao or categoria_aplicacao:
                reason = "Linha em quarentena: nome fraco e contexto apenas de aplicacao"
            return {
                "decision": "quarantine",
                "score": min(score, 50),
                "reason": reason,
            }

        if (nome_igual_sku or nome_codigo_peca) and not descricao_peca and not categoria_peca:
            reason = "Linha em quarentena: nome parece codigo sem descricao confiavel"
            if descricao_aplicacao or categoria_aplicacao:
                reason = "Linha em quarentena: nome parece codigo e contexto indica apenas aplicacao"
            return {
                "decision": "quarantine",
                "score": min(score, 55),
                "reason": reason,
            }

        if nome_numerico and not descricao_peca and not categoria_peca:
            return {
                "decision": "quarantine",
                "score": min(score, 52),
                "reason": "Linha em quarentena: nome parece apenas codigo sem contexto de peca",
            }

        if nome_codigo_peca and (descricao_aplicacao or categoria_aplicacao) and not descricao_peca and not categoria_peca:
            return {
                "decision": "quarantine",
                "score": min(score, 54),
                "reason": "Linha em quarentena: codigo sem descricao de peca",
            }

        if score < 45:
            return {
                "decision": "quarantine",
                "score": score,
                "reason": "Linha em quarentena: score de qualidade muito baixo",
            }

        if score < 58 and not self.text_has_context(nome) and not descricao_peca:
            return {
                "decision": "quarantine",
                "score": score,
                "reason": "Linha em quarentena: contexto fraco para nome do produto",
            }

        return {"decision": "accept", "score": score, "reason": None}
