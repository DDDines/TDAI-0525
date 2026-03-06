"""Module test web enrichment mapping.

Contains backend logic related to test web enrichment mapping and documents its role in the OOP architecture.
"""

from types import SimpleNamespace

from Backend.application.services.web_enrichment_content_quality_service import (
    WebEnrichmentContentQualityService,
)
from Backend.application.services.web_enrichment_normalization_service import (
    WebEnrichmentNormalizationService,
)
from Backend.application.services.web_enrichment_payload_service import (
    WebEnrichmentPayloadService,
)
from Backend.application.services.web_enrichment_relevance_service import (
    WebEnrichmentRelevanceService,
)


_normalization_service = WebEnrichmentNormalizationService()
_relevance_service = WebEnrichmentRelevanceService()
_content_quality_service = WebEnrichmentContentQualityService(
    normalization_service=_normalization_service
)
_payload_service = WebEnrichmentPayloadService(
    normalization_service=_normalization_service
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    def _make_product(**overrides):
        """Run make product in this workflow."""
        base = {
            "nome_chat_api": None,
            "descricao_original": None,
            "descricao_chat_api": None,
            "imagem_principal_url": None,
            "marca": None,
            "sku": None,
            "preco_venda": None,
            "dynamic_attributes": {"aplicacao": "Todos"},
            "product_type": SimpleNamespace(
                attribute_templates=[
                    SimpleNamespace(attribute_key="titulo", label="Titulo"),
                    SimpleNamespace(attribute_key="id", label="ID"),
                    SimpleNamespace(attribute_key="descricao", label="Descricao"),
                    SimpleNamespace(attribute_key="material", label="Material"),
                ]
            ),
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_build_payload_populates_visible_fields_and_dynamic_attributes():
        """Run test build payload populates visible fields and dynamic attributes in this workflow."""
        produto = _make_product()
        dados = {
            "nome": "Suporte Fixacao Apara Barro Randon 695mm",
            "descricao_curta": "Codigo: SP1081 Material: Metal",
            "imagem_url": "https://img.test/produto.webp",
            "marca": "Pickup Parts",
            "sku": "SP1081",
            "preco": "129,90",
            "disponibilidade": "InStock",
            "moeda_preco": "BRL",
        }
    
        update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)
    
        assert update_fields["nome_chat_api"] == "Suporte Fixacao Apara Barro Randon 695mm"
        assert update_fields["descricao_original"].startswith("Codigo: SP1081")
        assert "descricao_chat_api" not in update_fields
        assert update_fields["imagem_principal_url"] == "https://img.test/produto.webp"
        assert update_fields["marca"] == "Pickup Parts"
        assert update_fields["sku"] == "SP1081"
        assert update_fields["preco_venda"] == 129.90
        assert "dynamic_attributes" in update_fields
        dyn = update_fields["dynamic_attributes"]
        assert dyn["titulo"] == "Suporte Fixacao Apara Barro Randon 695mm"
        assert dyn["id"] == "SP1081"
        assert dyn["descricao"].startswith("Codigo: SP1081")
        assert dyn["material"] == "metal"
        assert dyn["aplicacao"] == "Todos"
        assert any("dynamic_attributes=" in note for note in notes)
        assert ignored == []

    def test_build_payload_does_not_override_existing_values():
        """Run test build payload does not override existing values in this workflow."""
        produto = _make_product(
            nome_chat_api="Nome Ja Definido",
            descricao_original="Descricao existente detalhada da peca automotiva",
            descricao_chat_api="Descricao IA existente detalhada da peca automotiva",
            imagem_principal_url="https://img.existing/principal.webp",
            marca="Marca Existente",
            sku="SKU-EXISTENTE",
            preco_venda=88.0,
            dynamic_attributes={
                "titulo": "Titulo existente",
                "id": "ID-EXISTENTE",
                "descricao": "Descricao existente detalhada",
            },
        )
        dados = {
            "nome": "Novo Nome",
            "descricao_curta": "Codigo: NOVO Material: SMC",
            "imagem_url": "https://img.test/novo.webp",
            "marca": "Nova Marca",
            "sku": "NOVO-SKU",
            "preco": "199,90",
        }
    
        update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)
    
        assert "nome_chat_api" not in update_fields
        assert "descricao_original" not in update_fields
        assert "descricao_chat_api" not in update_fields
        assert "imagem_principal_url" not in update_fields
        assert "marca" not in update_fields
        assert "sku" not in update_fields
        assert "preco_venda" not in update_fields
        assert "dynamic_attributes" in update_fields
        dyn = update_fields["dynamic_attributes"]
        assert dyn["titulo"] == "Titulo existente"
        assert dyn["id"] == "ID-EXISTENTE"
        assert dyn["descricao"] == "Descricao existente detalhada"
        # Pode complementar com novos atributos sem sobrescrever os existentes.
        assert dyn["material"] == "smc"
        assert dyn["marca"] == "Nova Marca"
        assert any("dynamic_attributes=" in note for note in notes)
        assert any(item.startswith("nome_chat_api:") for item in ignored)

    def test_build_payload_replaces_suspicious_code_on_dynamic_id():
        """Run test build payload replaces suspicious code on dynamic id in this workflow."""
        produto = _make_product(
            dynamic_attributes={
                "id": "SP1081MARCA",
            }
        )
        dados = {
            "descricao_curta": "Codigo: SP1081 Marca: XPTO",
        }
    
        update_fields, _, _ = _payload_service.build_payload_enriquecimento_visivel(produto, dados)
    
        assert "dynamic_attributes" in update_fields
        assert update_fields["dynamic_attributes"]["id"] == "SP1081"

    def test_build_payload_respects_template_key_with_suffix_using_label_alias():
        """Run test build payload respects template key with suffix using label alias in this workflow."""
        produto = _make_product(
            dynamic_attributes={},
            product_type=SimpleNamespace(
                attribute_templates=[
                    SimpleNamespace(attribute_key="titulo_auto", label="Titulo"),
                    SimpleNamespace(attribute_key="id_auto", label="ID"),
                    SimpleNamespace(attribute_key="desc_auto", label="Descricao"),
                ]
            ),
        )
        dados = {
            "nome": "Paralama Dianteiro",
            "descricao_curta": "Codigo: ABC123 Material: SMC",
            "sku": "ABC123",
        }
    
        update_fields, _, _ = _payload_service.build_payload_enriquecimento_visivel(produto, dados)
    
        dyn = update_fields["dynamic_attributes"]
        assert dyn["titulo_auto"] == "Paralama Dianteiro"
        assert dyn["id_auto"] == "ABC123"
        assert dyn["desc_auto"].startswith("Codigo: ABC123")

    def test_build_payload_migrates_existing_alias_value_to_template_key():
        """Run test build payload migrates existing alias value to template key in this workflow."""
        produto = _make_product(
            dynamic_attributes={
                "titulo": "Titulo legado",
                "id": "ID-LEGADO",
                "descricao": "Descricao legado",
            },
            product_type=SimpleNamespace(
                attribute_templates=[
                    SimpleNamespace(attribute_key="titulo_auto", label="Titulo"),
                    SimpleNamespace(attribute_key="id_auto", label="ID"),
                    SimpleNamespace(attribute_key="desc_auto", label="Descricao"),
                ]
            ),
        )
    
        update_fields, _, _ = _payload_service.build_payload_enriquecimento_visivel(produto, {})
        dyn = update_fields["dynamic_attributes"]
    
        assert dyn["titulo_auto"] == "Titulo legado"
        assert dyn["id_auto"] == "ID-LEGADO"
        assert dyn["desc_auto"] == "Descricao legado"

    def test_build_payload_replaces_weak_existing_description_and_name():
        """Run test build payload replaces weak existing description and name in this workflow."""
        produto = _make_product(
            nome_chat_api="as 927",
            descricao_original="Actros 2651 - 2016",
            descricao_chat_api="Actros 2651 - 2016",
        )
        dados = {
            "nome": "Suporte Fixacao do Para-choque",
            "descricao_curta": "Suporte de fixacao em metal com aplicacao em linha pesada.",
            "sku": "SP1081",
        }
    
        update_fields, notes, ignored = _payload_service.build_payload_enriquecimento_visivel(produto, dados)
    
        assert update_fields["nome_chat_api"] == "Suporte Fixacao do Para-choque"
        assert update_fields["descricao_original"].startswith("Suporte de fixacao")
        assert "descricao_chat_api" not in update_fields
        assert "nome_chat_api:substituido_valor_fraco" in notes
        assert "descricao_original:substituido_valor_fraco" in notes
        assert not any(item.startswith("descricao_chat_api:") for item in notes)
        assert not any(item.startswith("descricao_original:") for item in ignored)

    def test_build_payload_remove_historico_empresa_de_descricao_web():
        """Run test build payload remove historico empresa de descricao web in this workflow."""
        produto = _make_product(
            descricao_original="Actros 2651 - 2016",
            descricao_chat_api="Actros 2651 - 2016",
        )
        dados = {
            "descricao_detalhada_seo": (
                "Paralama externo em plastico reforcado. "
                "A Uouu iniciou suas atividades no ano de 2015 e atua no mercado."
            ),
        }

        update_fields, notes, _ = _payload_service.build_payload_enriquecimento_visivel(produto, dados)

        assert update_fields["descricao_original"].startswith("Paralama externo em plastico reforcado")
        assert "iniciou suas atividades" not in update_fields["descricao_original"].lower()
        assert "descricao_original:substituido_valor_fraco" in notes

    def test_source_relevance_rejects_unrelated_candidate():
        """Run test source relevance rejects unrelated candidate in this workflow."""
        produto = SimpleNamespace(
            nome_base="Parede Traseira Fechada",
            marca=None,
            sku="3192 2C456840300BB",
            ean=None,
            dados_brutos_web={},
        )
        is_relevant = _relevance_service.is_source_relevant_for_product(
            produto,
            source_name="Estribo Menor Cromado Scani 112 113",
            source_desc="Peca de acabamento para estribo scania",
            source_url="https://example.com/estribo-scania",
        )
        assert is_relevant is False

    def test_source_relevance_accepts_matching_candidate_with_code():
        """Run test source relevance accepts matching candidate with code in this workflow."""
        produto = SimpleNamespace(
            nome_base="Coluna interna",
            marca=None,
            sku="3235 E TJG809201A",
            ean=None,
            dados_brutos_web={},
        )
        is_relevant = _relevance_service.is_source_relevant_for_product(
            produto,
            source_name="Coluna Interna FD Cargo Até 2010 LE - TJG809201A",
            source_desc="Coluna interna lado esquerdo",
            source_url="https://example.com/coluna-cargo",
        )
        assert is_relevant is True

    def test_meaningful_text_rejects_error_page_content():
        """Run test meaningful text rejects error page content in this workflow."""
        text = (
            "Reference #18.45c51102.1771763903.d28fd55 "
            "https://errors.edgesuite.net/18.45c51102.1771763903.d28fd55"
        )
        assert _content_quality_service.is_meaningful_extracted_text(text) is False

    def test_meaningful_text_accepts_real_product_text():
        """Run test meaningful text accepts real product text in this workflow."""
        text = (
            "Parede Traseira Fechada para Caminhao Ford Cargo. "
            "Codigo original 2C456840300BB, material metalico, aplicacao linha pesada."
        )
        assert _content_quality_service.is_meaningful_extracted_text(text) is True

    def test_metadata_signal_rejects_low_quality_content():
        """Run test metadata signal rejects low quality content in this workflow."""
        metadata = {
            "nome": "Reference #18.45c51102",
            "descricao_curta": "errors.edgesuite.net",
            "sku": "",
        }
        assert _content_quality_service.metadata_has_minimum_signal(metadata) is False

    def test_metadata_signal_accepts_compact_product_metadata():
        """Run test metadata signal accepts compact product metadata in this workflow."""
        metadata = {
            "nome": "Coluna Interna FD Cargo Ate 2010 LE - TJG809201A",
            "descricao_curta": "Coluna interna caminhão ford cargo lado esquerdo",
            "sku": "TJG809201A",
        }
        assert _content_quality_service.metadata_has_minimum_signal(metadata) is True

_make_product = _TopLevelFunctionSurface._make_product
test_build_payload_populates_visible_fields_and_dynamic_attributes = _TopLevelFunctionSurface.test_build_payload_populates_visible_fields_and_dynamic_attributes
test_build_payload_does_not_override_existing_values = _TopLevelFunctionSurface.test_build_payload_does_not_override_existing_values
test_build_payload_replaces_suspicious_code_on_dynamic_id = _TopLevelFunctionSurface.test_build_payload_replaces_suspicious_code_on_dynamic_id
test_build_payload_respects_template_key_with_suffix_using_label_alias = _TopLevelFunctionSurface.test_build_payload_respects_template_key_with_suffix_using_label_alias
test_build_payload_migrates_existing_alias_value_to_template_key = _TopLevelFunctionSurface.test_build_payload_migrates_existing_alias_value_to_template_key
test_build_payload_replaces_weak_existing_description_and_name = _TopLevelFunctionSurface.test_build_payload_replaces_weak_existing_description_and_name
test_source_relevance_rejects_unrelated_candidate = _TopLevelFunctionSurface.test_source_relevance_rejects_unrelated_candidate
test_source_relevance_accepts_matching_candidate_with_code = _TopLevelFunctionSurface.test_source_relevance_accepts_matching_candidate_with_code
test_meaningful_text_rejects_error_page_content = _TopLevelFunctionSurface.test_meaningful_text_rejects_error_page_content
test_meaningful_text_accepts_real_product_text = _TopLevelFunctionSurface.test_meaningful_text_accepts_real_product_text
test_metadata_signal_rejects_low_quality_content = _TopLevelFunctionSurface.test_metadata_signal_rejects_low_quality_content
test_metadata_signal_accepts_compact_product_metadata = _TopLevelFunctionSurface.test_metadata_signal_accepts_compact_product_metadata
























