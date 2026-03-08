"""Additional helper-level tests for catalog import sanitization."""

from __future__ import annotations

from Backend.application.services.catalog_import_quality_service import (
    CatalogImportQualityService,
)
from Backend.application.services.catalog_import_sanitization_service import (
    CatalogImportSanitizationService,
)


class _QualityStub:
    """Minimal quality stub to deterministically drive sanitation branches."""

    def text_has_context(self, text):
        lowered = str(text).lower()
        return (
            "context" in lowered
            or "part" in lowered
            or "application" in lowered
        )

    def part_context_strength(self, text):
        lowered = str(text).lower()
        if "weak" in lowered:
            return 1
        if "application" in lowered:
            return 3
        if "part" in lowered or "context" in lowered:
            return 3
        return 0

    def text_looks_like_vehicle_application(self, text):
        return "application" in str(text).lower()

    def text_looks_like_part_name(self, text):
        lowered = str(text).lower()
        return "part" in lowered or "paralama" in lowered or "reservatorio" in lowered

    def text_looks_like_part_code(self, text):
        return str(text).replace(" ", "").isdigit()

    def name_looks_like_ocr_noise(self, text):
        return "ruido" in str(text).lower()

    def name_looks_like_annotation_header(self, text):
        return "acesse nosso" in str(text).lower()


class _TruncatingSanitizationService(CatalogImportSanitizationService):
    """Force overlong sanitize outputs so truncation branches become reachable."""

    def _normalize_product_text(self, value):
        return value

    @classmethod
    def _sanitize_identity_text(cls, value, *, max_len, cut_on_contact_marker=True):
        _ = max_len, cut_on_contact_marker
        mapping = {
            "nome": "N" * 300,
            "marca": "M" * 120,
            "modelo": "O" * 130,
            "categoria": "C" * 170,
        }
        return mapping.get(str(value), str(value))

    @classmethod
    def _sanitize_description_text(cls, value, *, max_len=5000):
        _ = max_len
        if str(value) == "descricao":
            return "D" * 5100
        return str(value)


def _service(quality=None):
    """Build sanitization service with configurable quality heuristic."""
    return CatalogImportSanitizationService(quality or CatalogImportQualityService())


def test_domain_token_correction_handles_empty_digits_short_folded_direct_and_no_match():
    """Cover all early returns and correction outcomes for domain tokens."""
    cls = CatalogImportSanitizationService
    assert cls._maybe_correct_domain_token("") == ""
    assert cls._maybe_correct_domain_token("abc1") == "abc1"
    assert cls._maybe_correct_domain_token("abc") == "abc"
    assert cls._maybe_correct_domain_token("----") == "----"
    assert cls._maybe_correct_domain_token("Reservatorio") == "Reservatório"
    assert cls._maybe_correct_domain_token("RESERVATORIO") == "RESERVATÓRIO"
    assert cls._maybe_correct_domain_token("xyzwq") == "xyzwq"
    assert cls._preserve_case_style("fixagdo", "fixação") == "fixação"


def test_sanitize_identity_and_description_text_cover_empty_marker_and_filtered_paths():
    """Exercise identity/description sanitizers across early exits and filtered content."""
    cls = CatalogImportSanitizationService
    assert cls._sanitize_identity_text("", max_len=20) is None
    assert (
        cls._sanitize_identity_text(
            "Paralama Loja Exemplo", max_len=20, cut_on_contact_marker=True
        )
        == "Paralama"
    )
    assert (
        cls._sanitize_identity_text(
            "www.site.com 11 99888 7766", max_len=20, cut_on_contact_marker=False
        )
        is None
    )

    assert cls._sanitize_description_text("") is None
    assert (
        cls._sanitize_description_text(
            "Paralama reforcado. Contato via whatsapp 11 99888 7766."
        )
        == "Paralama reforcado."
    )
    assert cls._sanitize_description_text("www.site.com 11 99888 7766") is None
    assert (
        cls._sanitize_description_text("Telefone 11 99888 7766 www.site.com")
        == "Telefone"
    )


def test_normalize_product_text_and_import_text_cover_early_break_paths():
    """Cover light normalization branches that return without mojibake rewrites."""
    service = _service()
    assert service._normalize_product_text(None) is None
    assert service._normalize_product_text("   ") is None
    assert service.normalize_import_text("texto limpo") == "texto limpo"


def test_pick_part_candidate_from_dynamic_attributes_covers_non_dict_low_score_and_application_penalty():
    """Drive best-candidate selection and low-score rejection deterministically."""
    service = _service(_QualityStub())
    assert service._pick_part_candidate_from_dynamic_attributes([]) is None
    assert (
        service._pick_part_candidate_from_dynamic_attributes(
            {"a": 1, "b": "weak text", "c": "application part context"}
        )
        == "application part context"
    )
    assert (
        service._pick_part_candidate_from_dynamic_attributes({"a": "weak text"})
        is None
    )


def test_normalize_issue_error_reason_and_non_critical_reason_helpers():
    """Cover normalization helpers for issue summaries and import reason classification."""
    service = _service()
    assert service.normalize_import_issue_item("raw") == "raw"
    normalized = service.normalize_import_issue_item(
        {
            "motivo_descarte": "nao critica",
            "log_pdf": ["conteudo", {"x": 1}],
        }
    )
    assert normalized["motivo_descarte"] == "não crítica"
    assert normalized["log_pdf"][0] == "conteúdo"

    assert service.extract_import_error_reason("raw") == "erro_sem_motivo"
    assert service.extract_import_error_reason({}) == "erro_sem_motivo"
    assert (
        service.extract_import_error_reason({"erro_processamento": "   "})
        == "erro_sem_motivo"
    )
    long_reason = "A" * 400
    assert len(service.extract_import_error_reason({"erro_processamento": long_reason})) == 300

    assert service.is_non_critical_import_reason("") is False
    assert service.is_non_critical_import_reason("linha descartada por baixa qualidade") is True
    assert service.is_non_critical_import_reason("faltam nome_base e sku_original") is True
    assert service.is_non_critical_import_reason("nenhum dado de produto encontrado no pdf") is True
    assert service.is_non_critical_import_reason("nome_base sem conteudo util") is True
    assert service.is_non_critical_import_reason("erro fatal") is False


def test_normalize_import_text_and_error_reason_cover_remaining_mojibake_and_blank_paths(monkeypatch):
    """Cover the no-improvement mojibake break and blank normalized error branches."""
    service = _service()
    monkeypatch.setattr(service, "_looks_mojibake", lambda text: "Ã" in str(text))
    monkeypatch.setattr(service, "_decode_maybe", lambda candidate, _source: candidate)
    assert service.normalize_import_text("PeÃ§a") == "PeÃ§a"

    monkeypatch.setattr(service, "normalize_import_text", lambda _value: "")
    assert service.extract_import_error_reason({"erro_processamento": "falha crua"}) == "erro_sem_motivo"
    monkeypatch.setattr(service, "normalize_import_text", lambda _value: "\n")
    assert service.extract_import_error_reason({"erro_processamento": "falha crua"}) == "erro_sem_motivo"


def test_normalize_import_text_can_exhaust_mojibake_loop_without_break(monkeypatch):
    """Force the decode loop to exhaust all iterations before applying replacements."""
    service = _service()

    monkeypatch.setattr(service, "_looks_mojibake", lambda _text: True)
    monkeypatch.setattr(service, "_marker_count", lambda candidate: len(str(candidate)))
    monkeypatch.setattr(service, "_decode_maybe", lambda candidate, _source: str(candidate)[:-1])

    assert service.normalize_import_text("abcdefghi").startswith("abc")


def test_sanitize_extracted_product_handles_missing_nome_base_key():
    """Cover the branch where nome_base is absent from the extracted payload."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "sku_original": "ZX99",
            "descricao_original": "part context",
        }
    )
    assert sanitized["nome_base"] == "part context"
    assert sanitized["dados_brutos_adicionais"]["nome_base_substituido_por_descricao"] is True


def test_sanitize_description_text_skips_blank_chunks_and_raw_extra_blank_candidates():
    """Cover blank chunk filtering and blank raw-extra candidates during product sanitation."""
    service = _service(_QualityStub())

    assert (
        CatalogImportSanitizationService._sanitize_description_text(
            "Paralama reforcado.\n   \nContato whatsapp 11 99888 7766."
        )
        == "Paralama reforcado."
    )

    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "123456",
            "sku_original": "123456",
            "descricao_original": "",
            "marca": "Bosch",
            "modelo": "X1",
            "dados_brutos_adicionais": {"vazio": "   ", "origem": "part context"},
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert sanitized["descricao_original"] == "part context"
    assert extras["descricao_substituida_por_dados_brutos"] == "origem"
    assert sanitized["marca"] == "Bosch"
    assert sanitized["modelo"] == "X1"


def test_normalize_validated_data_covers_dict_bad_json_non_dict_json_and_fallback_type():
    """Cover all normalized validated-data return branches."""
    service = _service()
    payload = {"nome_base": "ABC"}
    assert service.normalize_validated_data(payload, {}) is payload
    assert service.normalize_validated_data("[1,2,3]", {"fallback": True}) == {"fallback": True}
    assert service.normalize_validated_data("{invalid", {"fallback": True}) == {"fallback": True}
    assert service.normalize_validated_data(123, {"fallback": True}) == {"fallback": True}
    assert service.normalize_validated_data("{}", []) == {}


def test_sanitize_extracted_product_merges_raw_payloads_and_handles_dynamic_attrs_and_ean():
    """Cover extras merge conflicts, raw payload preservation and EAN edge cases."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "123456",
            "sku_original": "--",
            "descricao_original": "Application only",
            "categoria_original": "Paralama Part",
            "dynamic_attributes": {"obs": "", "contato": "www.site.com"},
            "ean_original": "12345678901234",
            "dados_brutos_adicionais": {"foo": "part context"},
            "dados_brutos_web": {"foo": "other value"},
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert extras["dados_brutos_web_foo"] == "other value"
    assert extras["sku_original_descartado"] == "--"
    assert extras["ean_original_descartado"] == "12345678901234"
    assert sanitized["descricao_original"] == "Paralama Part"
    assert extras["descricao_aplicacao_substituida_por_categoria"] is True
    assert sanitized["dynamic_attributes"]["obs"] == ""
    assert sanitized["dynamic_attributes"]["contato"] is None


def test_sanitize_extracted_product_uses_category_when_description_is_missing():
    """Cover the category-to-description recovery branch."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "",
            "descricao_original": "",
            "categoria_original": "Reservatorio Part",
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert sanitized["descricao_original"] == "Reservatório Part"
    assert extras["descricao_substituida_por_categoria"] is True


def test_sanitize_extracted_product_can_recover_description_from_raw_extras_without_overwriting_equal_text():
    """Cover raw extras fallback and the branch where the description already matches the candidate."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "123456",
            "sku_original": "123456",
            "descricao_original": "part application context",
            "dados_brutos_adicionais": {"origem": "part application context"},
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert sanitized["descricao_original"] == "part application context"
    assert extras["descricao_substituida_por_dados_brutos"] == "origem"
    assert sanitized["nome_base"] == "part application context"
    assert extras["nome_base_substituido_por_descricao"] is True


def test_sanitize_extracted_product_dynamic_part_candidate_does_not_replace_good_description():
    """Cover the false branch when a strong dynamic candidate exists but replacement is not needed."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "Paralama Part",
            "descricao_original": "part context",
            "dynamic_attributes": {"candidate": "part context"},
        }
    )
    extras = sanitized.get("dados_brutos_adicionais") or {}
    assert "descricao_substituida_por_atributo_dinamico" not in extras
    assert sanitized["descricao_original"] == "part context"


def test_sanitize_extracted_product_handles_valid_and_blank_ean_and_no_name_promotion():
    """Cover EAN success/blank branches and the false branch of name promotion."""
    service = _service(_QualityStub())
    sanitized_valid = service.sanitize_extracted_product(
        {
            "nome_base": "codigo x",
            "sku_original": "codigo x",
            "descricao_original": "application context",
            "ean_original": "123.456.789",
        }
    )
    assert sanitized_valid["ean_original"] == "123456789"
    assert sanitized_valid["nome_base"] == "codigo x"
    assert "nome_base_substituido_por_descricao" not in (
        sanitized_valid.get("dados_brutos_adicionais") or {}
    )

    sanitized_blank = service.sanitize_extracted_product(
        {
            "nome_base": "Paralama Part",
            "descricao_original": "part context",
            "ean_original": "",
            "dynamic_attributes": {"numero": 1},
        }
    )
    assert sanitized_blank["ean_original"] is None
    assert sanitized_blank["dynamic_attributes"]["numero"] == 1


def test_sanitize_extracted_product_annotation_header_and_raw_payload_scalar_are_preserved():
    """Cover annotation-header discard and scalar raw payload preservation."""
    service = _service(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "Acesse nosso catalogo",
            "descricao_original": "",
            "dados_brutos_web": "conteudo bruto",
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert sanitized["nome_base"] is None
    assert extras["nome_base_descartado"] == "Acesse nosso catálogo"
    assert extras["dados_brutos_web_raw"] == "conteudo bruto"


def test_sanitize_extracted_product_truncates_overlong_identity_and_description_fields():
    """Reach truncation branches that are otherwise unreachable with the default sanitizers."""
    service = _TruncatingSanitizationService(_QualityStub())
    sanitized = service.sanitize_extracted_product(
        {
            "nome_base": "nome",
            "marca": "marca",
            "modelo": "modelo",
            "categoria_original": "categoria",
            "descricao_original": "descricao",
        }
    )
    extras = sanitized["dados_brutos_adicionais"]
    assert len(sanitized["nome_base"]) == 255
    assert len(sanitized["marca"]) == 100
    assert len(sanitized["modelo"]) == 100
    assert len(sanitized["categoria_original"]) == 150
    assert len(sanitized["descricao_original"]) == 5000
    assert len(extras["nome_base_truncado_de"]) == 300
    assert len(extras["marca_truncada_de"]) == 120
    assert len(extras["modelo_truncado_de"]) == 130
    assert len(extras["categoria_original_truncada_de"]) == 170
    assert len(extras["descricao_original_truncada_de"]) == 5100
