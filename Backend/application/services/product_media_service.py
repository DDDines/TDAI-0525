"""Module product media service.

Contains backend logic related to product media service and documents its role in the OOP architecture.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException


class ProductMediaService:
    """Centraliza upload e vinculacao de imagem principal de produto."""

    def __init__(
        self,
        *,
        produto_repo: Any,
        schemas: Any,
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._produto_repo = produto_repo
        self._schemas = schemas

    @staticmethod
    def _ensure_owner_or_superuser(*, db_produto: Any, current_user: Any) -> None:
        """Run ensure owner or superuser in this workflow."""
        if not current_user.is_superuser and db_produto.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Nao autorizado a modificar este produto")

    def _get_produto_for_update(self, *, produto_id: int, current_user: Any) -> Any:
        """Run get produto for update in this workflow."""
        db_produto = self._produto_repo.get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")
        self._ensure_owner_or_superuser(db_produto=db_produto, current_user=current_user)
        return db_produto

    async def upload_produto_image(
        self,
        *,
        produto_id: int,
        file: Any,
        current_user: Any,
    ) -> Any:
        """Run upload produto image in this workflow."""
        db_produto = self._get_produto_for_update(
            produto_id=produto_id,
            current_user=current_user,
        )
        try:
            file_path_in_db = await self._produto_repo.save_produto_image(
                produto_id=produto_id,
                file=file,
            )
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
        return self._produto_repo.update_produto(
            db_produto=db_produto,
            produto_update=produto_update,
        )
