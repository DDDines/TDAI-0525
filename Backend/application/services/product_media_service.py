from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ProductMediaService:
    """Centraliza upload e vinculacao de imagem principal de produto."""

    def __init__(
        self,
        *,
        crud_produtos: Any,
        schemas: Any,
    ) -> None:
        self._crud_produtos = crud_produtos
        self._schemas = schemas

    @staticmethod
    def _ensure_owner_or_superuser(*, db_produto: Any, current_user: Any) -> None:
        if not current_user.is_superuser and db_produto.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Nao autorizado a modificar este produto")

    def _get_produto_for_update(self, *, db: Any, produto_id: int, current_user: Any) -> Any:
        db_produto = self._crud_produtos.get_produto(db, produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")
        self._ensure_owner_or_superuser(db_produto=db_produto, current_user=current_user)
        return db_produto

    async def upload_produto_image(
        self,
        *,
        db: Any,
        produto_id: int,
        file: Any,
        current_user: Any,
    ) -> Any:
        db_produto = self._get_produto_for_update(
            db=db,
            produto_id=produto_id,
            current_user=current_user,
        )
        try:
            file_path_in_db = await self._crud_produtos.save_produto_image(db, produto_id, file)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except IOError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail=f"Nao foi possivel salvar a imagem: {str(exc)}",
            ) from exc

        produto_update = self._schemas.ProdutoUpdate(imagem_principal_url=file_path_in_db)
        return self._crud_produtos.update_produto(
            db=db,
            db_produto=db_produto,
            produto_update=produto_update,
        )
