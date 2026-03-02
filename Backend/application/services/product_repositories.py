"""Document product repositories module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)


# Aliases preservando contratos existentes na camada de aplicacao.
ProdutoRepository = ProductRepository
UsoIARepository = RegistroUsoIARepository


class ProductRepositories:
    """Factories OO para composicao de repositorios da camada de aplicacao."""

    @staticmethod
    def build_product_management_repositories(*, session: Any) -> dict[str, Any]:
        """Build product management repositories from current inputs and configuration."""
        return {
            "produto_repo": ProductRepository(session),
            "fornecedor_repo": FornecedorRepository(session),
            "product_type_repo": ProductTypeRepository(session),
            "historico_repo": HistoricoRepository(session),
            "uso_ia_repo": RegistroUsoIARepository(session),
        }

    @staticmethod
    def build_product_media_repositories(*, session: Any) -> dict[str, Any]:
        """Build product media repositories from current inputs and configuration."""
        return {
            "produto_repo": ProductRepository(session),
        }

