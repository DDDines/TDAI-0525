from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class GenerationSchedulingService:
    """Encapsula validacao de acesso e agendamento das tasks de geracao IA."""

    def __init__(self, *, crud_produtos: Any, schemas: Any, models: Any) -> None:
        self._crud_produtos = crud_produtos
        self._schemas = schemas
        self._models = models

    def validate_product_access(
        self,
        *,
        db: Any,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        db_produto = self._crud_produtos.get_produto(db, produto_id=produto_id)
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
        db: Any,
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
        self._crud_produtos.update_produto(
            db,
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
