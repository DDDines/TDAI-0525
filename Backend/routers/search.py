"""Camada de transporte HTTP para o dominio 'search'."""

from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.fornecedor_repository import FornecedorRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository
from Backend.infrastructure.repositories.user_repository import UserRepository

from . import auth_utils


router = APIRouter(
    prefix="/search",
    tags=["Search"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)


class SearchRequestService:
    """Servico request-scoped do router de busca global."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize injected dependencies and runtime configuration for Search Request Service."""
        self._product_repo = ProductRepository(session)
        self._fornecedor_repo = FornecedorRepository(session)
        self._product_type_repo = ProductTypeRepository(session)
        self._user_repo = UserRepository(session)

    def search_all(
        self,
        *,
        current_user: models.User,
        q: Optional[str],
        limit: int,
    ) -> schemas.SearchResults:
        """Execute search all as part of this module workflow."""
        results_items: List[Tuple] = []
        term = q.strip().lower() if q else None

        produtos = self._product_repo.search_produtos_for_index(
            query_text=term,
            limit=limit,
            user_id=current_user.id,
            is_admin=current_user.is_superuser,
        )
        for prod in produtos:
            results_items.append(
                (
                    prod.created_at,
                    schemas.SearchItem(id=prod.id, type="produto", name=prod.nome_base),
                )
            )

        fornecedores = self._fornecedor_repo.search_fornecedores_for_index(
            query_text=term,
            limit=limit,
            user_id=current_user.id,
            is_admin=current_user.is_superuser,
        )
        for forn in fornecedores:
            results_items.append(
                (
                    forn.created_at,
                    schemas.SearchItem(id=forn.id, type="fornecedor", name=forn.nome),
                )
            )

        product_types = self._product_type_repo.search_product_types_for_index(
            query_text=term,
            limit=limit,
            user_id=current_user.id,
            is_admin=current_user.is_superuser,
        )
        for product_type in product_types:
            results_items.append(
                (
                    product_type.created_at,
                    schemas.SearchItem(
                        id=product_type.id,
                        type="tipo_produto",
                        name=product_type.friendly_name,
                    ),
                )
            )

        if current_user.is_superuser:
            users = self._user_repo.search_users_by_email(query_text=term, limit=limit)
            for user in users:
                results_items.append(
                    (
                        user.created_at,
                        schemas.SearchItem(id=user.id, type="usuario", name=user.email),
                    )
                )

        sorted_items = sorted(results_items, key=lambda item: item[0], reverse=True)
        results = [item for _, item in sorted_items][:limit]
        return schemas.SearchResults(results=results)


@router.get("/", response_model=schemas.SearchResults)
def search_all(
    q: Optional[str] = Query(None, min_length=1),
    limit: int = Query(10, ge=1, le=50),
    request_service: SearchRequestService = Depends(),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
):
    """Execute search all as part of this module workflow."""
    return request_service.search_all(current_user=current_user, q=q, limit=limit)
