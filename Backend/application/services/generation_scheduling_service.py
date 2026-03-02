"""Module generation scheduling service.

This module contains backend application/runtime logic and is fully
documented for maintainability and onboarding.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class GenerationSchedulingService:
    """Encapsula validacao de acesso e agendamento das tasks de geracao IA."""

    def __init__(
        self,
        *,
        schemas: Any,
        models: Any,
        product_repository: Any,
    ) -> None:
        """Execute __init__.

        This callable is documented to make behavior explicit for readers.
        """
        self._product_repository = product_repository
        self._schemas = schemas
        self._models = models

    def validate_product_access(
        self,
        *,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        """Execute validate_product_access.

        This callable is documented to make behavior explicit for readers.
        """
        db_produto = self._product_repository.get_produto(produto_id=produto_id)
        if not db_produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado",
            )
        if db_produto.user_id != current_user.id and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado",
            )
        return db_produto

    def mark_pending_status(
        self,
        *,
        db_produto: Any,
        generation_type: str,
    ) -> None:
        """Execute mark_pending_status.

        This callable is documented to make behavior explicit for readers.
        """
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
        self._product_repository.update_produto(
            db_produto=db_produto,
            produto_update=self._schemas.ProdutoUpdate(**update_data),
        )

    def enqueue_generation_task(
        self,
        *,
        background_tasks: Any,
        task_executor: Any,
        user_id: int,
        produto_id: int,
        generation_type: str,
        generation_func: Any,
        num_titulos: int | None = None,
        tamanho_palavras: int | None = None,
    ) -> None:
        """Execute enqueue_generation_task.

        This callable is documented to make behavior explicit for readers.
        """
        background_tasks.add_task(
            task_executor,
            user_id=user_id,
            produto_id=produto_id,
            tipo_geracao_principal=generation_type,
            funcao_geracao_ia_no_servico=generation_func,
            num_titulos=num_titulos,
            tamanho_palavras=tamanho_palavras,
        )
