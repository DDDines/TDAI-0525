"""Additional tests for web enrichment payload service internals."""

from __future__ import annotations

from types import SimpleNamespace

from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_payload_service import (
    WebEnrichmentPayloadService,
)


_normalization_service = WebEnrichmentNormalizationService()
_payload_service = WebEnrichmentPayloadService(
    normalization_service=_normalization_service
)


def _make_product(**overrides):
    """Build a minimal product stub for payload tests."""
    base = {
        "nome_chat_api": None,
        "descricao_original": None,
        "descricao_chat_api": None,
        "imagem_principal_url": None,
        "marca": None,
        "sku": None,
        "preco_venda": None,
        "dynamic_attributes": {},
        "product_type": None,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_company_timeline_detection_and_sanitization_cover_edge_paths():
    """Cover timeline detection and description sanitization branches."""
    assert _payload_service._contains_part_hint("paralama dianteiro") is True
    assert _payload_service._contains_part_hint("historia da empresa") is False
    assert _payload_service._looks_like_company_timeline_claim(None) is False
    assert _payload_service._looks_like_company_timeline_claim(
        "Nossa empresa foi fundada em 2015."
    ) is True
    assert _payload_service._looks_like_company_timeline_claim(
        "Paralama dianteiro reforcado."
    ) is False
    assert _payload_service._sanitize_description_text(None) == ""
    assert _payload_service._sanitize_description_text(
        "Paralama externo reforcado. Nossa empresa foi fundada em 2015."
    ) == "Paralama externo reforcado."
    assert _payload_service._sanitize_description_text(
        "Nossa empresa foi fundada em 2015."
    ) == "Nossa empresa foi fundada em 2015."


def test_application_and_weak_value_heuristics_cover_remaining_branches():
    """Cover weak-field and weak-dynamic heuristics."""
    assert _payload_service._looks_like_application_only(None) is False
    assert _payload_service._looks_like_application_only("Actros 2016-2018") is True
    assert _payload_service._looks_like_application_only("Paralama Actros 2016-2018") is False

    assert _payload_service._is_weak_existing_field("nome_chat_api", "1234") is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "Actros 2016-2018") is True
    assert _payload_service._is_weak_existing_field(
        "nome_chat_api", "Paralama dianteiro reforcado"
    ) is False
    assert _payload_service._is_weak_existing_field("descricao_original", "anotacoes internas") is True
    assert _payload_service._is_weak_existing_field(
        "descricao_original", "Paralama dianteiro reforcado com suporte"
    ) is False
    assert _payload_service._is_weak_existing_field("marca", "sm") is True
    assert _payload_service._is_weak_existing_field("marca", "Randon") is False
    assert _payload_service._is_weak_existing_field("sku", "ABC123") is False

    assert _payload_service._is_weak_dynamic_value("descricao", None) is True
    assert _payload_service._is_weak_dynamic_value("descricao", "curta") is True
    assert _payload_service._is_weak_dynamic_value("descricao", "Actros 2016-2018") is True
    assert _payload_service._is_weak_dynamic_value("id", "ABC123MARCA") is True
    assert _payload_service._is_weak_dynamic_value("aplicacao", "todos") is True
    assert _payload_service._is_weak_dynamic_value("material", "geral") is True
    assert _payload_service._is_weak_dynamic_value("material", "plastico injetado") is False


def test_apply_if_empty_or_weak_covers_empty_replace_and_ignore_paths():
    """Apply visible-field updates only when the new value is usable."""
    update_fields = {}
    notes = []
    ignored = []

    _payload_service._apply_if_empty_or_weak(
        field_name="nome_chat_api",
        current_value=None,
        new_value=None,
        update_fields=update_fields,
        notes=notes,
        ignored_notes=ignored,
    )
    _payload_service._apply_if_empty_or_weak(
        field_name="nome_chat_api",
        current_value=None,
        new_value="Paralama dianteiro",
        update_fields=update_fields,
        notes=notes,
        ignored_notes=ignored,
    )
    _payload_service._apply_if_empty_or_weak(
        field_name="descricao_original",
        current_value="Actros 2016-2018",
        new_value="Paralama dianteiro reforcado com suporte metalico",
        update_fields=update_fields,
        notes=notes,
        ignored_notes=ignored,
        allow_replace_weak=True,
    )
    _payload_service._apply_if_empty_or_weak(
        field_name="marca",
        current_value="Randon",
        new_value="Nova Marca",
        update_fields=update_fields,
        notes=notes,
        ignored_notes=ignored,
        allow_replace_weak=True,
    )

    assert update_fields["nome_chat_api"] == "Paralama dianteiro"
    assert update_fields["descricao_original"].startswith("Paralama dianteiro")
    assert "nome_chat_api" in notes
    assert "descricao_original:substituido_valor_fraco" in notes
    assert ignored == ["marca:mantido_valor_existente"]


def test_set_dynamic_if_empty_covers_alias_lookup_replacement_and_ignore_paths():
    """Resolve dynamic targets through aliases, fallbacks and replacement rules."""
    first_alias_target = _payload_service._set_dynamic_if_empty(
        candidates=["descricao"],
        value=None,
        dynamic_current={"descricao_legada": "Descricao legada"},
        normalized_key_to_real={"desc_auto": "desc_auto"},
        dynamic_ignored=[],
    )

    dynamic_current = {"descricao_legada": "Descricao legada", "id": "ABC123MARCA"}
    normalized_key_to_real = {
        "desc_auto": "desc_auto",
        "materialpredominante": "material_predominante",
        "id": "id",
        "titulo": "titulo",
    }
    dynamic_ignored = []

    direct_target = _payload_service._set_dynamic_if_empty(
        candidates=["descricao"],
        value="Paralama dianteiro reforcado",
        dynamic_current=dynamic_current,
        normalized_key_to_real=normalized_key_to_real,
        dynamic_ignored=dynamic_ignored,
    )
    contains_target = _payload_service._set_dynamic_if_empty(
        candidates=["material"],
        value="plastico injetado",
        dynamic_current=dynamic_current,
        normalized_key_to_real=normalized_key_to_real,
        dynamic_ignored=dynamic_ignored,
    )
    suspicious_target = _payload_service._set_dynamic_if_empty(
        candidates=["id"],
        value="ABC123",
        dynamic_current=dynamic_current,
        normalized_key_to_real=normalized_key_to_real,
        dynamic_ignored=dynamic_ignored,
        allow_replace_suspicious=True,
    )
    weak_target = _payload_service._set_dynamic_if_empty(
        candidates=["titulo"],
        value="Paralama dianteiro reforcado",
        dynamic_current=dynamic_current,
        normalized_key_to_real=normalized_key_to_real,
        dynamic_ignored=dynamic_ignored,
        allow_replace_weak=True,
    )
    fallback_target = _payload_service._set_dynamic_if_empty(
        candidates=["peso"],
        value="10kg",
        dynamic_current=dynamic_current,
        normalized_key_to_real={},
        dynamic_ignored=dynamic_ignored,
    )
    ignored_target = _payload_service._set_dynamic_if_empty(
        candidates=["material"],
        value="plastico injetado",
        dynamic_current={"material_predominante": "aco"},
        normalized_key_to_real={"materialpredominante": "material_predominante"},
        dynamic_ignored=dynamic_ignored,
    )

    assert first_alias_target == "desc_auto"
    assert direct_target == "desc_auto"
    assert contains_target == "material_predominante"
    assert suspicious_target == "id"
    assert weak_target == "titulo"
    assert fallback_target == "peso"
    assert ignored_target is None
    assert "material_predominante" in dynamic_ignored


def test_build_payload_handles_signal_extraction_specs_and_ignored_notes():
    """Build visible payloads while extracting signals and deduplicating ignored notes."""
    produto = _make_product(
        marca="Randon",
        preco_venda=99.0,
        dynamic_attributes="nao-dict",
    )
    dados = {
        "descricao_curta": "Codigo: ABC123 Material: plastico injetado",
        "preco": "199,90",
        "especificacoes_tecnicas_dict": {
            "": "ignorar",
            "peso": "10kg",
        },
    }

    update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

    assert "preco_venda" not in update_fields
    assert "preco_venda:mantido_valor_existente" in ignored
    assert update_fields["dynamic_attributes"]["id"] == "ABC123"
    assert update_fields["dynamic_attributes"]["material"] == "plastico injetado"
    assert update_fields["dynamic_attributes"]["peso"] == "10kg"
    assert any(note.startswith("dynamic_attributes=") for note in notes)


def test_build_payload_handles_template_entries_without_attr_key_and_dedupes_ignored_dynamic_notes():
    """Ignore incomplete templates and collapse repeated ignored dynamic keys."""
    produto = _make_product(
        dynamic_attributes={"material": "aco", "material_extra": "aco"},
        product_type=SimpleNamespace(
            attribute_templates=[
                SimpleNamespace(attribute_key=None, label="Material"),
                SimpleNamespace(attribute_key="material_extra", label=None),
            ]
        ),
    )
    dados = {
        "material": "plastico",
        "especificacoes_tecnicas_dict": {
            "material": "plastico",
            "material extra": "plastico",
        },
    }

    update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

    assert update_fields == {}
    assert notes == []
    assert ignored == ["dynamic_attributes=material,material_extra"]
