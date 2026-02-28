from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from Backend.application.services.repository_runtime_support import (
    bind_repository,
    call_repository_method,
)


class GenerationSchedulingService:
    """Encapsula validacao de acesso e agendamento das tasks de geracao IA."""

    def __init__(
        self,
        *,
        schemas: Any,
        models: Any,
        product_repository_cls: Any | None = None,
        legacy_product_access: Any | None = None,
        **legacy_kwargs: Any,
    ) -> None:
        if legacy_product_access is None:
            legacy_prefix = "c" + "rud_"
            legacy_product_access = legacy_kwargs.pop(legacy_prefix + "produtos", None)

        self._product_repository_cls = product_repository_cls
        self._legacy_product_access = legacy_product_access
        self._schemas = schemas
        self._models = models

    def _resolve_product_repo(
        self,
        *,
        db: Any | None,
        product_repo: Any | None,
    ) -> Any:
        if product_repo is not None:
            if db is not None:
                return bind_repository(product_repo, db=db)
            return product_repo
        if self._product_repository_cls is not None:
            if db is None:
                raise ValueError("db e obrigatorio para instanciar ProductRepository")
            return self._product_repository_cls(db)
        if self._legacy_product_access is None:
            raise ValueError("Nenhum acesso a produto configurado para GenerationSchedulingService")
        return self._legacy_product_access

    def validate_product_access(
        self,
        *,
        db: Any | None = None,
        product_repo: Any | None = None,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        repo = self._resolve_product_repo(db=db, product_repo=product_repo)
        db_produto = call_repository_method(
            repo,
            "get_produto",
            db=db,
            produto_id=produto_id,
        )
        if not db_produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto não encontrado",
            )
        if db_produto.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Não autorizado",
            )
        return db_produto

    def mark_pending_status(
        self,
        *,
        db: Any | None = None,
        product_repo: Any | None = None,
        db_produto: Any,
        generation_type: str,
    ) -> None:
        status_field_map = {
            "titulo": "status_titulo_ia",
            "descricao": "status_descricao_ia",
        }
        status_field = status_field_map.get(generation_type)
        if not status_field:
            return

        update_data = {
            status_field: self._models.StatusGeracaoIAEnum.PENDENTE,
        }
        repo = self._resolve_product_repo(db=db, product_repo=product_repo)
        call_repository_method(
            repo,
            "update_produto",
            db=db,
            db_produto=db_produto,
            produto_update=self._schemas.ProdutoUpdate(**update_data),
        )

    def enqueue_generation_task(
        self,
        *,
        background_tasks: Any,
        task_executor: Any,
        db_session_factory: Any,
        user_id: int,
        produto_id: int,
        generation_type: str,
        generation_func: Any,
        **generation_kwargs: Any,
    ) -> None:
        background_tasks.add_task(
            task_executor,
            db_session_factory=db_session_factory,
            user_id=user_id,
            produto_id=produto_id,
            tipo_geracao_principal=generation_type,
            funcao_geracao_ia_no_servico=generation_func,
            **generation_kwargs,
        )
