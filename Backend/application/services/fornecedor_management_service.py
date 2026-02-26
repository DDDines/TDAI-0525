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
        crud_fornecedores: Any,
        crud_historico: Any,
        sqlalchemy_func: Any,
    ) -> None:
        self._models = models
        self._schemas = schemas
        self._crud_fornecedores = crud_fornecedores
        self._crud_historico = crud_historico
        self._func = sqlalchemy_func

    @staticmethod
    def ensure_current_user_identified(*, current_user: Any) -> None:
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
        db: Any,
        fornecedor_id: int,
        detail: str = "Fornecedor nao encontrado",
    ) -> Any:
        fornecedor = self._crud_fornecedores.get_fornecedor(db, fornecedor_id=fornecedor_id)
        if not fornecedor:
            raise HTTPException(status_code=404, detail=detail)
        return fornecedor

    @staticmethod
    def ensure_user_access(*, fornecedor: Any, current_user: Any, forbidden_detail: str) -> None:
        if not current_user.is_superuser and fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=403, detail=forbidden_detail)

    def resolve_fornecedor_for_user(
        self,
        *,
        db: Any,
        fornecedor_id: int,
        current_user: Any,
        not_found_detail: str,
        forbidden_detail: str,
    ) -> Any:
        fornecedor = self.get_fornecedor_or_404(
            db=db,
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
        db: Any,
        fornecedor_id: int,
        owner_user_id: int,
        new_name: str,
    ) -> None:
        existing_fornecedor = (
            db.query(self._models.Fornecedor)
            .filter(
                self._models.Fornecedor.user_id == owner_user_id,
                self._func.lower(self._models.Fornecedor.nome) == self._func.lower(new_name),
                self._models.Fornecedor.id != fornecedor_id,
            )
            .first()
        )
        if existing_fornecedor:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Ja existe um fornecedor com o nome '{new_name}'.",
            )

    def create_fornecedor(
        self,
        *,
        db: Any,
        fornecedor: Any,
        current_user: Any,
    ) -> Any:
        self.ensure_current_user_identified(current_user=current_user)
        created = self._crud_fornecedores.create_fornecedor(
            db=db,
            fornecedor=fornecedor,
            user_id=current_user.id,
        )
        self._crud_historico.create_registro_historico(
            db,
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
        db: Any,
        current_user: Any,
        skip: int,
        limit: int,
        termo_busca: str | None,
    ) -> dict[str, Any]:
        if current_user.is_superuser:
            fornecedores_query = db.query(self._models.Fornecedor)
            if termo_busca:
                fornecedores_query = fornecedores_query.filter(
                    self._models.Fornecedor.nome.ilike(f"%{termo_busca}%")
                )
            total_items = fornecedores_query.count()
            items = (
                fornecedores_query.order_by(self._models.Fornecedor.nome)
                .offset(skip)
                .limit(limit)
                .all()
            )
        else:
            items = self._crud_fornecedores.get_fornecedores_by_user(
                db,
                user_id=current_user.id,
                skip=skip,
                limit=limit,
                search=termo_busca,
            )
            total_items = self._crud_fornecedores.count_fornecedores_by_user(
                db=db,
                user_id=current_user.id,
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
        db: Any,
        fornecedor_id: int,
        fornecedor_update: Any,
        current_user: Any,
    ) -> Any:
        fornecedor = self.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado.",
            forbidden_detail="Nao autorizado a modificar este fornecedor.",
        )
        if fornecedor_update.nome and fornecedor_update.nome != fornecedor.nome:
            self.ensure_unique_name_on_update(
                db=db,
                fornecedor_id=fornecedor_id,
                owner_user_id=fornecedor.user_id,
                new_name=fornecedor_update.nome,
            )

        updated = self._crud_fornecedores.update_fornecedor(
            db=db,
            db_fornecedor=fornecedor,
            fornecedor_update=fornecedor_update,
        )
        self._crud_historico.create_registro_historico(
            db,
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
        db: Any,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        fornecedor = self.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado",
            forbidden_detail="Nao autorizado",
        )
        return fornecedor.default_column_mapping

    def update_mapping(
        self,
        *,
        db: Any,
        fornecedor_id: int,
        current_user: Any,
        mapping: Any,
    ) -> Any:
        fornecedor = self.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado",
            forbidden_detail="Nao autorizado",
        )
        fornecedor.default_column_mapping = mapping
        db.add(fornecedor)
        db.commit()
        db.refresh(fornecedor)
        return fornecedor

    def delete_fornecedor(
        self,
        *,
        db: Any,
        fornecedor_id: int,
        current_user: Any,
    ) -> Any:
        fornecedor = self.resolve_fornecedor_for_user(
            db=db,
            fornecedor_id=fornecedor_id,
            current_user=current_user,
            not_found_detail="Fornecedor nao encontrado.",
            forbidden_detail="Nao autorizado a deletar este fornecedor.",
        )
        deleted = self._crud_fornecedores.delete_fornecedor(
            db=db,
            db_fornecedor=fornecedor,
        )
        self._crud_historico.create_registro_historico(
            db,
            self._schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="Fornecedor",
                acao=self._models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted.id,
            ),
        )
        return deleted
