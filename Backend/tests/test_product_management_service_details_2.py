from __future__ import annotations

from types import SimpleNamespace

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
        produto_repo=SimpleNamespace(get_produto=lambda *, produto_id: produto),
        fornecedor_repo=SimpleNamespace(get_fornecedor=lambda **kwargs: True),
        product_type_repo=SimpleNamespace(get_product_type=lambda **kwargs: True),
        historico_repo=SimpleNamespace(create_registro_historico=lambda payload: payload),
        uso_ia_repo=SimpleNamespace(create_registro_uso_ia=lambda payload: payload),
    )

    assert service.read_produto(
        produto_id=1,
        current_user=SimpleNamespace(id=3, is_superuser=False),
    ) is produto
