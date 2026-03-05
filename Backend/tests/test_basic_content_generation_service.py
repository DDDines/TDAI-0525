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


_build_service = _TopLevelFunctionSurface._build_service
test_gerar_titulos_basicos_respeita_limite = _TopLevelFunctionSurface.test_gerar_titulos_basicos_respeita_limite
test_gerar_descricao_basica_inclui_campos_relevantes = _TopLevelFunctionSurface.test_gerar_descricao_basica_inclui_campos_relevantes

