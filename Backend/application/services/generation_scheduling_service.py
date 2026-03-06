"""Document generation scheduling service module responsibilities and runtime integration points."""

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
        """Initialize injected dependencies and runtime configuration for Generation Scheduling Service."""
        self._product_repository = product_repository
        self._schemas = schemas
        self._models = models

    def validate_product_access(
        self,
        *,
        produto_id: int,
        current_user: Any,
    ) -> Any:
        """Execute validate product access as part of this module workflow."""
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
        """Execute mark pending status as part of this module workflow."""
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
        template_titulo: str | None = None,
        template_descricao: str | None = None,
    ) -> None:
        """Execute enqueue generation task as part of this module workflow."""
        task_payload = {
            "user_id": user_id,
            "produto_id": produto_id,
            "tipo_geracao_principal": generation_type,
            "funcao_geracao_ia_no_servico": generation_func,
            "num_titulos": num_titulos,
            "tamanho_palavras": tamanho_palavras,
        }
        if template_titulo is not None:
            task_payload["template_titulo"] = template_titulo
        if template_descricao is not None:
            task_payload["template_descricao"] = template_descricao

        background_tasks.add_task(
            task_executor,
            **task_payload,
        )
