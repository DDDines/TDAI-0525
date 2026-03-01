"""Camada de transporte HTTP para o dominio 'uso_ia'."""
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.service_container import (
    build_request_scoped_dependency,
)
from Backend.core.logging_config import get_logger
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from . import auth_utils

router = APIRouter(
    prefix="/uso-ia",
    tags=["uso-ia"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

logger = get_logger(__name__)


class _UsoIAWorkflow:
    """Workflow/escopo request-scoped para o fluxo de 'uso_ia'."""
    def __init__(self, runtime: Optional["_UsoIARuntime"] = None) -> None:
        self._runtime = runtime or _UsoIARuntime()

    def create_uso_ia(
        self,
        db: Session,
        current_user: models.User,
        uso_ia_data: schemas.RegistroUsoIACreate,
    ) -> schemas.RegistroUsoIAResponse:
        try:
            uso_ia_data.user_id = current_user.id
            return self._runtime.create_registro_uso_ia(db=db, registro_uso=uso_ia_data)
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("ERRO INESPERADO ao criar registro de uso de IA: %s", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro interno ao registrar uso de IA.",
            ) from exc

    def list_usos_ia_usuario(
        self,
        db: Session,
        current_user: models.User,
        skip: int,
        limit: int,
        tipo_geracao: Optional[str],
        data_inicio: Optional[datetime],
        data_fim: Optional[datetime],
    ) -> schemas.UsoIAPage:
        try:
            tipo_enum = models.TipoAcaoEnum(tipo_geracao) if tipo_geracao else None
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="tipo_geracao invalido",
            ) from exc

        registros = self._runtime.get_registros_uso_ia(
            db=db,
            user_id=current_user.id,
            skip=skip,
            limit=limit,
            tipo_acao=tipo_enum,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        total_items = self._runtime.count_registros_uso_ia(
            db=db,
            user_id=current_user.id,
            tipo_acao=tipo_enum,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )
        page_number = skip // limit + 1
        return schemas.UsoIAPage(
            items=registros,
            total_items=total_items,
            page=page_number,
            limit=limit,
        )

    def read_uso_ia_especifico(
        self,
        db: Session,
        current_user: models.User,
        registro_id: int,
    ) -> schemas.RegistroUsoIAResponse:
        db_registro = self._runtime.get_registro_uso_ia_by_id(
            db=db,
            registro_id=registro_id,
        )
        if db_registro is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro de uso de IA nao encontrado.",
            )
        if not current_user.is_superuser and db_registro.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a visualizar este registro.",
            )
        return db_registro

    def read_usos_ia_por_produto(
        self,
        db: Session,
        current_user: models.User,
        produto_id: int,
        skip: int,
        limit: int,
    ) -> List[schemas.RegistroUsoIAResponse]:
        produto = self._runtime.get_produto(db=db, produto_id=produto_id)
        if not produto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Produto nao encontrado",
            )
        if not current_user.is_superuser and produto.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Nao autorizado a ver usos de IA para este produto",
            )

        query_user_id = produto.user_id if current_user.is_superuser else current_user.id
        return self._runtime.get_usos_ia_by_produto(
            db=db,
            produto_id=produto_id,
            user_id=query_user_id,
            skip=skip,
            limit=limit,
        )


class _UsoIARuntime:
    """Runtime OO para integraÃ§Ãµes do router de uso de IA."""

    def create_registro_uso_ia(self, *, db: Session, registro_uso):
        return RegistroUsoIARepository(db).create_registro_uso_ia(
            registro_uso=registro_uso,
        )

    def get_registros_uso_ia(self, *, db: Session, **kwargs):
        return RegistroUsoIARepository(db).get_registros_uso_ia(**kwargs)

    def count_registros_uso_ia(self, *, db: Session, **kwargs):
        return RegistroUsoIARepository(db).count_registros_uso_ia(**kwargs)

    def get_registro_uso_ia_by_id(self, *, db: Session, registro_id: int):
        return (
            db.query(models.RegistroUsoIA)
            .filter(models.RegistroUsoIA.id == registro_id)
            .first()
        )

    def get_produto(self, *, db: Session, produto_id: int):
        return ProductRepository(db).get_produto(produto_id=produto_id)

    def get_usos_ia_by_produto(self, *, db: Session, **kwargs):
        return RegistroUsoIARepository(db).get_usos_ia_by_produto(**kwargs)


UsoIAWorkflow = _UsoIAWorkflow


def get_uso_ia_workflow() -> UsoIAWorkflow:
    """Factory de workflow OO para o modulo atual (get_uso_ia_workflow)."""
    return UsoIAWorkflow(runtime=_UsoIARuntime())


class _UsoIARequestScope:
    """Workflow/escopo request-scoped para o fluxo de 'uso_ia'."""
    def __init__(self, db: Session, workflow: UsoIAWorkflow | None = None) -> None:
        self._db = db
        self._workflow = workflow or get_uso_ia_workflow()

    def create_uso_ia(
        self,
        *,
        current_user: models.User,
        uso_ia_data: schemas.RegistroUsoIACreate,
    ) -> schemas.RegistroUsoIAResponse:
        return self._workflow.create_uso_ia(
            db=self._db,
            current_user=current_user,
            uso_ia_data=uso_ia_data,
        )

    def list_usos_ia_usuario(
        self,
        *,
        current_user: models.User,
        skip: int,
        limit: int,
        tipo_geracao: Optional[str],
        data_inicio: Optional[datetime],
        data_fim: Optional[datetime],
    ) -> schemas.UsoIAPage:
        return self._workflow.list_usos_ia_usuario(
            db=self._db,
            current_user=current_user,
            skip=skip,
            limit=limit,
            tipo_geracao=tipo_geracao,
            data_inicio=data_inicio,
            data_fim=data_fim,
        )

    def read_usos_ia_por_produto(
        self,
        *,
        current_user: models.User,
        produto_id: int,
        skip: int,
        limit: int,
    ) -> List[schemas.RegistroUsoIAResponse]:
        return self._workflow.read_usos_ia_por_produto(
            db=self._db,
            current_user=current_user,
            produto_id=produto_id,
            skip=skip,
            limit=limit,
        )

    def read_uso_ia_especifico(
        self,
        *,
        current_user: models.User,
        registro_id: int,
    ) -> schemas.RegistroUsoIAResponse:
        return self._workflow.read_uso_ia_especifico(
            db=self._db,
            current_user=current_user,
            registro_id=registro_id,
        )


_build_uso_ia_request_workflow = build_request_scoped_dependency(
    lambda session: _UsoIARequestScope(db=session),
)


@router.post("/", response_model=schemas.RegistroUsoIAResponse, status_code=status.HTTP_201_CREATED)
def create_uso_ia_endpoint(
    uso_ia_data: schemas.RegistroUsoIACreate,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_workflow: _UsoIARequestScope = Depends(_build_uso_ia_request_workflow),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (create_uso_ia_endpoint)."""
    return request_workflow.create_uso_ia(
        current_user=current_user,
        uso_ia_data=uso_ia_data,
    )


@router.get("/", response_model=schemas.UsoIAPage)
def read_usos_ia_usuario_logado(
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_workflow: _UsoIARequestScope = Depends(_build_uso_ia_request_workflow),
    skip: int = Query(0, ge=0, description="Numero de itens para pular"),
    limit: int = Query(100, ge=1, le=200, description="Numero maximo por pagina"),
    tipo_geracao: Optional[str] = Query(None, description="Filtrar por tipo de geracao"),
    data_inicio: Optional[datetime] = Query(None, description="Data de inicio (ISO)"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (ISO)"),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (read_usos_ia_usuario_logado)."""
    return request_workflow.list_usos_ia_usuario(
        current_user=current_user,
        skip=skip,
        limit=limit,
        tipo_geracao=tipo_geracao,
        data_inicio=data_inicio,
        data_fim=data_fim,
    )


@router.get("/por-produto/{produto_id}", response_model=List[schemas.RegistroUsoIAResponse])
def read_usos_ia_por_produto(
    produto_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_workflow: _UsoIARequestScope = Depends(_build_uso_ia_request_workflow),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=200),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (read_usos_ia_por_produto)."""
    return request_workflow.read_usos_ia_por_produto(
        current_user=current_user,
        produto_id=produto_id,
        skip=skip,
        limit=limit,
    )


@router.get("/{registro_id}", response_model=schemas.RegistroUsoIAResponse)
def read_uso_ia_especifico(
    registro_id: int,
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    request_workflow: _UsoIARequestScope = Depends(_build_uso_ia_request_workflow),
):
    """Endpoint HTTP que delega a execucao para workflow/servico OO (read_uso_ia_especifico)."""
    return request_workflow.read_uso_ia_especifico(
        current_user=current_user,
        registro_id=registro_id,
    )





