from __future__ import annotations

from typing import Any, Optional


class ProdutoRepository:
    """Repositorio de produto com sessao vinculada na borda HTTP."""

    def __init__(self, *, data_access: Any, db: Any) -> None:
        self._data_access = data_access
        self._db = db

    def create_produto(self, *, produto: Any, user_id: int) -> Any:
        return self._data_access.create_produto(
            db=self._db,
            produto=produto,
            user_id=user_id,
        )

    def get_produto(self, *, produto_id: int) -> Any:
        return self._data_access.get_produto(self._db, produto_id=produto_id)

    def get_produtos_by_user(self, **kwargs: Any) -> Any:
        return self._data_access.get_produtos_by_user(self._db, **kwargs)

    def count_produtos_by_user(self, **kwargs: Any) -> int:
        return self._data_access.count_produtos_by_user(self._db, **kwargs)

    def update_produto(self, **kwargs: Any) -> Any:
        return self._data_access.update_produto(self._db, **kwargs)

    def delete_produto(self, *, db_produto: Any) -> Any:
        return self._data_access.delete_produto(db=self._db, db_produto=db_produto)

    async def save_produto_image(self, *, produto_id: int, file: Any) -> str:
        return await self._data_access.save_produto_image(self._db, produto_id, file)


class FornecedorRepository:
    """Repositorio de fornecedor com sessao vinculada na borda HTTP."""

    def __init__(self, *, data_access: Any, db: Any) -> None:
        self._data_access = data_access
        self._db = db

    def get_fornecedor(self, *, fornecedor_id: int) -> Any:
        return self._data_access.get_fornecedor(self._db, fornecedor_id=fornecedor_id)


class ProductTypeRepository:
    """Repositorio de tipo de produto com sessao vinculada na borda HTTP."""

    def __init__(self, *, data_access: Any, db: Any) -> None:
        self._data_access = data_access
        self._db = db

    def get_product_type(self, *, product_type_id: int) -> Any:
        return self._data_access.get_product_type(
            self._db,
            product_type_id=product_type_id,
        )


class HistoricoRepository:
    """Repositorio de historico com sessao vinculada na borda HTTP."""

    def __init__(self, *, data_access: Any, db: Any) -> None:
        self._data_access = data_access
        self._db = db

    def create_registro_historico(self, payload: Any) -> Any:
        return self._data_access.create_registro_historico(self._db, payload)


class UsoIARepository:
    """Repositorio de uso de IA com sessao vinculada na borda HTTP."""

    def __init__(self, *, data_access: Any, db: Any) -> None:
        self._data_access = data_access
        self._db = db

    def create_registro_uso_ia(self, payload: Any) -> Any:
        return self._data_access.create_registro_uso_ia(
            self._db,
            registro_uso=payload,
        )


def build_product_management_repositories(*, data_access_service: Any, db: Any) -> dict[str, Any]:
    return {
        "produto_repo": ProdutoRepository(data_access=data_access_service.produtos, db=db),
        "fornecedor_repo": FornecedorRepository(
            data_access=data_access_service.fornecedores,
            db=db,
        ),
        "product_type_repo": ProductTypeRepository(
            data_access=data_access_service.product_types,
            db=db,
        ),
        "historico_repo": HistoricoRepository(data_access=data_access_service.historico, db=db),
        "uso_ia_repo": UsoIARepository(data_access=data_access_service.uso_ia, db=db),
    }


def build_product_media_repositories(*, data_access_service: Any, db: Any) -> dict[str, Any]:
    return {
        "produto_repo": ProdutoRepository(data_access=data_access_service.produtos, db=db),
    }
