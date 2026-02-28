"""Legacy CRUD package root kept for import compatibility.

This module now exposes only workflow classes/getters.
Procedural helper functions were removed in the OOP cleanup.
"""

from .crud_fornecedor_import_jobs import (
    FornecedorImportJobWorkflow,
    get_fornecedor_import_job_workflow,
)
from .crud_fornecedores import FornecedorCrudWorkflow, get_fornecedor_crud_workflow
from .crud_historico import HistoricoCrudWorkflow, get_historico_crud_workflow
from .crud_product_types import ProductTypeCrudWorkflow, get_product_type_crud_workflow
from .crud_produtos import ProdutoCrudWorkflow, get_produto_crud_workflow
from .crud_registros_uso_ia import (
    RegistroUsoIACrudWorkflow,
    get_registro_uso_ia_crud_workflow,
)
from .crud_users import UserCrudWorkflow, get_user_crud_workflow

__all__ = [
    "FornecedorImportJobWorkflow",
    "FornecedorCrudWorkflow",
    "HistoricoCrudWorkflow",
    "ProductTypeCrudWorkflow",
    "ProdutoCrudWorkflow",
    "RegistroUsoIACrudWorkflow",
    "UserCrudWorkflow",
    "get_fornecedor_import_job_workflow",
    "get_fornecedor_crud_workflow",
    "get_historico_crud_workflow",
    "get_product_type_crud_workflow",
    "get_produto_crud_workflow",
    "get_registro_uso_ia_crud_workflow",
    "get_user_crud_workflow",
]
