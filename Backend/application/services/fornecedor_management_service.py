"""Fornecedor management service.

Defines the module responsibilities and how it fits in the backend architecture.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class FornecedorManagementService:
    """Centraliza regras de acesso e operacoes CRUD de fornecedores."""

    def __init__(
        self,
        *,
        models: Any,
        schemas: Any,
        fornecedor_repo: Any,
        historico_repo: Any,
    ) -> None:
        """Initialize required dependencies and runtime configuration."""
        self._models = models
        self._schemas = schemas
        self._fornecedor_repo = fornecedor_repo
        self._historico_repo = historico_repo

    @staticmethod
    def ensure_current_user_identified(*, current_user: Any) -> None:
        """Ensure current user identified."""
        if current_user is None or getattr(current_user, "id", None) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Nao foi possivel identificar o usuario logado para criar o fornecedor. "
                    "Por favor, tente fazer login novamente."
                ),
            )

    def get_fornecedor_or_404(
        self,
        *,
        fornecedor_id: int,
        detail: str = "Fornecedor nao encontrado",
    ) -> Any:
        """Return Fornecedor or 404."""
        fornecedor = self._fornecedor_repo.get_fornecedor(fornecedor_id=fornecedor_id)
        if not fornecedor:
            raise HTTPException(status_code=404, detail=detail)
        return fornecedor

    @staticmethod
    def ensure_user_access(*, fornecedor: Any, current_user: Any, forbidden_detail: str) -> None:
        """Ensure user access."""
        if not current_user.is_superuser and fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=forbidden_detail)

    def resolve_fornecedor_for_user(
        self,
        *,
        fornecedor_id: int,
        current_user: Any,
        not_found_detail: str,
        forbidden_detail: str,
    ) -> Any:
        """Resolve fornecedor for user."""
        fornecedor = self.get_fornecedor_or_404(
            fornecedor_id=fornecedor_id,
            detail=not_found_detail,
        )
        self.ensure_user_access(
            fornecedor=fornecedor,
            current_user=current_user,
            forbidden_detail=forbidden_detail,
        )
        return fornecedor

    def ensure_unique_name_on_update(
        self,
        *,
        fornecedor_id: int,
        owner_user_id: int,
        new_name: str,
    ) -> None:
        """Ensure unique name on update."""
        already_exists = self._fornecedor_repo.exists_fornecedor_with_name_for_user(
            user_id=owner_user_id,
            nome=new_name,
            exclude_id=fornecedor_id,
        )
        if already_exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ja existe um fornecedor com o nome '{new_name}'.",
            )

    def create_fornecedor(
        self,
        *,
        fornecedor: Any,
        current_user: Any,
    ) -> Any:
        """Create fornecedor."""
        self.ensure_current_user_identified(current_user=current_user)
        created = self._fornecedor_repo.create_fornecedor(
            fornecedor=fornecedor,
            user_id=current_user.id,
        )
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=self._models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=created.id,
            ),
        )
        return created

    def list_fornecedores_page(
        self,
        *,
        current_user: Any,
        skip: int,
        limit: int,
        termo_busca: str | None,
    ) -> dict[str, Any]:
        """List fornecedores page."""
        items = self._fornecedor_repo.get_fornecedores_by_user(
            user_id=current_user.id,
            is_admin=current_user.is_superuser,
            skip=skip,
            limit=limit,
            search=termo_busca,
        )
        total_items = self._fornecedor_repo.count_fornecedores_by_user(
            user_id=current_user.id,
            is_admin=current_user.is_superuser,
            search=termo_busca,
        )

        return {
            "items": items,
            "total_items": total_items,
            "page": skip // limit + 1,
            "limit": limit,
        }

    def update_fornecedor(
        self,
        *,
        fornecedor_id: int,
        fornecedor_update: Any,
        current_user: Any,
    ) -> Any:
        """Update fornecedor."""
        fornecedor = self.resolve_fornecedor_for_user(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado.",
            forbidden_detail="Nao autorizado a modificar este fornecedor.",
        )
        if fornecedor_update.nome and fornecedor_update.nome != fornecedor.nome:
            self.ensure_unique_name_on_update(
                fornecedor_id=fornecedor_id,
                owner_user_id=fornecedor.user_id,
                new_name=fornecedor_update.nome,
            )

        updated = self._fornecedor_repo.update_fornecedor(
            db_fornecedor=fornecedor,
            fornecedor_update=fornecedor_update,
        )
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=self._models.TipoAcaoSistemaEnum.ATUALIZACAO,
                entity_id=updated.id,
            ),
        )
        return updated

    def get_mapping(
        self,
        *,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        """Return Mapping."""
        fornecedor = self.resolve_fornecedor_for_user(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado",
            forbidden_detail="Nao autorizado",
        )
        return fornecedor.default_column_mapping

    def update_mapping(
        self,
        *,
        fornecedor_id: int,
        current_user: Any,
        mapping: Any,
    ) -> Any:
        """Update mapping."""
        fornecedor = self.resolve_fornecedor_for_user(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado",
            forbidden_detail="Nao autorizado",
        )
        return self._fornecedor_repo.set_default_column_mapping(
            db_fornecedor=fornecedor,
            mapping=mapping,
        )

    def delete_fornecedor(
        self,
        *,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        """Delete fornecedor."""
        fornecedor = self.resolve_fornecedor_for_user(
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado.",
            forbidden_detail="Nao autorizado a deletar este fornecedor.",
        )
        deleted = self._fornecedor_repo.delete_fornecedor(
            db_fornecedor=fornecedor,
        )
        self._historico_repo.create_registro_historico(
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=self._models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted.id,
            ),
        )
        return deleted
