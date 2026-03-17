from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from Backend import schemas as real_schemas
from Backend.application.services.product_management_service import (
    ProductManagementService,
)


class _SchemasStub:
    class RegistroUsoIACreate:
        def __init__(self, **kwargs):
            self.data = kwargs

    class RegistroHistoricoCreate:
        def __init__(self, **kwargs):
            self.data = kwargs


class _ModelsStub:
    class TipoAcaoEnum:
        CRIACAO_PRODUTO = "CRIACAO_PRODUTO"

    class TipoAcaoSistemaEnum:
        CRIACAO = "CRIACAO"
        ATUALIZACAO = "ATUALIZACAO"
        DELECAO = "DELECAO"


def test_read_produto_returns_owned_product():
    produto = SimpleNamespace(id=1, user_id=3)
    service = ProductManagementService(
        models=_ModelsStub,
        schemas=_SchemasStub,
        produto_repo=SimpleNamespace(get_produto=lambda *, produto_id, user_id=None: produto),
        fornecedor_repo=SimpleNamespace(get_fornecedor=lambda **kwargs: True),
        product_type_repo=SimpleNamespace(get_product_type=lambda **kwargs: True),
        historico_repo=SimpleNamespace(create_registro_historico=lambda payload: payload),
        uso_ia_repo=SimpleNamespace(create_registro_uso_ia=lambda payload: payload),
    )

    assert service.read_produto(
        produto_id=1,
        current_user=SimpleNamespace(id=3, is_superuser=False),
    ) is produto


def test_read_produto_sanitizes_dirty_encoded_descriptions_for_response():
    dirty_product = SimpleNamespace(
        id=14513,
        user_id=3,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        nome_base="Winter Wishes Snowman Figures - 2 Assorted",
        nome_chat_api=None,
        descricao_original=(
            "This%20collection%2C%20including%20the%20Lit%20Snowman%20Scene%20Glass%20Ornaments%20-%202%20Assorted"
        ),
        descricao_chat_api=(
            "Winter Wishes Snowman Figures - 2 Assorted\n\n"
            "Winter Wishes Snowman Figures - 2 Assorted\n\n"
            "Resumo tecnico:\n"
            "This collection, including the Lit Snowman Scene Glass Ornaments - 2 Assorted, "
            "represents winter landscapes.\n"
            "Aplicacao:\nHoliday\n"
            "Referencia:\n2020220485\n"
            "Destaques tecnicos:\n"
            "- This collection, including the Lit Snowman Scene Glass Ornaments.\n"
            "- URL da fonte"
        ),
        sku="2020220485",
        ean=None,
        ncm=None,
        marca="DEMDACO",
        modelo=None,
        preco_custo=None,
        preco_venda=None,
        margem_lucro=None,
        estoque_disponivel=None,
        peso_gramas=None,
        dimensoes_cm=None,
        fornecedor_id=None,
        product_type_id=None,
        categoria_original="Holiday",
        categoria_mapeada=None,
        tags_palavras_chave=None,
        imagem_principal_url=None,
        imagens_secundarias_urls=None,
        video_url=None,
        status_enriquecimento_web=None,
        status_titulo_ia=None,
        status_descricao_ia=None,
        dados_brutos_web={
            "descricao_gerada": (
                "Winter Wishes Snowman Figures - 2 Assorted\n\n"
                "Resumo tecnico:\n"
                "This collection, including the Lit Snowman Scene Glass Ornaments - 2 Assorted, "
                "represents winter landscapes.\n"
                "Destaques tecnicos:\n"
                "- This collection, including the Lit Snowman Scene Glass Ornaments.\n"
                "- URL da fonte"
            ),
            "descricao_detalhada_seo": (
                "This%20collection%2C%20including%20the%20Lit%20Snowman%20Scene%20Glass%20Ornaments%20-%202%20Assorted"
            ),
        },
        dynamic_attributes={},
        log_enriquecimento_web=None,
        log_processamento=[],
        titulos_sugeridos=[],
        fornecedor=None,
        product_type=None,
    )

    service = ProductManagementService(
        models=_ModelsStub,
        schemas=real_schemas,
        produto_repo=SimpleNamespace(get_produto=lambda *, produto_id, user_id=None: dirty_product),
        fornecedor_repo=SimpleNamespace(get_fornecedor=lambda **kwargs: True),
        product_type_repo=SimpleNamespace(get_product_type=lambda **kwargs: True),
        historico_repo=SimpleNamespace(create_registro_historico=lambda payload: payload),
        uso_ia_repo=SimpleNamespace(create_registro_uso_ia=lambda payload: payload),
    )

    result = service.read_produto(
        produto_id=14513,
        current_user=SimpleNamespace(id=3, is_superuser=False),
    )

    assert isinstance(result, real_schemas.ProdutoResponse)
    assert "This%20collection" not in result.descricao_chat_api
    assert "This collection" not in result.descricao_chat_api
    assert "URL da fonte" not in result.descricao_chat_api
    assert "Resumo tecnico:" in result.descricao_chat_api
    assert "Conteudo da embalagem:" in result.descricao_chat_api
    assert result.descricao_chat_api.startswith("Winter Wishes Snowman Figures - 2 Assorted")
