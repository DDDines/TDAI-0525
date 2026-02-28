from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from Backend import crud
from Backend import crud_historico
from Backend import crud_product_types
from Backend import crud_produtos
from Backend import crud_users


class UserDataAccessService:
    """Explicit user/plans CRUD access used by router runtimes."""

    def get_user(self, db: Any, *, user_id: int):
        return crud_users.get_user(db, user_id=user_id)

    def get_planos(self, db: Any, *, skip: int, limit: int):
        return crud_users.get_planos(db, skip=skip, limit=limit)

    def get_users(self, db: Any, *, skip: int, limit: int):
        return crud_users.get_users(db, skip=skip, limit=limit)

    def get_user_by_email(self, db: Any, *, email: str):
        return crud_users.get_user_by_email(db, email=email)

    def set_user_password_reset_token(
        self,
        db: Any,
        user: Any,
        *,
        token_hash: str,
        expires_at: Any,
    ) -> None:
        crud_users.set_user_password_reset_token(
            db,
            user,
            token_hash=token_hash,
            expires_at=expires_at,
        )

    def get_user_by_reset_token(self, db: Any, *, token_hash: str):
        return crud_users.get_user_by_reset_token(db, token_hash=token_hash)


class HistoricoDataAccessService:
    """Explicit historico CRUD access used by router runtimes."""

    def get_registros_historico(
        self,
        db: Any,
        *,
        user_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ):
        return crud_historico.get_registros_historico(
            db,
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
        return crud_historico.count_registros_historico(db, user_id=user_id)

    def create_registro_historico(self, db: Any, payload: Any):
        return crud_historico.create_registro_historico(db, payload)


class ProductTypeDataAccessService:
    """Explicit product type CRUD access used by router runtimes."""

    def get_product_type_by_key_name(
        self,
        db: Any,
        *,
        key_name: str,
        user_id: Optional[int],
    ):
        return crud_product_types.get_product_type_by_key_name(
            db,
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
        return crud_product_types.create_product_type(
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
        return crud_product_types.get_product_types_for_user(
            db,
            skip=skip,
            limit=limit,
            user_id=user_id,
        )

    def get_product_type(self, db: Any, *, product_type_id: int):
        return crud_product_types.get_product_type(db, product_type_id=product_type_id)

    def update_product_type(
        self,
        db: Any,
        *,
        db_product_type: Any,
        product_type_update: Any,
    ):
        return crud_product_types.update_product_type(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_update,
        )

    def delete_product_type(self, db: Any, *, db_product_type: Any):
        return crud_product_types.delete_product_type(
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
        return crud_product_types.create_attribute_template(
            db=db,
            attr_template_create=attr_template_create,
            product_type_id=product_type_id,
        )

    def get_attribute_template(self, db: Any, *, attribute_id: int):
        return crud_product_types.get_attribute_template(db, attribute_id)

    def update_attribute_template(
        self,
        db: Any,
        *,
        db_attr_template: Any,
        attr_template_update: Any,
    ):
        return crud_product_types.update_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
            attr_template_update=attr_template_update,
        )

    def delete_attribute_template(self, db: Any, *, db_attr_template: Any):
        return crud_product_types.delete_attribute_template(
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
        return crud_product_types.reorder_attribute_template(
            db,
            attribute_id=attribute_id,
            direction=direction,
        )


class ProdutoDataAccessService:
    """Explicit produto CRUD access used by router runtimes."""

    def get_produto(self, db: Any, *, produto_id: int):
        return crud_produtos.get_produto(db, produto_id=produto_id)


class UsoIADataAccessService:
    """Explicit usage CRUD access used by router runtimes."""

    def create_registro_uso_ia(self, db: Any, *, registro_uso: Any):
        return crud.create_registro_uso_ia(db, registro_uso=registro_uso)

    def get_registros_uso_ia(self, db: Any, **kwargs: Any):
        return crud.get_registros_uso_ia(db, **kwargs)

    def count_registros_uso_ia(self, db: Any, **kwargs: Any):
        return crud.count_registros_uso_ia(db, **kwargs)

    def get_usos_ia_by_produto(self, db: Any, **kwargs: Any):
        return crud.get_usos_ia_by_produto(db, **kwargs)


@dataclass
class DataAccessService:
    users: UserDataAccessService = field(default_factory=UserDataAccessService)
    historico: HistoricoDataAccessService = field(default_factory=HistoricoDataAccessService)
    product_types: ProductTypeDataAccessService = field(default_factory=ProductTypeDataAccessService)
    produtos: ProdutoDataAccessService = field(default_factory=ProdutoDataAccessService)
    uso_ia: UsoIADataAccessService = field(default_factory=UsoIADataAccessService)


data_access_service = DataAccessService()

