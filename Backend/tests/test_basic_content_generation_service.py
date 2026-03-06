"""Module test basic content generation service.

Contains backend logic related to test basic content generation service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from Backend.application.services.basic_content_generation_service import (
    BasicContentGenerationService,
)


class _TopLevelFunctionSurface:

    """Represent top level function surface and centralize responsibilities for this module."""
    @staticmethod
    def _build_service(produto):
        """Build service with a repository stub bound to a product fixture."""

        class _ProductRepositoryStub:
            """Repository stub exposing only the method used by the service."""

            def __init__(self, _session):
                """Initialize collaborators and configuration required by this component."""
                self._produto = produto

            def get_produto(self, *, produto_id):
                """Return the configured product fixture."""
                _ = produto_id
                return self._produto

        return BasicContentGenerationService(
            product_repository_factory=_ProductRepositoryStub
        )

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_respeita_limite():
        """Run test gerar titulos basicos respeita limite in this workflow."""
        produto = SimpleNamespace(
            id=10,
            nome_base="Filtro de Ar",
            marca="Bosch",
            modelo="X1",
            sku="ABC123",
            ean="7891234567890",
            categoria_original="Filtro",
            categoria_mapeada=None,
            fornecedor=SimpleNamespace(nome="Fornecedor A"),
            dynamic_attributes={},
            dados_brutos_web={},
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=10,
            user=SimpleNamespace(id=1),
            num_titulos=2,
        )

        assert len(titulos) == 2
        assert any("Filtro de Ar" in titulo for titulo in titulos)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_inclui_campos_relevantes():
        """Run test gerar descricao basica inclui campos relevantes in this workflow."""
        produto = SimpleNamespace(
            id=20,
            nome_base="Pastilha de Freio",
            marca="MarcaX",
            modelo="PX-20",
            sku="PF20",
            ean="",
            categoria_original="Freios",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={
                "Material": "Ceramica",
                "Aplicacao": "Dianteira",
            },
            dados_brutos_web={
                "descricao_curta": "Composto com alta resistencia termica.",
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=20,
            user=SimpleNamespace(id=1),
            tamanho_palavras=80,
        )

        assert "Pastilha de Freio" in descricao
        assert "SKU: PF20" in descricao
        assert "Material: Ceramica" in descricao

    @pytest.mark.asyncio
    async def test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes():
        """Run test gerar titulos basicos padrao entrega cinco opcoes in this workflow."""
        produto = SimpleNamespace(
            id=30,
            nome_base="Paralama Dianteiro",
            marca="Pickup Parts",
            modelo="FD-2010",
            sku="PP-1081",
            ean="",
            categoria_original="Lataria",
            categoria_mapeada=None,
            fornecedor=SimpleNamespace(nome="Fornecedor B"),
            dynamic_attributes={},
            dados_brutos_web={
                "palavras_chave_seo_relevantes_lista": [
                    "paralama",
                    "ford cargo",
                    "linha pesada",
                ],
                "especificacoes_tecnicas_dict": {
                    "Aplicacao": "Ford Cargo",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        titulos = await service.gerar_titulos_basicos(
            session=object(),
            produto_id=30,
            user=SimpleNamespace(id=1),
        )

        assert len(titulos) == 5
        assert any("Paralama Dianteiro" in titulo for titulo in titulos)

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_aproveita_contexto_web():
        """Run test gerar descricao basica aproveita contexto web in this workflow."""
        produto = SimpleNamespace(
            id=31,
            nome_base="Suporte de Fixacao",
            marca="Pickup Parts",
            modelo="SP1081",
            sku="SP1081",
            ean="7890000000000",
            categoria_original="Fixacao",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": "Suporte reforcado para linha pesada e alta durabilidade.",
                "lista_caracteristicas_beneficios_bullets": [
                    "Estrutura em metal resistente",
                    "Instalacao simplificada",
                ],
                "palavras_chave_seo_relevantes_lista": [
                    "suporte reforcado",
                    "linha pesada",
                ],
                "especificacoes_tecnicas_dict": {
                    "Material": "Metal",
                    "Aplicacao": "Caminhoes",
                },
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=31,
            user=SimpleNamespace(id=1),
            tamanho_palavras=160,
        )

        assert "Suporte reforcado para linha pesada" in descricao
        assert "Destaques:" in descricao
        assert "Palavras-chave:" in descricao
        assert "Material: Metal" in descricao

    @pytest.mark.asyncio
    async def test_gerar_descricao_basica_remove_historico_empresa_inferido():
        """Run test gerar descricao basica remove historico empresa inferido in this workflow."""
        produto = SimpleNamespace(
            id=32,
            nome_base="Paralama Externo",
            marca="Rodoplast",
            modelo="IV-FD",
            sku="900484",
            ean="",
            categoria_original="Lataria",
            categoria_mapeada=None,
            fornecedor=None,
            dynamic_attributes={},
            dados_brutos_web={
                "descricao_detalhada_seo": (
                    "Paralama externo em plastico reforcado. "
                    "A Uouu iniciou suas atividades no ano de 2015 e segue no mercado."
                ),
            },
        )
        service = _TopLevelFunctionSurface._build_service(produto)

        descricao = await service.gerar_descricao_basica(
            session=object(),
            produto_id=32,
            user=SimpleNamespace(id=1),
            tamanho_palavras=120,
        )

        assert "Paralama externo em plastico reforcado" in descricao
        assert "iniciou suas atividades" not in descricao.lower()
        assert "ano de 2015" not in descricao.lower()


_build_service = _TopLevelFunctionSurface._build_service
test_gerar_titulos_basicos_respeita_limite = _TopLevelFunctionSurface.test_gerar_titulos_basicos_respeita_limite
test_gerar_descricao_basica_inclui_campos_relevantes = _TopLevelFunctionSurface.test_gerar_descricao_basica_inclui_campos_relevantes
test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes = _TopLevelFunctionSurface.test_gerar_titulos_basicos_padrao_entrega_cinco_opcoes
test_gerar_descricao_basica_aproveita_contexto_web = _TopLevelFunctionSurface.test_gerar_descricao_basica_aproveita_contexto_web
test_gerar_descricao_basica_remove_historico_empresa_inferido = _TopLevelFunctionSurface.test_gerar_descricao_basica_remove_historico_empresa_inferido
