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
    assert _payload_service._looks_like_company_timeline_claim("Nossa marca desde 2015.") is True
    assert _payload_service._sanitize_description_text(
        "Paralama reforcado.\n\nNossa marca desde 2015."
    ) == "Paralama reforcado."


def test_sanitize_description_skips_empty_chunks_via_normalizer(monkeypatch):
    """Ignore empty normalized chunks while keeping valid description pieces."""
    original_as_text = _payload_service._normalization.as_text

    def _patched_as_text(value, max_len=10000):
        if value == "vazio":
            return ""
        return original_as_text(value, max_len=max_len)

    monkeypatch.setattr(_payload_service._normalization, "as_text", _patched_as_text)
    sanitized = _payload_service._sanitize_description_text(
        "Paralama reforcado.\nvazio\nNossa marca desde 2015."
    )

    assert sanitized == "Paralama reforcado."


def test_application_and_weak_value_heuristics_cover_remaining_branches():
    """Cover weak-field and weak-dynamic heuristics."""
    assert _payload_service._looks_like_application_only(None) is False
    assert _payload_service._looks_like_application_only("----") is False
    assert _payload_service._looks_like_application_only("Actros 2016-2018") is True
    assert _payload_service._looks_like_application_only("Paralama Actros 2016-2018") is False

    assert _payload_service._is_weak_existing_field("nome_chat_api", None) is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "----") is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "todos") is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "1234") is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "1234/5678") is True
    assert _payload_service._is_weak_existing_field("nome_chat_api", "Actros 2016-2018") is True
    assert _payload_service._is_weak_existing_field(
        "nome_chat_api", "Paralama dianteiro reforcado"
    ) is False
    assert _payload_service._is_weak_existing_field("descricao_original", "anotacoes internas") is True
    assert (
        _payload_service._is_weak_existing_field(
            "descricao_original",
            "Garanta freios e suspensao com alta performance e seguranca. Sua compra online protegida.",
        )
        is True
    )
    assert (
        _payload_service._is_weak_existing_field(
            "descricao_original",
            "Mercedes Actros 2016-2018 dianteiro",
        )
        is True
    )
    assert (
        _payload_service._is_weak_existing_field(
            "descricao_original",
            "Observacoes internas detalhadas do fornecedor",
        )
        is True
    )
    assert _payload_service._is_weak_existing_field(
        "descricao_original", "Paralama dianteiro reforcado com suporte"
    ) is False
    assert _payload_service._is_weak_existing_field("marca", None) is True
    assert _payload_service._is_weak_existing_field("marca", "generico") is True
    assert _payload_service._is_weak_existing_field("marca", "sm") is True
    assert _payload_service._is_weak_existing_field("marca", "Mercadocar") is True
    assert _payload_service._is_weak_existing_field("marca", "Randon") is False
    assert _payload_service._is_weak_existing_field("sku", "ABC123") is False

    assert _payload_service._is_weak_dynamic_value("descricao", None) is True
    assert _payload_service._is_weak_dynamic_value("descricao", "----") is True
    assert _payload_service._is_weak_dynamic_value("descricao", "todos") is True
    assert _payload_service._is_weak_dynamic_value("descricao", "curta") is True
    assert _payload_service._is_weak_dynamic_value("descricao", "Actros 2016-2018") is True
    assert (
        _payload_service._is_weak_dynamic_value(
            "descricao",
            "Garanta freios e suspensao com alta performance e seguranca.",
        )
        is True
    )
    assert _payload_service._is_weak_dynamic_value("titulo", "Reservatorio de Ar 20 Litros - ROCHEPECAS") is True
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


def test_set_dynamic_if_empty_covers_weak_replacement_branch():
    """Replace weak dynamic values when a stronger candidate arrives."""
    dynamic_current = {"material": "geral"}
    target = _payload_service._set_dynamic_if_empty(
        candidates=["material"],
        value="plastico injetado",
        dynamic_current=dynamic_current,
        normalized_key_to_real={"material": "material"},
        dynamic_ignored=[],
        allow_replace_weak=True,
    )

    assert target == "material"
    assert dynamic_current["material"] == "plastico injetado"


def test_set_dynamic_if_empty_covers_empty_known_norm_branch():
    """Skip empty normalized keys while resolving fallback target aliases."""
    dynamic_current = {"peso_legado": "10kg"}
    target = _payload_service._set_dynamic_if_empty(
        candidates=["peso"],
        value="12kg",
        dynamic_current=dynamic_current,
        normalized_key_to_real={"": "ignorar", "peso_legado": "peso_legado"},
        dynamic_ignored=[],
    )

    assert target is None


def test_set_dynamic_if_empty_skips_empty_existing_alias_before_using_next_match():
    """Keep scanning alias matches when the first current value is empty."""
    target = _payload_service._set_dynamic_if_empty(
        candidates=["descricao"],
        value=None,
        dynamic_current={
            "descricao_vazia": "   ",
            "descricao_legada": "Descricao reaproveitada",
        },
        normalized_key_to_real={"desc_auto": "desc_auto"},
        dynamic_ignored=[],
    )

    assert target == "desc_auto"


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


def test_build_payload_prefers_short_supplier_description_over_structured_seo_dump():
    """Keep the visible product description concise when supplier enrichment already has a short factual description."""
    produto = _make_product(descricao_original="Garanta sua compra online protegida")
    dados = {
        "fonte_principal_fornecedor": True,
        "descricao_curta": "Reservatório de ar de 20 litros para Mercedes Benz LN 608/708.",
        "descricao_detalhada_seo": (
            "Reservatório de ar de 20 litros para Mercedes Benz LN 608/708. "
            "Destaques: URL da fonte: https://fornecedor.example/produto Controle sua privacidade"
        ),
    }

    update_fields, notes, _ = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

    assert update_fields["descricao_original"] == "Reservatório de ar de 20 litros para Mercedes Benz LN 608/708."
    assert "descricao_original:substituido_valor_fraco" in notes


def test_build_payload_discards_unrelated_web_payload_for_generic_seed():
    """Block visible updates when the web payload does not match the product seed."""
    produto = _make_product(
        marca="wera",
        dynamic_attributes={},
        product_type=SimpleNamespace(
            attribute_templates=[
                SimpleNamespace(attribute_key="titulo", label="Titulo"),
                SimpleNamespace(attribute_key="descricao", label="Descricao"),
                SimpleNamespace(attribute_key="material", label="Material"),
            ]
        ),
    )
    setattr(produto, "nome_base", "Wera tool kit")
    dados = {
        "nome": "Estribo Strada 2021 2022 Cabine Dupla AlumÃ­nio Preto",
        "descricao_curta": (
            "Estribo SUV II para Strada 2021 em diante aluminio preto com kit aplicacao. "
            "Protege a lateral do veiculo contra pedras e barro."
        ),
        "imagem_url": "https://cdn.awsli.com.br/1991/1991068/produto/19021944890526e4ff6.jpg",
        "marca": "Bepo",
        "especificacoes_tecnicas_dict": {
            "Aplicacao": "Strada 2021 em diante cabine simples e dupla",
            "Material": "Aluminio",
            "Acabamento": "Preto",
        },
    }

    update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

    assert update_fields == {}
    assert notes == []
    assert ignored == [
        "validacao_relevancia=marca divergente da referencia do produto; conteudo indica outra categoria/produto"
    ]
    assert dados["validacao_relevancia_payload"]["aprovado"] is False


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


def test_build_payload_keeps_existing_signal_values_and_replaces_weak_dynamic_aliases():
    """Preserve explicit extracted signals and replace weak dynamic aliases once."""
    produto = _make_product(
        dynamic_attributes={"descricao": "Actros 2016-2018"},
        product_type=SimpleNamespace(
            attribute_templates=[SimpleNamespace(attribute_key="descricao", label="Descricao")]
        ),
    )
    dados = {
        "codigo_original": "LEGADO-1",
        "descricao_curta": "Codigo: ABC123 Material: plastico injetado",
    }

    update_fields, notes, _ = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

    assert dados["codigo_original"] == "LEGADO-1"
    assert update_fields["dynamic_attributes"]["descricao"].startswith("Codigo: ABC123")
    assert "dynamic_attributes=descricao,id,material" in notes
