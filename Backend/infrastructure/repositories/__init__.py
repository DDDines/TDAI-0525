"""Initialize repositories package exports and integration boundaries."""

from Backend.infrastructure.repositories.fornecedor_import_job_repository import (
    FornecedorImportJobRepository,
)
from Backend.infrastructure.repositories.catalog_import_file_repository import (
    CatalogImportFileRepository,
)
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository

__all__ = [
    "CatalogImportFileRepository",
    "FornecedorImportJobRepository",
    "FornecedorRepository",
    "HistoricoRepository",
    "ProductRepository",
    "ProductTypeRepository",
    "RegistroUsoIARepository",
    "UserRepository",
]
