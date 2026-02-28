from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from Backend.crud_fornecedor_import_jobs import (
    FornecedorImportJobWorkflow,
    get_fornecedor_import_job_workflow,
)
from Backend.crud_fornecedores import (
    FornecedorCrudWorkflow,
    get_fornecedor_crud_workflow,
)
from Backend.crud_historico import HistoricoCrudWorkflow, get_historico_crud_workflow
from Backend.crud_product_types import (
    ProductTypeCrudWorkflow,
    get_product_type_crud_workflow,
)
from Backend.crud_produtos import ProdutoCrudWorkflow, get_produto_crud_workflow
from Backend.crud_registros_uso_ia import (
    RegistroUsoIACrudWorkflow,
    get_registro_uso_ia_crud_workflow,
)
from Backend.crud_users import UserCrudWorkflow, get_user_crud_workflow


class UserDataAccessService:
    """Explicit user/plans CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[UserCrudWorkflow] = None) -> None:
        self._workflow = workflow or get_user_crud_workflow()

    def get_user(self, db: Any, *, user_id: int):
        return self._workflow.get_user(db=db, user_id=user_id)

    def get_planos(self, db: Any, *, skip: int, limit: int):
        return self._workflow.get_planos(db=db, skip=skip, limit=limit)

    def get_users(self, db: Any, *, skip: int, limit: int):
        return self._workflow.get_users(db=db, skip=skip, limit=limit)

    def get_user_by_email(self, db: Any, *, email: str):
        return self._workflow.get_user_by_email(db=db, email=email)

    def set_user_password_reset_token(
        self,
        db: Any,
        user: Any,
        *,
        token_hash: str,
        expires_at: Any,
    ) -> None:
        self._workflow.set_user_password_reset_token(
            db=db,
            user=user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def get_user_by_reset_token(self, db: Any, *, token_hash: str):
        return self._workflow.get_user_by_reset_token(db=db, token_hash=token_hash)

    def update_user(self, *, db: Any, db_user: Any, user_update: Any):
        return self._workflow.update_user(
            db=db,
            db_user=db_user,
            user_update=user_update,
        )

    def get_role_by_name(self, db: Any, *, name: str):
        return self._workflow.get_role_by_name(db=db, name=name)

    def create_role(self, db: Any, *, role: Any):
        return self._workflow.create_role(db=db, role=role)

    def get_plano_by_name(self, db: Any, nome: str):
        return self._workflow.get_plano_by_name(db=db, nome=nome)

    def create_plano(self, db: Any, *, plano: Any):
        return self._workflow.create_plano(db=db, plano=plano)

    def create_user(self, *, db: Any, user: Any):
        return self._workflow.create_user(db=db, user=user)

    def create_user_oauth(
        self,
        *,
        db: Any,
        user_oauth: Any,
        plano_id_default: Optional[int],
    ):
        return self._workflow.create_user_oauth(
            db=db,
            user_oauth=user_oauth,
            plano_id_default=plano_id_default,
        )


class HistoricoDataAccessService:
    """Explicit historico CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[HistoricoCrudWorkflow] = None) -> None:
        self._workflow = workflow or get_historico_crud_workflow()

    def get_registros_historico(
        self,
        db: Any,
        *,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return self._workflow.get_registros_historico(
            db=db,
            user_id=user_id,
            skip=skip,
            limit=limit,
        )

    def count_registros_historico(
        self,
        db: Any,
        *,
        user_id: Optional[int] = None,
    ) -> int:
        return self._workflow.count_registros_historico(db=db, user_id=user_id)

    def create_registro_historico(self, db: Any, payload: Any):
        return self._workflow.create_registro_historico(db=db, registro_in=payload)


class ProductTypeDataAccessService:
    """Explicit product type CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[ProductTypeCrudWorkflow] = None) -> None:
        self._workflow = workflow or get_product_type_crud_workflow()

    def get_product_type_by_key_name(
        self,
        db: Any,
        *,
        key_name: str,
        user_id: Optional[int],
    ):
        return self._workflow.get_product_type_by_key_name(
            db=db,
            key_name=key_name,
            user_id=user_id,
        )

    def create_product_type(
        self,
        db: Any,
        *,
        product_type_create: Any,
        user_id: Optional[int],
    ):
        return self._workflow.create_product_type(
            db=db,
            product_type_create=product_type_create,
            user_id=user_id,
        )

    def get_product_types_for_user(
        self,
        db: Any,
        *,
        skip: int,
        limit: int,
        user_id: int,
    ):
        return self._workflow.get_product_types_for_user(
            db=db,
            skip=skip,
            limit=limit,
            user_id=user_id,
        )

    def get_product_type(self, db: Any, *, product_type_id: int):
        return self._workflow.get_product_type(db=db, product_type_id=product_type_id)

    def update_product_type(
        self,
        db: Any,
        *,
        db_product_type: Any,
        product_type_update: Any,
    ):
        return self._workflow.update_product_type(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_update,
        )

    def delete_product_type(self, db: Any, *, db_product_type: Any):
        return self._workflow.delete_product_type(
            db=db,
            db_product_type=db_product_type,
        )

    def create_attribute_template(
        self,
        db: Any,
        *,
        attr_template_create: Any,
        product_type_id: int,
    ):
        return self._workflow.create_attribute_template(
            db=db,
            attr_template_create=attr_template_create,
            product_type_id=product_type_id,
        )

    def get_attribute_template(self, db: Any, *, attribute_id: int):
        return self._workflow.get_attribute_template(
            db=db,
            attribute_template_id=attribute_id,
        )

    def update_attribute_template(
        self,
        db: Any,
        *,
        db_attr_template: Any,
        attr_template_update: Any,
    ):
        return self._workflow.update_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
            attr_template_update=attr_template_update,
        )

    def delete_attribute_template(self, db: Any, *, db_attr_template: Any):
        return self._workflow.delete_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
        )

    def reorder_attribute_template(
        self,
        db: Any,
        *,
        attribute_id: int,
        direction: str,
    ):
        return self._workflow.reorder_attribute_template(
            db=db,
            attribute_id=attribute_id,
            direction=direction,
        )


class ProdutoDataAccessService:
    """Explicit produto CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[ProdutoCrudWorkflow] = None) -> None:
        self._workflow = workflow or get_produto_crud_workflow()

    def get_produto(self, db: Any, *, produto_id: int):
        return self._workflow.get_produto(db=db, produto_id=produto_id)

    def create_produto(self, *, db: Any, produto: Any, user_id: int):
        return self._workflow.create_produto(db=db, produto=produto, user_id=user_id)

    def get_produtos_by_user(self, db: Any, **kwargs: Any):
        return self._workflow.get_produtos_by_user(db=db, **kwargs)

    def count_produtos_by_user(self, db: Any, **kwargs: Any):
        return self._workflow.count_produtos_by_user(db=db, **kwargs)

    def update_produto(self, db: Any, **kwargs: Any):
        return self._workflow.update_produto(db=db, **kwargs)

    def delete_produto(self, *, db: Any, db_produto: Any):
        return self._workflow.delete_produto(db=db, db_produto=db_produto)

    async def save_produto_image(self, db: Any, produto_id: int, file: Any):
        return await self._workflow.save_produto_image(db=db, produto_id=produto_id, file=file)

    def get_or_create_produto(self, db: Any, produto_schema: Any, user_id: int):
        return self._workflow.get_or_create_produto(
            db=db,
            produto=produto_schema,
            user_id=user_id,
        )

    def create_produtos_bulk(self, db: Any, produtos_data: Any, user_id: int):
        return self._workflow.create_produtos_bulk(
            db=db,
            produtos=produtos_data,
            user_id=user_id,
        )


class UsoIADataAccessService:
    """Explicit usage CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[RegistroUsoIACrudWorkflow] = None) -> None:
        self._workflow = workflow or get_registro_uso_ia_crud_workflow()

    def create_registro_uso_ia(self, *args: Any, **kwargs: Any):
        return self._workflow.create_registro_uso_ia(*args, **kwargs)

    def get_registros_uso_ia(self, db: Any, **kwargs: Any):
        return self._workflow.get_registros_uso_ia(db=db, **kwargs)

    def count_registros_uso_ia(self, db: Any, **kwargs: Any):
        return self._workflow.count_registros_uso_ia(db=db, **kwargs)

    def get_usos_ia_by_produto(self, db: Any, **kwargs: Any):
        return self._workflow.get_usos_ia_by_produto(db=db, **kwargs)


class FornecedorDataAccessService:
    """Explicit fornecedor CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[FornecedorCrudWorkflow] = None) -> None:
        self._workflow = workflow or get_fornecedor_crud_workflow()

    def get_fornecedor(self, db: Any, fornecedor_id: int):
        return self._workflow.get_fornecedor(db=db, fornecedor_id=fornecedor_id)

    def create_fornecedor(self, *, db: Any, fornecedor: Any, user_id: int):
        return self._workflow.create_fornecedor(
            db=db,
            fornecedor=fornecedor,
            user_id=user_id,
        )

    def get_fornecedores_by_user(self, db: Any, **kwargs: Any):
        return self._workflow.get_fornecedores_by_user(db=db, **kwargs)

    def count_fornecedores_by_user(
        self,
        *,
        db: Any,
        user_id: int,
        search: Optional[str] = None,
    ):
        return self._workflow.count_fornecedores_by_user(
            db=db,
            user_id=user_id,
            search=search,
        )

    def update_fornecedor(self, *, db: Any, db_fornecedor: Any, fornecedor_update: Any):
        return self._workflow.update_fornecedor(
            db=db,
            db_fornecedor=db_fornecedor,
            fornecedor_update=fornecedor_update,
        )

    def delete_fornecedor(self, *, db: Any, db_fornecedor: Any):
        return self._workflow.delete_fornecedor(
            db=db,
            db_fornecedor=db_fornecedor,
        )


class FornecedorImportJobDataAccessService:
    """Explicit fornecedor import job CRUD access used by router runtimes."""

    def __init__(self, workflow: Optional[FornecedorImportJobWorkflow] = None) -> None:
        self._workflow = workflow or get_fornecedor_import_job_workflow()

    def get_import_job(self, db: Any, job_id: int):
        return self._workflow.get_import_job(db=db, job_id=job_id)

    def update_job_status(self, db: Any, job: Any, new_status: str):
        return self._workflow.update_job_status(db=db, job=job, status=new_status)


@dataclass
class DataAccessService:
    users: UserDataAccessService = field(default_factory=UserDataAccessService)
    historico: HistoricoDataAccessService = field(default_factory=HistoricoDataAccessService)
    product_types: ProductTypeDataAccessService = field(default_factory=ProductTypeDataAccessService)
    produtos: ProdutoDataAccessService = field(default_factory=ProdutoDataAccessService)
    uso_ia: UsoIADataAccessService = field(default_factory=UsoIADataAccessService)
    fornecedores: FornecedorDataAccessService = field(default_factory=FornecedorDataAccessService)
    fornecedor_import_jobs: FornecedorImportJobDataAccessService = field(
        default_factory=FornecedorImportJobDataAccessService
    )


data_access_service = DataAccessService()
