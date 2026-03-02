"""Camada de transporte HTTP para o dominio 'product_types'."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Path as FastAPIPath, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_type_repository import ProductTypeRepository

from . import auth_utils


router = APIRouter(
    prefix="/product-types",
    tags=["Tipos de Produto e Templates de Atributos"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
)
logger = get_logger(__name__)


class ReorderRequest(BaseModel):
    """Payload para mover atributos para cima/baixo na ordem de exibicao."""

    direction: str


class ProductTypesRequestService:
    """Servico request-scoped do router de tipos de produto."""

    def __init__(
        self,
        session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
    ) -> None:
        """Initialize collaborators and configuration required by this component."""
        self._session = session
        self._product_type_repo = ProductTypeRepository(session)
        self._historico_repo = HistoricoRepository(session)

    def create_product_type(
        self,
        *,
        product_type_in: schemas.ProductTypeCreate,
        current_user: models.User,
    ) -> models.ProductType:
        """Create product type for this workflow."""
        user_id_for_type = None if current_user.is_superuser else current_user.id
        logger.info(
            "ROUTER (create_product_type): requisicao recebida do usuario ID %s para alvo %s",
            current_user.id,
            user_id_for_type,
        )
        existing_type = self._product_type_repo.get_product_type_by_key_name(
            key_name=product_type_in.key_name,
            user_id=user_id_for_type,
        )
        if user_id_for_type is None and (not existing_type):
            existing_type = self._product_type_repo.get_product_type_by_key_name(
                key_name=product_type_in.key_name,
                user_id=None,
            )
        if existing_type:
            scope_msg = (
                "globalmente"
                if existing_type.user_id is None
                else f"para o usuario ID {existing_type.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Um tipo de produto com a chave '{product_type_in.key_name}' "
                    f"ja existe {scope_msg}."
                ),
            )

        created = self._product_type_repo.create_product_type(
            product_type_create=product_type_in,
            user_id=user_id_for_type,
        )
        self._historico_repo.create_registro_historico(
            registro_in=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=created.id,
            )
        )
        return created

    def read_product_types(
        self,
        *,
        current_user: models.User,
        skip: int = 0,
        limit: int = 100,
    ) -> List[models.ProductType]:
        """Run read product types in this workflow."""
        logger.info(
            "ROUTER (read_product_types): iniciando busca para usuario ID %s",
            current_user.id,
        )
        product_types = self._product_type_repo.get_product_types_for_user(
            skip=skip,
            limit=limit,
            user_id=current_user.id,
        )
        logger.info(
            "ROUTER (read_product_types): Encontrados %s tipos de produto.",
            len(product_types),
        )
        return product_types

    async def read_product_type_details(
        self,
        *,
        identifier: str,
        current_user: models.User,
    ) -> models.ProductType:
        """Run read product type details in this workflow."""
        logger.info(
            "ROUTER (read_product_type_details): iniciando busca por '%s'",
            identifier,
        )
        db_product_type = None
        try:
            numeric_id = int(identifier)
            db_product_type = self._product_type_repo.get_product_type(product_type_id=numeric_id)
        except ValueError:
            pass

        if not db_product_type:
            db_product_type = self._product_type_repo.get_product_type_by_key_name(
                key_name=str(identifier),
                user_id=current_user.id,
            )
            if not db_product_type:
                db_product_type = self._product_type_repo.get_product_type_by_key_name(
                    key_name=str(identifier),
                    user_id=None,
                )

        if db_product_type is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Tipo de Produto com identificador '{identifier}' nao encontrado.",
            )

        is_global = db_product_type.user_id is None
        is_owner = db_product_type.user_id == current_user.id
        if not (current_user.is_superuser or is_global or is_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a visualizar este tipo de produto.",
            )
        return db_product_type

    def update_product_type(
        self,
        *,
        type_id: int,
        product_type_in: schemas.ProductTypeUpdate,
        current_user: models.User,
    ) -> models.ProductType:
        """Update product type for this workflow."""
        db_product_type = self._product_type_repo.get_product_type(product_type_id=type_id)
        if not db_product_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de produto nao encontrado.",
            )
        updated_type = self._product_type_repo.update_product_type(
            db_product_type=db_product_type,
            product_type_update=product_type_in,
        )
        self._historico_repo.create_registro_historico(
            registro_in=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.ATUALIZACAO,
                entity_id=updated_type.id,
            )
        )
        return updated_type

    def delete_product_type(
        self,
        *,
        type_id: int,
        current_user: models.User,
    ) -> models.ProductType:
        """Delete product type for this workflow."""
        db_product_type = self._product_type_repo.get_product_type(product_type_id=type_id)
        if not db_product_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de Produto nao encontrado para delecao.",
            )
        deleted_type = self._product_type_repo.delete_product_type(db_product_type=db_product_type)
        self._historico_repo.create_registro_historico(
            registro_in=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted_type.id,
            )
        )
        return deleted_type

    def add_attribute_to_product_type(
        self,
        *,
        type_id: int,
        attribute_in: schemas.AttributeTemplateCreate,
    ) -> models.AttributeTemplate:
        """Run add attribute to product type in this workflow."""
        existing_attr_template = (
            self._session.query(models.AttributeTemplate)
            .filter(
                models.AttributeTemplate.product_type_id == type_id,
                models.AttributeTemplate.attribute_key == attribute_in.attribute_key,
            )
            .first()
        )
        if existing_attr_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Um atributo com a chave '{attribute_in.attribute_key}' "
                    "ja existe para este tipo de produto."
                ),
            )
        return self._product_type_repo.create_attribute_template(
            attr_template_create=attribute_in,
            product_type_id=type_id,
        )

    def update_attribute_for_product_type(
        self,
        *,
        type_id: int,
        attribute_id: int,
        attribute_in: schemas.AttributeTemplateUpdate,
    ) -> models.AttributeTemplate:
        """Update attribute for product type for this workflow."""
        db_attribute_to_check = self._product_type_repo.get_attribute_template(
            attribute_template_id=attribute_id
        )
        if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Atributo nao encontrado ou nao pertence ao tipo de produto "
                    "especificado."
                ),
            )

        if attribute_in.attribute_key and attribute_in.attribute_key != db_attribute_to_check.attribute_key:
            existing_attr_with_new_key = (
                self._session.query(models.AttributeTemplate)
                .filter(
                    models.AttributeTemplate.product_type_id == type_id,
                    models.AttributeTemplate.attribute_key == attribute_in.attribute_key,
                    models.AttributeTemplate.id != attribute_id,
                )
                .first()
            )
            if existing_attr_with_new_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Um atributo com a nova chave '{attribute_in.attribute_key}' "
                        "ja existe para este tipo de produto."
                    ),
                )

        updated_attribute = self._product_type_repo.update_attribute_template(
            db_attr_template=db_attribute_to_check,
            attr_template_update=attribute_in,
        )
        if not updated_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao atualizar o atributo.",
            )
        return updated_attribute

    def remove_attribute_from_product_type(
        self,
        *,
        type_id: int,
        attribute_id: int,
    ) -> models.AttributeTemplate:
        """Run remove attribute from product type in this workflow."""
        db_attribute_to_check = self._product_type_repo.get_attribute_template(
            attribute_template_id=attribute_id
        )
        if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Atributo nao encontrado ou nao pertence ao tipo de produto "
                    "especificado para delecao."
                ),
            )
        deleted_attribute = self._product_type_repo.delete_attribute_template(
            db_attr_template=db_attribute_to_check
        )
        if not deleted_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Falha ao deletar o atributo.",
            )
        return deleted_attribute

    def reorder_attribute(
        self,
        *,
        type_id: int,
        attribute_id: int,
        reorder_request: ReorderRequest,
        current_user: models.User,
    ) -> models.AttributeTemplate:
        """Run reorder attribute in this workflow."""
        product_type = self._product_type_repo.get_product_type(product_type_id=type_id)
        if not product_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de produto nao encontrado.",
            )
        is_owner = product_type.user_id == current_user.id
        if not current_user.is_superuser and (not is_owner):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a modificar este tipo de produto.",
            )
        reordered_attribute = self._product_type_repo.reorder_attribute_template(
            attribute_id=attribute_id,
            direction=reorder_request.direction,
        )
        if not reordered_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atributo nao encontrado ou movimento invalido.",
            )
        return reordered_attribute


@router.post("/", response_model=schemas.ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type_endpoint(
    product_type_in: schemas.ProductTypeCreate,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Create product type endpoint for this workflow."""
    return request_service.create_product_type(product_type_in=product_type_in, current_user=current_user)


@router.get("/", response_model=List[schemas.ProductTypeResponse])
def read_product_types_endpoint(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Run read product types endpoint in this workflow."""
    return request_service.read_product_types(current_user=current_user, skip=skip, limit=limit)


@router.get(
    "/{type_id_or_key_path:path}",
    response_model=schemas.ProductTypeResponse,
    name="read_product_type_details",
)
async def read_product_type_details_route(
    type_id_or_key_path: str = FastAPIPath(
        ...,
        description="ID (numerico) ou key_name (string) do tipo de produto",
    ),
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Run read product type details route in this workflow."""
    return await request_service.read_product_type_details(
        identifier=type_id_or_key_path,
        current_user=current_user,
    )


@router.put("/{type_id}", response_model=schemas.ProductTypeResponse)
def update_product_type_endpoint(
    type_id: int,
    product_type_in: schemas.ProductTypeUpdate,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Update product type endpoint for this workflow."""
    return request_service.update_product_type(
        type_id=type_id,
        product_type_in=product_type_in,
        current_user=current_user,
    )


@router.delete("/{type_id}", response_model=schemas.ProductTypeResponse)
def delete_product_type_endpoint(
    type_id: int,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Delete product type endpoint for this workflow."""
    return request_service.delete_product_type(type_id=type_id, current_user=current_user)


@router.post(
    "/{type_id}/attributes/",
    response_model=schemas.AttributeTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_attribute_to_product_type_endpoint(
    type_id: int,
    attribute_in: schemas.AttributeTemplateCreate,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Run add attribute to product type endpoint in this workflow."""
    _ = current_user
    return request_service.add_attribute_to_product_type(type_id=type_id, attribute_in=attribute_in)


@router.put("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def update_attribute_for_product_type_endpoint(
    type_id: int,
    attribute_id: int,
    attribute_in: schemas.AttributeTemplateUpdate,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Update attribute for product type endpoint for this workflow."""
    _ = current_user
    return request_service.update_attribute_for_product_type(
        type_id=type_id,
        attribute_id=attribute_id,
        attribute_in=attribute_in,
    )


@router.delete("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def remove_attribute_from_product_type_endpoint(
    type_id: int,
    attribute_id: int,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Run remove attribute from product type endpoint in this workflow."""
    _ = current_user
    return request_service.remove_attribute_from_product_type(type_id=type_id, attribute_id=attribute_id)


@router.post(
    "/{type_id}/attributes/{attribute_id}/reorder",
    response_model=schemas.AttributeTemplateResponse,
)
def reorder_attribute_endpoint(
    type_id: int,
    attribute_id: int,
    reorder_request: ReorderRequest,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    request_service: ProductTypesRequestService = Depends(),
):
    """Run reorder attribute endpoint in this workflow."""
    return request_service.reorder_attribute(
        type_id=type_id,
        attribute_id=attribute_id,
        reorder_request=reorder_request,
        current_user=current_user,
    )
