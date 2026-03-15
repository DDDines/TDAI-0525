"""Document web enrichment normalization service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from html import unescape
import re
import unicodedata
from urllib.parse import unquote


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
        # Conta caracteres típicos de mojibake UTF-8->latin1/cp1252.
        # A versão anterior usava tokens multi-char ("Ãƒ"), o que nunca
        # batia com chars individuais iterados em `candidate`.
        """Execute encoding marker count as part of this module workflow."""
        if not candidate:
            return 0
        return sum(
            candidate.count(ch)
            for ch in ("\u00c3", "\u00c2", "\u00e2", "\u0192", "\ufffd")
        )

    def _has_markers(self, candidate: str) -> bool:
        """Execute has markers as part of this module workflow."""
        return self._encoding_marker_count(candidate) > 0 or "??" in candidate

    @staticmethod
    def _decode_maybe(candidate: str, source_encoding: str) -> str:
        """Decode maybe for secure downstream consumption."""
        try:
            return candidate.encode(source_encoding).decode("utf-8")
        except Exception:
            return candidate

    def normalize_human_text(self, value: Any) -> str:
        """Normalize human text to keep behavior consistent across callers."""
        text = str(value or "")
        if not text:
            return ""

        for _ in range(3):
            decoded = unquote(text)
            if decoded == text:
                break
            text = decoded
        text = unescape(text)
        text = re.sub(r"[?&](?:utm_[^=\s]+|fbclid|gclid|msclkid|vqd|ig|cid)=[^\s&]+", "", text)
        text = re.sub(r"https?://[^\s]+", lambda match: unquote(match.group(0)), text)

        for _ in range(6):
            if not self._has_markers(text):
                break
            best = text
            best_markers = self._encoding_marker_count(best)
            best_alnum = sum(ch.isalnum() for ch in best)
            for source_encoding in ("cp1252", "latin-1"):
                decoded = self._decode_maybe(text, source_encoding)
                if not decoded or decoded == text:
                    continue
                decoded_markers = self._encoding_marker_count(decoded)
                decoded_alnum = sum(ch.isalnum() for ch in decoded)
                alnum_guard = decoded_alnum >= int(best_alnum * 0.8)
                if decoded_markers < best_markers and alnum_guard:
                    best = decoded
                    best_markers = decoded_markers
                    best_alnum = decoded_alnum
            if best == text:
                break
            text = best

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
        text = text.replace("\xad", "")
        for src, dst in replacements.items():
            text = text.replace(src, dst)
        text = text.replace("p´de", "pôde").replace("P´de", "Pôde")
        text = text.replace("extra­do", "extraído").replace("extra­vel", "extraível")
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def fold_text(value: Any) -> str:
        """Execute fold text as part of this module workflow."""
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = text.encode("ascii", "ignore").decode("ascii")
        text = re.sub(r"[^a-zA-Z0-9]+", " ", text).lower()
        return re.sub(r"\s+", " ", text).strip()

    def is_empty(self, value: Any) -> bool:
        """Execute is empty as part of this module workflow."""
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
        """Execute as text as part of this module workflow."""
        if self.is_empty(value):
            return None
        if isinstance(value, (list, tuple, set)):
            parts = [str(v).strip() for v in value if not self.is_empty(v)]
            text = " | ".join(parts)
        else:
            text = str(value).strip()
        if not text:
            return None
        text = self.normalize_human_text(text)
        if not text:
            return None
        return text[:max_len] if len(text) > max_len else text

    def first_non_empty(self, values: List[Any]) -> Optional[Any]:
        """Execute first non empty as part of this module workflow."""
        for value in values:
            if not self.is_empty(value):
                return value
        return None

    @staticmethod
    def parse_price(value: Any) -> Optional[float]:
        """Parse price into structured data used by downstream logic."""
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
        """Execute sanitize code value as part of this module workflow."""
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
        """Execute is suspicious code as part of this module workflow."""
        text = self.sanitize_code_value(value)
        if not text:
            return False
        return any(
            str(value or "").upper().endswith(suffix)
            for suffix in ("MARCA", "MATERIAL", "PESO", "QUANTIDADE", "ATENCAO")
        )

    def extract_signals_from_description(self, text: Any) -> Dict[str, str]:
        """Execute extract signals from description as part of this module workflow."""
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
        """Execute is placeholder value as part of this module workflow."""
        text = self.as_text(value, max_len=1000)
        if not text:
            return True
        folded = self.fold_text(text)
        return not folded or folded in self._PLACEHOLDER_HINTS
