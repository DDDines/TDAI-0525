from __future__ import annotations

from typing import Any, Dict, Optional
import re
import unicodedata


class WebEnrichmentNormalizationService:
    """Centraliza normalizacao de texto e sinais para enriquecimento web."""

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

    def _encoding_marker_count(self, candidate: str) -> int:
        return sum(1 for ch in candidate if ch in {"Ãƒ", "Ã‚", "\ufffd"})

    def normalize_human_text(self, value: Any) -> str:
        text = str(value or "")
        if not text:
            return ""

        def _has_markers(candidate: str) -> bool:
            return self._encoding_marker_count(candidate) > 0 or "??" in candidate

        for _ in range(4):
            if not _has_markers(text):
                break
            try:
                decoded = bytes((ord(ch) & 0xFF for ch in text)).decode("utf-8")
            except Exception:
                break
            if not decoded or decoded == text:
                break
            if self._encoding_marker_count(decoded) <= self._encoding_marker_count(text):
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
            "nÃƒÂ£o": "não",
            "NÃƒÂ£o": "Não",
            "pÃƒÂ´de": "pôde",
            "pÃƒÂ¡gina": "página",
            "PÃƒÂ¡gina": "Página",
            "descriÃƒÂ§ÃƒÂ£o": "descrição",
            "DescriÃƒÂ§ÃƒÂ£o": "Descrição",
            "conteÃƒÂºdo": "conteúdo",
            "extraÃƒÂ§ÃƒÂ£o": "extração",
            "extraÃƒÂ­vel": "extraível",
            "situaÃƒÂ§ÃƒÂ£o": "situação",
            "configuraÃƒÂ§ÃƒÂ£o": "configuração",
            "ConfiguraÃƒÂ§ÃƒÂ£o": "Configuração",
        }
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def fold_text(value: Any) -> str:
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
        return re.sub(r"\s+", " ", text).strip()

    def is_empty(self, value: Any) -> bool:
        if value is None:
            return True
        if isinstance(value, str):
            raw = value.strip()
            if not raw:
                return True
            folded = self.fold_text(raw)
            return folded in {"none", "null", "nan", "na", "n a", "-", "--"}
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) == 0
        return False

    def as_text(self, value: Any, max_len: int = 8000) -> Optional[str]:
        if self.is_empty(value):
            return None
        if isinstance(value, (list, tuple, set)):
            parts = [str(v).strip() for v in value if not self.is_empty(v)]
            text = " | ".join(parts)
        else:
            text = str(value).strip()
        if not text:
            return None
        return text[:max_len] if len(text) > max_len else text

    def first_non_empty(self, *values: Any) -> Optional[Any]:
        for value in values:
            if not self.is_empty(value):
                return value
        return None

    @staticmethod
    def parse_price(value: Any) -> Optional[float]:
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

    def sanitize_code_value(self, value: Any) -> Optional[str]:
        text = self.as_text(value, max_len=120)
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
        for suffix in (
            "MARCA",
            "MATERIAL",
            "PESO",
            "QUANTIDADE",
            "REFERENCIA",
            "CODIGO",
            "ATENCAO",
        ):
            if clean.endswith(suffix) and len(clean) > len(suffix) + 2:
                clean = clean[: -len(suffix)]
                break
        clean = clean.strip("-./")
        return clean or None

    def is_suspicious_code(self, value: Any) -> bool:
        text = self.sanitize_code_value(value)
        if not text:
            return False
        return any(
            str(value or "").upper().endswith(suffix)
            for suffix in ("MARCA", "MATERIAL", "PESO", "QUANTIDADE", "ATENCAO")
        )

    def extract_signals_from_description(self, text: Any) -> Dict[str, str]:
        raw = self.as_text(text, max_len=12000)
        if not raw:
            return {}

        compact = re.sub(r"\s+", " ", raw)
        normalized = (
            unicodedata.normalize("NFKD", compact).encode("ascii", "ignore").decode("ascii")
        )
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

    def is_placeholder_value(self, value: Any) -> bool:
        text = self.as_text(value, max_len=1000)
        if not text:
            return True
        folded = self.fold_text(text)
        return not folded or folded in self._PLACEHOLDER_HINTS
