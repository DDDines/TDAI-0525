# Backend/routers/product_types.py
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Path as FastAPIPath, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from Backend import crud_historico
from Backend import crud_product_types
from Backend import database
from Backend import models
from Backend import schemas
from Backend.core.deprecation import deprecated_legacy_service_proxy
from Backend.core.logging_config import get_logger

from . import auth_utils

router = APIRouter(
    prefix="/product-types",
    tags=["Tipos de Produto e Templates de Atributos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = get_logger(__name__)


class ReorderRequest(BaseModel):
    direction: str


class _ProductTypesRouterWorkflow:
    def __init__(self, runtime: Optional["_ProductTypesRouterRuntime"] = None) -> None:
        self._runtime = runtime or _ProductTypesRouterRuntime()

    def create_product_type(
        self,
        product_type_in: schemas.ProductTypeCreate,
        db: Session,
        current_user: models.User,
    ) -> models.ProductType:
        user_id_for_type = None if current_user.is_superuser else current_user.id
        logger.info(
            "ROUTER (create_product_type): requisicao recebida do usuario ID %s para alvo %s",
            current_user.id,
            user_id_for_type,
        )

        existing_type = self._runtime.get_product_type_by_key_name(
            db=db,
            key_name=product_type_in.key_name,
            user_id=user_id_for_type,
        )

        if user_id_for_type is None and not existing_type:
            existing_type = self._runtime.get_product_type_by_key_name(
                db=db,
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

        created = self._runtime.create_product_type(
            db=db,
            product_type_create=product_type_in,
            user_id=user_id_for_type,
        )
        self._runtime.create_registro_historico(
            db=db,
            payload=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=created.id,
            ),
        )
        return created

    def read_product_types(
        self,
        db: Session,
        current_user: models.User,
        skip: int = 0,
        limit: int = 100,
    ) -> List[models.ProductType]:
        logger.info(
            "ROUTER (read_product_types): iniciando busca para usuario ID %s",
            current_user.id,
        )
        product_types = self._runtime.get_product_types_for_user(
            db=db,
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
        identifier: str,
        db: Session,
        current_user: models.User,
    ) -> models.ProductType:
        logger.info("ROUTER (read_product_type_details): iniciando busca por '%s'", identifier)
        db_product_type = None

        try:
            numeric_id = int(identifier)
            db_product_type = self._runtime.get_product_type(
                db=db,
                product_type_id=numeric_id,
            )
        except ValueError:
            pass

        if not db_product_type:
            db_product_type = self._runtime.get_product_type_by_key_name(
                db=db,
                key_name=str(identifier),
                user_id=current_user.id,
            )

            if not db_product_type:
                db_product_type = self._runtime.get_product_type_by_key_name(
                    db=db,
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
        type_id: int,
        product_type_in: schemas.ProductTypeUpdate,
        db: Session,
        current_user: models.User,
    ) -> models.ProductType:
        db_product_type = self._runtime.get_product_type(db=db, product_type_id=type_id)
        if not db_product_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de produto nao encontrado.")

        updated_type = self._runtime.update_product_type(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_in,
        )
        self._runtime.create_registro_historico(
            db=db,
            payload=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.ATUALIZACAO,
                entity_id=updated_type.id,
            ),
        )
        return updated_type

    def delete_product_type(
        self,
        type_id: int,
        db: Session,
        current_user: models.User,
    ) -> models.ProductType:
        db_product_type = self._runtime.get_product_type(db=db, product_type_id=type_id)
        if not db_product_type:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tipo de Produto nao encontrado para delecao.",
            )

        deleted_type = self._runtime.delete_product_type(db=db, db_product_type=db_product_type)
        self._runtime.create_registro_historico(
            db=db,
            payload=schemas.RegistroHistoricoCreate(
                user_id=current_user.id,
                entidade="ProductType",
                acao=models.TipoAcaoSistemaEnum.DELECAO,
                entity_id=deleted_type.id,
            ),
        )
        return deleted_type

    def add_attribute_to_product_type(
        self,
        type_id: int,
        attribute_in: schemas.AttributeTemplateCreate,
        db: Session,
    ) -> models.AttributeTemplate:
        existing_attr_template = self._runtime.find_attribute_template_by_key(
            db=db,
            type_id=type_id,
            attribute_key=attribute_in.attribute_key,
        )
        if existing_attr_template:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Um atributo com a chave '{attribute_in.attribute_key}' "
                    "ja existe para este tipo de produto."
                ),
            )

        return self._runtime.create_attribute_template(
            db=db,
            attr_template_create=attribute_in,
            product_type_id=type_id,
        )

    def update_attribute_for_product_type(
        self,
        type_id: int,
        attribute_id: int,
        attribute_in: schemas.AttributeTemplateUpdate,
        db: Session,
    ) -> models.AttributeTemplate:
        db_attribute_to_check = self._runtime.get_attribute_template(
            db=db,
            attribute_id=attribute_id,
        )
        if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atributo nao encontrado ou nao pertence ao tipo de produto especificado.",
            )

        if attribute_in.attribute_key and attribute_in.attribute_key != db_attribute_to_check.attribute_key:
            existing_attr_with_new_key = self._runtime.find_attribute_template_by_key(
                db=db,
                type_id=type_id,
                attribute_key=attribute_in.attribute_key,
                exclude_id=attribute_id,
            )
            if existing_attr_with_new_key:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Um atributo com a nova chave '{attribute_in.attribute_key}' "
                        "ja existe para este tipo de produto."
                    ),
                )

        updated_attribute = self._runtime.update_attribute_template(
            db=db,
            db_attr_template=db_attribute_to_check,
            attr_template_update=attribute_in,
        )
        if not updated_attribute:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao atualizar o atributo.")
        return updated_attribute

    def remove_attribute_from_product_type(
        self,
        type_id: int,
        attribute_id: int,
        db: Session,
    ) -> models.AttributeTemplate:
        db_attribute_to_check = self._runtime.get_attribute_template(
            db=db,
            attribute_id=attribute_id,
        )
        if not db_attribute_to_check or db_attribute_to_check.product_type_id != type_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Atributo nao encontrado ou nao pertence ao tipo de produto "
                    "especificado para delecao."
                ),
            )

        deleted_attribute = self._runtime.delete_attribute_template(
            db=db,
            db_attr_template=db_attribute_to_check,
        )
        if not deleted_attribute:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Falha ao deletar o atributo.")
        return deleted_attribute

    def reorder_attribute(
        self,
        type_id: int,
        attribute_id: int,
        reorder_request: ReorderRequest,
        db: Session,
        current_user: models.User,
    ) -> models.AttributeTemplate:
        product_type = self._runtime.get_product_type(db=db, product_type_id=type_id)
        if not product_type:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tipo de produto nao encontrado.")

        is_owner = product_type.user_id == current_user.id
        if not current_user.is_superuser and not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a modificar este tipo de produto.",
            )

        reordered_attribute = self._runtime.reorder_attribute_template(
            db=db,
            attribute_id=attribute_id,
            direction=reorder_request.direction,
        )

        if not reordered_attribute:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Atributo nao encontrado ou movimento invalido.",
            )

        return reordered_attribute


class _ProductTypesRouterRuntime:
    """Runtime OO com operações de CRUD/histórico do router de tipos."""

    def get_product_type_by_key_name(self, *, db: Session, key_name: str, user_id: Optional[int]):
        return crud_product_types.get_product_type_by_key_name(
            db,
            key_name=key_name,
            user_id=user_id,
        )

    def create_product_type(self, *, db: Session, product_type_create, user_id: Optional[int]):
        return crud_product_types.create_product_type(
            db=db,
            product_type_create=product_type_create,
            user_id=user_id,
        )

    def create_registro_historico(self, *, db: Session, payload):
        return crud_historico.create_registro_historico(db, payload)

    def get_product_types_for_user(self, *, db: Session, skip: int, limit: int, user_id: int):
        return crud_product_types.get_product_types_for_user(
            db,
            skip=skip,
            limit=limit,
            user_id=user_id,
        )

    def get_product_type(self, *, db: Session, product_type_id: int):
        return crud_product_types.get_product_type(db, product_type_id=product_type_id)

    def update_product_type(self, *, db: Session, db_product_type, product_type_update):
        return crud_product_types.update_product_type(
            db=db,
            db_product_type=db_product_type,
            product_type_update=product_type_update,
        )

    def delete_product_type(self, *, db: Session, db_product_type):
        return crud_product_types.delete_product_type(db=db, db_product_type=db_product_type)

    def find_attribute_template_by_key(
        self,
        *,
        db: Session,
        type_id: int,
        attribute_key: str,
        exclude_id: Optional[int] = None,
    ):
        query = db.query(models.AttributeTemplate).filter(
            models.AttributeTemplate.product_type_id == type_id,
            models.AttributeTemplate.attribute_key == attribute_key,
        )
        if exclude_id is not None:
            query = query.filter(models.AttributeTemplate.id != exclude_id)
        return query.first()

    def create_attribute_template(self, *, db: Session, attr_template_create, product_type_id: int):
        return crud_product_types.create_attribute_template(
            db=db,
            attr_template_create=attr_template_create,
            product_type_id=product_type_id,
        )

    def get_attribute_template(self, *, db: Session, attribute_id: int):
        return crud_product_types.get_attribute_template(db, attribute_id)

    def update_attribute_template(self, *, db: Session, db_attr_template, attr_template_update):
        return crud_product_types.update_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
            attr_template_update=attr_template_update,
        )

    def delete_attribute_template(self, *, db: Session, db_attr_template):
        return crud_product_types.delete_attribute_template(
            db=db,
            db_attr_template=db_attr_template,
        )

    def reorder_attribute_template(self, *, db: Session, attribute_id: int, direction: str):
        return crud_product_types.reorder_attribute_template(
            db,
            attribute_id=attribute_id,
            direction=direction,
        )


product_types_router_runtime = _ProductTypesRouterRuntime()
product_types_router_workflow = _ProductTypesRouterWorkflow(runtime=product_types_router_runtime)


@router.post("/", response_model=schemas.ProductTypeResponse, status_code=status.HTTP_201_CREATED)
def create_product_type_endpoint(
    product_type_in: schemas.ProductTypeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return product_types_router_workflow.create_product_type(
        product_type_in=product_type_in,
        db=db,
        current_user=current_user,
    )


@router.get("/", response_model=List[schemas.ProductTypeResponse])
def read_product_types_endpoint(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return product_types_router_workflow.read_product_types(
        db=db,
        current_user=current_user,
        skip=skip,
        limit=limit,
    )


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
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return await product_types_router_workflow.read_product_type_details(
        identifier=type_id_or_key_path,
        db=db,
        current_user=current_user,
    )


@router.put("/{type_id}", response_model=schemas.ProductTypeResponse)
def update_product_type_endpoint(
    type_id: int,
    product_type_in: schemas.ProductTypeUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return product_types_router_workflow.update_product_type(
        type_id=type_id,
        product_type_in=product_type_in,
        db=db,
        current_user=current_user,
    )


@router.delete("/{type_id}", response_model=schemas.ProductTypeResponse)
def delete_product_type_endpoint(
    type_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return product_types_router_workflow.delete_product_type(
        type_id=type_id,
        db=db,
        current_user=current_user,
    )


@router.post(
    "/{type_id}/attributes/",
    response_model=schemas.AttributeTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_attribute_to_product_type_endpoint(
    type_id: int,
    attribute_in: schemas.AttributeTemplateCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    _ = current_user
    return product_types_router_workflow.add_attribute_to_product_type(
        type_id=type_id,
        attribute_in=attribute_in,
        db=db,
    )


@router.put("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def update_attribute_for_product_type_endpoint(
    type_id: int,
    attribute_id: int,
    attribute_in: schemas.AttributeTemplateUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    _ = current_user
    return product_types_router_workflow.update_attribute_for_product_type(
        type_id=type_id,
        attribute_id=attribute_id,
        attribute_in=attribute_in,
        db=db,
    )


@router.delete("/{type_id}/attributes/{attribute_id}", response_model=schemas.AttributeTemplateResponse)
def remove_attribute_from_product_type_endpoint(
    type_id: int,
    attribute_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    _ = current_user
    return product_types_router_workflow.remove_attribute_from_product_type(
        type_id=type_id,
        attribute_id=attribute_id,
        db=db,
    )


@router.post("/{type_id}/attributes/{attribute_id}/reorder", response_model=schemas.AttributeTemplateResponse)
def reorder_attribute_endpoint(
    type_id: int,
    attribute_id: int,
    reorder_request: ReorderRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    return product_types_router_workflow.reorder_attribute(
        type_id=type_id,
        attribute_id=attribute_id,
        reorder_request=reorder_request,
        db=db,
        current_user=current_user,
    )


class ProductTypesRouterLegacyService:
    def create_product_type(self, *args, **kwargs):
        return product_types_router_workflow.create_product_type(*args, **kwargs)

    def read_product_types(self, *args, **kwargs):
        return product_types_router_workflow.read_product_types(*args, **kwargs)

    async def read_product_type_details(self, *args, **kwargs):
        return await product_types_router_workflow.read_product_type_details(*args, **kwargs)

    def update_product_type(self, *args, **kwargs):
        return product_types_router_workflow.update_product_type(*args, **kwargs)

    def delete_product_type(self, *args, **kwargs):
        return product_types_router_workflow.delete_product_type(*args, **kwargs)

    def add_attribute_to_product_type(self, *args, **kwargs):
        return product_types_router_workflow.add_attribute_to_product_type(*args, **kwargs)

    def update_attribute_for_product_type(self, *args, **kwargs):
        return product_types_router_workflow.update_attribute_for_product_type(*args, **kwargs)

    def remove_attribute_from_product_type(self, *args, **kwargs):
        return product_types_router_workflow.remove_attribute_from_product_type(*args, **kwargs)

    def reorder_attribute(self, *args, **kwargs):
        return product_types_router_workflow.reorder_attribute(*args, **kwargs)


product_types_router_legacy_service = deprecated_legacy_service_proxy(
    ProductTypesRouterLegacyService(),
    qualified_name="Backend.routers.product_types.product_types_router_legacy_service",
)
