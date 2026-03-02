"""Document product management service module responsibilities and runtime integration points."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class ProductManagementService:
    """Centraliza regras CRUD de produtos e validacoes de ownership."""

    def __init__(
        self,
        *,
        models: Any,
        schemas: Any,
        produto_repo: Any,
        fornecedor_repo: Any,
        product_type_repo: Any,
        historico_repo: Any,
        uso_ia_repo: Any,
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Product Management Service."""
        self._models = models
        self._schemas = schemas
        self._produto_repo = produto_repo
        self._fornecedor_repo = fornecedor_repo
        self._product_type_repo = product_type_repo
        self._historico_repo = historico_repo
        self._uso_ia_repo = uso_ia_repo

    @staticmethod
    def _ensure_owner_or_superuser(*, db_obj: Any, current_user: Any, forbidden_detail: str) -> None:
        """Ensure owner or superuser exists or is valid before continuing the flow."""
        if not current_user.is_superuser and db_obj.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=forbidden_detail)

    def _get_produto_or_404(self, *, produto_id: int) -> Any:
        """Retrieve produto or 404 using the current service dependencies."""
        db_produto = self._produto_repo.get_produto(produto_id=produto_id)
        if db_produto is None:
            raise HTTPException(status_code=404, detail="Produto nao encontrado")
        return db_produto

    def _ensure_fornecedor_exists(self, *, fornecedor_id: int) -> None:
        """Ensure fornecedor exists exists or is valid before continuing the flow."""
        fornecedor = self._fornecedor_repo.get_fornecedor(fornecedor_id=fornecedor_id)
        if not fornecedor:
            raise HTTPException(
                status_code=404,
                detail=f"Fornecedor com ID {fornecedor_id} nao encontrado.",
            )

    def _ensure_product_type_exists(self, *, product_type_id: int) -> None:
        """Ensure product type exists exists or is valid before continuing the flow."""
        product_type = self._product_type_repo.get_product_type(
            product_type_id=product_type_id,
        )
        if not product_type:
            raise HTTPException(
                status_code=404,
                detail=f"Tipo de Produto com ID {product_type_id} nao encontrado.",
            )

    def create_produto(
        self,
        *,
        produto: Any,
        current_user: Any,
    ) -> Any:
        """Create produto and return the resulting payload or entity."""
        if getattr(produto, "fornecedor_id", None):
            self._ensure_fornecedor_exists(fornecedor_id=produto.fornecedor_id)
        if getattr(produto, "product_type_id", None):
            self._ensure_product_type_exists(
                product_type_id=produto.product_type_id,
            )

        db_produto = self._produto_repo.create_produto(
            produto=produto,
            user_id=current_user.id,
        )
        self._uso_ia_repo.create_registro_uso_ia(
            self._schemas.RegistroUsoIACreate(
                user_id=current_user.id,
                produto_id=db_produto.id,
                tipo_acao=self._models.TipoAcaoEnum.CRIACAO_PRODUTO,
                creditos_consumidos=0,
            ),
        )
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Produto",
                acao=self._models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=db_produto.id,
            ),
        )
        return db_produto

    def read_produto(
        self,
        *,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        """Execute read produto as part of this module workflow."""
        db_produto = self._get_produto_or_404(produto_id=produto_id)
        self._ensure_owner_or_superuser(
            db_obj=db_produto,
            current_user=current_user,
            forbidden_detail="Nao autorizado a visualizar este produto",
        )
        return db_produto

    def list_produtos(
        self,
        *,
        skip: int,
        limit: int,
        sort_by: str | None,
        sort_order: str | None,
        search: str | None,
        fornecedor_id: int | None,
        categoria: str | None,
        status_enriquecimento_web: Any,
        status_titulo_ia: Any,
        status_descricao_ia: Any,
        product_type_id: int | None,
        current_user: Any,
    ) -> dict[str, Any]:
        """Execute list produtos as part of this module workflow."""
        user_id_filter = None if current_user.is_superuser else current_user.id
        items = self._produto_repo.get_produtos_by_user(
            user_id=user_id_filter,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
            product_type_id=product_type_id,
            is_admin=current_user.is_superuser,
        )
        total_items = self._produto_repo.count_produtos_by_user(
            user_id=user_id_filter,
            search=search,
            fornecedor_id=fornecedor_id,
            categoria=categoria,
            status_enriquecimento_web=status_enriquecimento_web,
            status_titulo_ia=status_titulo_ia,
            status_descricao_ia=status_descricao_ia,
            product_type_id=product_type_id,
            is_admin=current_user.is_superuser,
        )
        return {
            "items": items,
            "total_items": total_items,
            "page": skip // limit + 1,
            "limit": limit,
        }

    def update_produto(
        self,
        *,
        produto_id: int,
        produto_update: Any,
        current_user: Any,
    ) -> Any:
        """Update produto and persist the resulting state changes."""
        db_produto = self._get_produto_or_404(produto_id=produto_id)
        self._ensure_owner_or_superuser(
            db_obj=db_produto,
            current_user=current_user,
            forbidden_detail="Nao autorizado a modificar este produto",
        )

        if (
            produto_update.fornecedor_id is not None
            and produto_update.fornecedor_id != db_produto.fornecedor_id
        ):
            self._ensure_fornecedor_exists(
                fornecedor_id=produto_update.fornecedor_id,
            )
        if (
            produto_update.product_type_id is not None
            and produto_update.product_type_id != db_produto.product_type_id
        ):
            self._ensure_product_type_exists(
                product_type_id=produto_update.product_type_id,
            )

        updated = self._produto_repo.update_produto(
            db_produto=db_produto,
            produto_update=produto_update,
        )
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Produto",
                acao=self._models.TipoAcaoSistemaEnum.ATUALIZACAO,
                entity_id=updated.id,
            ),
        )
        return updated

    def delete_produto(
        self,
        *,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        """Execute delete produto as part of this module workflow."""
        db_produto = self._get_produto_or_404(produto_id=produto_id)
        self._ensure_owner_or_superuser(
            db_obj=db_produto,
            current_user=current_user,
            forbidden_detail="Nao autorizado a deletar este produto",
        )
        deleted = self._produto_repo.delete_produto(db_produto=db_produto)
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Produto",
                acao=self._models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted.id,
            ),
        )
        return deleted

    def batch_delete_produtos(
        self,
        *,
        produto_ids: list[int],
        current_user: Any,
    ) -> list[Any]:
        """Execute batch delete produtos as part of this module workflow."""
        deleted_produtos: list[Any] = []
        not_found_ids: list[int] = []
        not_authorized_ids: list[int] = []

        for produto_id in produto_ids:
            db_produto = self._produto_repo.get_produto(produto_id=produto_id)
            if db_produto is None:
                not_found_ids.append(produto_id)
                continue
            if not current_user.is_superuser and db_produto.user_id != current_user.id:
                not_authorized_ids.append(produto_id)
                continue

            self._produto_repo.delete_produto(db_produto=db_produto)
            self._historico_repo.create_registro_historico(
                self._schemas.RegistroHistoricoCreate(
                    user_id=current_user.id,
                    entidade="Produto",
                    acao=self._models.TipoAcaoSistemaEnum.DELECAO,
                    entity_id=db_produto.id,
                ),
            )
            deleted_produtos.append(db_produto)

        if not_found_ids or not_authorized_ids:
            error_detail_parts = []
            if not_found_ids:
                error_detail_parts.append(f"Produtos nao encontrados: IDs {not_found_ids}.")
            if not_authorized_ids:
                error_detail_parts.append(
                    f"Nao autorizado a deletar produtos: IDs {not_authorized_ids}."
                )
            if not deleted_produtos:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=" ".join(error_detail_parts),
                )

        if not deleted_produtos and not (not_found_ids or not_authorized_ids):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nenhum ID de produto fornecido ou lista de IDs vazia.",
            )
        return deleted_produtos
