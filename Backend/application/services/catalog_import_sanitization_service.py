from __future__ import annotations

from typing import Any, Dict
import json
import re

from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)


class CatalogImportSanitizationService:
    """Centraliza normalizacao/sanitizacao textual da importacao de catalogo."""

    def __init__(self, quality_service: CatalogImportQualityService) -> None:
        self._quality = quality_service

    def normalize_import_text(self, value: str) -> str:
        """Corrige artefatos comuns de encoding em mensagens de importacao."""
        text = str(value or "")

        def _marker_count(candidate: str) -> int:
            return sum(
                candidate.count(ch)
                for ch in ("\u00c3", "\u00c2", "\u00e2", "\u0192", "\ufffd")
            )

        def _looks_mojibake(candidate: str) -> bool:
            return _marker_count(candidate) > 0 or "??" in candidate

        def _decode_maybe(candidate: str, source_encoding: str) -> str:
            try:
                return candidate.encode(source_encoding).decode("utf-8")
            except Exception:
                return candidate

        # Tenta corrigir mojibake comum (UTF-8 lido como latin-1/cp1252).
        for _ in range(6):
            if not _looks_mojibake(text):
                break

            best = text
            best_markers = _marker_count(best)
            best_alnum = sum(ch.isalnum() for ch in best)
            for source_encoding in ("cp1252", "latin-1"):
                decoded = _decode_maybe(text, source_encoding)
                if not decoded or decoded == text:
                    continue
                decoded_markers = _marker_count(decoded)
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
            "não": "não",
            "nÃ£o": "não",
            "nao": "não",
            "Página": "Página",
            "página": "página",
            "PÃ¡gina": "Página",
            "pÃ¡gina": "página",
            "PÃƒÂ¡gina": "Página",
            "pÃƒÂ¡gina": "página",
            "pôde": "pôde",
            "pÃ´de": "pôde",
            "pÃƒÂ´de": "pôde",
            "p??de": "pôde",
            "p????de": "pôde",
            "extraído": "extraído",
            "extraível": "extraível",
            "extraÃ­do": "extraído",
            "extraÃ­vel": "extraível",
            "extraÃƒÂ­do": "extraído",
            "extraÃƒÂ­vel": "extraível",
            "extraido": "extraído",
            "extraivel": "extraível",
            "catálogo": "catálogo",
            "catÃ¡logo": "catálogo",
            "catalogo": "catálogo",
            "Conteúdo": "Conteúdo",
            "conteúdo": "conteúdo",
            "ConteÃºdo": "Conteúdo",
            "conteÃºdo": "conteúdo",
            "conteudo": "conteúdo",
            "possível": "possível",
            "possÃ­vel": "possível",
            "possivel": "possível",
            "inválido": "inválido",
            "invÃ¡lido": "inválido",
            "invalido": "inválido",
            "crítico": "crítico",
            "crítica": "crítica",
            "crÃ­tico": "crítico",
            "crÃ­tica": "crítica",
            "critico": "crítico",
            "critica": "crítica",
            "criticos": "críticos",
            "relatório": "relatório",
            "Relatório": "Relatório",
            "relatorio": "relatório",
            "Relatorio": "Relatório",
            "Importação": "Importação",
            "importação": "importação",
            "Importacao": "Importação",
            "importacao": "importação",
            "descri??o": "descrição",
            "descricao": "descrição",
            "ordena??o": "ordenação",
            "ordenacao": "ordenação",
            "p?s-valida??o": "pós-validação",
            "p?s valida??o": "pós validação",
            "não críticos": "não críticos",
            "nao criticos": "não críticos",
            "nÃƒÂ£o crÃ­ticos": "não críticos",
            "não crítica": "não crítica",
            "nao critica": "não crítica",
            "nÃƒÂ£o crÃ­tica": "não crítica",
            "não disponíveis": "não disponíveis",
            "nao disponiveis": "não disponíveis",
            "obrigatório": "obrigatório",
            "obrigatorio": "obrigatório",
            "concluída": "concluída",
            "concluida": "concluída",
            "RelatÃƒÂ³rio": "Relatório",
            "importaÃƒÂ§ÃƒÂ£o": "importação",
            "regiÃƒÂ£o": "região",
            "nÃƒÂ£o": "não",
        }
        text = text.replace("\xad", "")
        for source, target in replacements.items():
            text = text.replace(source, target)
        text = text.replace("p´de", "pôde").replace("P´de", "Pôde")
        text = text.replace("extra­do", "extraído").replace("extra­vel", "extraível")
        return re.sub(r"\s+", " ", text).strip()

    def normalize_import_issue_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza campos textuais exibidos ao usuario no resumo de importacao."""
        if not isinstance(item, dict):
            return item
        normalized = dict(item)
        for key in ("motivo_descarte", "erro_processamento_pdf", "erro_processamento"):
            if key in normalized and isinstance(normalized[key], str):
                normalized[key] = self.normalize_import_text(normalized[key])
        if isinstance(normalized.get("log_pdf"), list):
            normalized["log_pdf"] = [
                self.normalize_import_text(entry) if isinstance(entry, str) else entry
                for entry in normalized["log_pdf"]
            ]
        return normalized

    def extract_import_error_reason(self, error_item: Dict[str, Any]) -> str:
        """Extrai uma razao curta e consistente para agregacao de erros."""
        if not isinstance(error_item, dict):
            return "erro_sem_motivo"
        for key in ("motivo_descarte", "erro_processamento_pdf", "erro_processamento"):
            value = error_item.get(key)
            if value:
                line = self.normalize_import_text(str(value).strip()).splitlines()[0].strip()
                if line:
                    return line[:300]
        return "erro_sem_motivo"

    @staticmethod
    def is_non_critical_import_reason(reason: str) -> bool:
        reason_norm = str(reason or "").strip().lower()
        if not reason_norm:
            return False
        # Descartes esperados/operacionais (ruido OCR ou paginas sem dados).
        if reason_norm.startswith("linha descartada por baixa qualidade"):
            return True
        if "faltam nome_base e sku_original" in reason_norm:
            return True
        if "nenhum dado de produto" in reason_norm and "pdf" in reason_norm:
            return True
        if reason_norm.startswith("nome_base sem conte"):
            return True
        return False

    @staticmethod
    def normalize_validated_data(
        candidate: Any,
        fallback: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Garante dict para o pipeline mesmo quando o validador retorna texto/JSON string."""
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, str):
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
        return fallback if isinstance(fallback, dict) else {}

    def sanitize_extracted_product(self, prod: Dict[str, Any]) -> Dict[str, Any]:
        """Normaliza campos antes de instanciar ProdutoCreate para evitar descartes."""
        data = dict(prod) if isinstance(prod, dict) else {}

        # Une dados_brutos_adicionais + dados_brutos_web para nao perder contexto util.
        extras: Dict[str, Any] = {}
        for raw_key in ("dados_brutos_adicionais", "dados_brutos_web"):
            raw_payload = data.get(raw_key)
            if isinstance(raw_payload, dict):
                for key, value in raw_payload.items():
                    if key in extras and extras.get(key) != value:
                        extras[f"{raw_key}_{key}"] = value
                    else:
                        extras[key] = value
            elif raw_payload not in (None, "", [], {}):
                extras[f"{raw_key}_raw"] = str(raw_payload)

        nome_base = data.get("nome_base")
        if nome_base is not None:
            nome_base = str(nome_base).strip()
            if len(nome_base) > 255:
                extras["nome_base_truncado_de"] = nome_base
                nome_base = nome_base[:255]
            data["nome_base"] = nome_base or None

        sku_original = data.get("sku_original")
        if sku_original is not None:
            sku_original = str(sku_original).strip()
            if sku_original.lower() in {"none", "null", "nan", "na", "n/a", "-", "--"}:
                extras["sku_original_descartado"] = sku_original
                sku_original = ""
            if len(sku_original) > 100:
                extras["sku_original_truncado_de"] = sku_original
                sku_original = sku_original[:100]
            data["sku_original"] = sku_original or None

        marca = data.get("marca")
        if marca is not None:
            marca = str(marca).strip()
            if len(marca) > 100:
                extras["marca_truncada_de"] = marca
                marca = marca[:100]
            data["marca"] = marca or None

        modelo = data.get("modelo")
        if modelo is not None:
            modelo = str(modelo).strip()
            if len(modelo) > 100:
                extras["modelo_truncado_de"] = modelo
                modelo = modelo[:100]
            data["modelo"] = modelo or None

        categoria_original = data.get("categoria_original")
        if categoria_original is not None:
            categoria_original = str(categoria_original).strip()
            if len(categoria_original) > 150:
                extras["categoria_original_truncada_de"] = categoria_original
                categoria_original = categoria_original[:150]
            data["categoria_original"] = categoria_original or None

        descricao_original = data.get("descricao_original")
        if descricao_original is not None:
            descricao_original = str(descricao_original).strip()
            if len(descricao_original) > 5000:
                extras["descricao_original_truncada_de"] = descricao_original
                descricao_original = descricao_original[:5000]
            data["descricao_original"] = descricao_original or None

        ean_original = data.get("ean_original")
        if ean_original is not None:
            ean_text = str(ean_original).strip()
            if ean_text:
                # Aceita apenas EAN informado como numero + separadores.
                # Evita transformar textos livres ("Actros 2651 - 2016") em falso EAN.
                if not re.fullmatch(r"[\d\s\-_/.]+", ean_text):
                    extras["ean_original_descartado"] = ean_text
                    data["ean_original"] = None
                else:
                    normalized = re.sub(r"[\s\-_/.]", "", ean_text)
                    if 1 <= len(normalized) <= 13:
                        data["ean_original"] = normalized
                    else:
                        extras["ean_original_descartado"] = ean_text
                        data["ean_original"] = None
            else:
                data["ean_original"] = None

        # Recupera nome quando OCR traz somente codigo no nome_base.
        nome_base = str(data.get("nome_base") or "").strip()
        sku_original = str(data.get("sku_original") or "").strip()
        descricao_original = str(data.get("descricao_original") or "").strip()
        categoria_original = str(data.get("categoria_original") or "").strip()
        nome_compacto = re.sub(r"[^0-9A-Za-z]", "", nome_base).lower()
        sku_compacto = re.sub(r"[^0-9A-Za-z]", "", sku_original).lower()
        nome_numerico = bool(nome_compacto) and nome_compacto.isdigit()
        nome_codigo_peca = self._quality.text_looks_like_part_code(nome_base)
        nome_igual_sku = bool(nome_compacto and sku_compacto and nome_compacto == sku_compacto)
        nome_ruido_ocr = self._quality.name_looks_like_ocr_noise(nome_base)
        descricao_util = self._quality.text_has_context(descricao_original)
        descricao_parece_peca = self._quality.text_looks_like_part_name(descricao_original)
        descricao_parece_aplicacao = self._quality.text_looks_like_vehicle_application(
            descricao_original
        )

        if nome_base and self._quality.name_looks_like_annotation_header(nome_base):
            extras["nome_base_descartado"] = nome_base
            nome_base = ""
            data["nome_base"] = None

        # Quando categoria parece conter nome de peca e descricao esta vazia,
        # aproveita categoria como descricao para nao perder contexto util.
        if (
            not descricao_util
            and categoria_original
            and self._quality.text_looks_like_part_name(categoria_original)
        ):
            data["descricao_original"] = categoria_original[:5000]
            descricao_original = data["descricao_original"]
            descricao_util = self._quality.text_has_context(descricao_original)
            descricao_parece_peca = self._quality.text_looks_like_part_name(descricao_original)
            descricao_parece_aplicacao = self._quality.text_looks_like_vehicle_application(
                descricao_original
            )
            extras["descricao_substituida_por_categoria"] = True

        # Se descricao atual e apenas aplicacao e categoria contem nome de peca,
        # prioriza categoria como descricao principal.
        if (
            descricao_util
            and descricao_parece_aplicacao
            and categoria_original
            and self._quality.text_looks_like_part_name(categoria_original)
        ):
            data["descricao_original"] = categoria_original[:5000]
            descricao_original = data["descricao_original"]
            descricao_util = self._quality.text_has_context(descricao_original)
            descricao_parece_peca = self._quality.text_looks_like_part_name(descricao_original)
            descricao_parece_aplicacao = self._quality.text_looks_like_vehicle_application(
                descricao_original
            )
            extras["descricao_aplicacao_substituida_por_categoria"] = True

        nome_fraco = (
            not nome_base
            or nome_numerico
            or nome_codigo_peca
            or nome_igual_sku
            or nome_ruido_ocr
            or self._quality.name_looks_like_annotation_header(nome_base)
        )

        # Tenta recuperar descricao util a partir de dados brutos (colunas nao mapeadas).
        # Tambem corrige casos em que a descricao atual e apenas aplicacao veicular.
        should_try_raw_part = (
            not descricao_util
            or (descricao_parece_aplicacao and nome_fraco)
            or (nome_fraco and not descricao_parece_peca)
        )
        if should_try_raw_part and isinstance(extras, dict):
            for raw_key, raw_value in extras.items():
                candidate = str(raw_value or "").strip()
                if not candidate:
                    continue
                if self._quality.text_looks_like_part_name(candidate):
                    if data.get("descricao_original") != candidate:
                        data["descricao_original"] = candidate[:5000]
                    descricao_original = data["descricao_original"]
                    descricao_util = self._quality.text_has_context(descricao_original)
                    descricao_parece_peca = self._quality.text_looks_like_part_name(
                        descricao_original
                    )
                    descricao_parece_aplicacao = (
                        self._quality.text_looks_like_vehicle_application(descricao_original)
                    )
                    extras["descricao_substituida_por_dados_brutos"] = str(raw_key)
                    break

        # Se nome e' apenas codigo/sku, tenta promover descricao util para nome_base.
        if descricao_util and (
            not nome_base
            or nome_numerico
            or nome_codigo_peca
            or nome_igual_sku
            or nome_ruido_ocr
            or self._quality.name_looks_like_annotation_header(nome_base)
        ):
            if descricao_parece_peca or nome_numerico or (
                not nome_base and not descricao_parece_aplicacao
            ):
                data["nome_base"] = descricao_original[:255]
                extras["nome_base_substituido_por_descricao"] = True

        if extras:
            data["dados_brutos_adicionais"] = extras

        return data
