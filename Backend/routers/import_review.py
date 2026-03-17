"""Router HTTP para revisao de importacoes."""

from __future__ import annotations

from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from Backend import models, schemas
from Backend.application.services.import_validation_memory_service import (
    ImportValidationMemoryService,
)
from Backend.application.services.service_container import ServiceContainerDependencySupport
from Backend.infrastructure.repositories.catalog_import_file_repository import CatalogImportFileRepository as CatalogFileRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository

from . import auth_utils

router = APIRouter(
    prefix="/importacoes",
    tags=["Revisao de Importacao"],
    dependencies=[Depends(auth_utils._AuthUtilsActiveUserDependency.get_current_active_user)],
    redirect_slashes=False,
)


@router.get("/{file_id}/quarentena", response_model=List[schemas.ImportQuarantineItemResponse])
def listar_produtos_quarentenados(
    file_id: int,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Lista os produtos quarentenados de uma importacao aguardando revisao."""
    repo = CatalogFileRepository(session)
    catalog_file = repo.get_catalog_file_for_user(file_id=file_id, user_id=current_user.id)
    if not catalog_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado")

    svc = ImportValidationMemoryService(db=session, models=models, schemas=schemas)
    items = svc.get_quarantine_items(catalog_file=catalog_file)

    result: List[schemas.ImportQuarantineItemResponse] = []
    for idx, item in enumerate(items):
        cleaned = item.get("linha_sanitizada") or item.get("linha_validada") or item.get("linha_original") or {}
        result.append(
            schemas.ImportQuarantineItemResponse(
                index=idx,
                nome_base=(cleaned.get("nome_base") or cleaned.get("sku_original") or ""),
                sku=cleaned.get("sku_original"),
                quality_score=item.get("qualidade_score"),
                reason=item.get("motivo_descarte"),
                raw_data=cleaned,
            )
        )
    return result


@router.post("/{file_id}/quarentena/{item_index}/aprovar", response_model=schemas.ProdutoResponse)
def aprovar_produto_quarentenado(
    file_id: int,
    item_index: int,
    payload: schemas.ImportReviewApproveRequest,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
):
    """Aprova um produto quarentenado, criando-o no catalogo."""
    repo = CatalogFileRepository(session)
    catalog_file = repo.get_catalog_file_for_user(file_id=file_id, user_id=current_user.id)
    if not catalog_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado")

    svc = ImportValidationMemoryService(
        db=session,
        models=models,
        schemas=schemas,
        product_store=ProductRepository(session),
    )
    produto = svc.approve_item(
        catalog_file=catalog_file,
        item_index=item_index,
        current_user=current_user,
        remember=payload.remember,
        min_quality_score=payload.min_quality_score,
    )
    if produto is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item nao encontrado na fila de quarentena",
        )
    session.commit()
    session.refresh(produto)
    return schemas.ProdutoResponse.model_validate(produto)


@router.post("/{file_id}/quarentena/aprovar-lote")
def aprovar_lote_quarentena(
    file_id: int,
    payload: schemas.ImportReviewBatchApproveRequest,
    current_user: models.User = Depends(
        auth_utils._AuthUtilsActiveUserDependency.get_current_active_user
    ),
    session: Session = Depends(ServiceContainerDependencySupport.get_request_db_session),
) -> Any:
    """Aprova em lote todos os itens com score >= threshold."""
    repo = CatalogFileRepository(session)
    catalog_file = repo.get_catalog_file_for_user(file_id=file_id, user_id=current_user.id)
    if not catalog_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Arquivo nao encontrado")

    svc = ImportValidationMemoryService(
        db=session,
        models=models,
        schemas=schemas,
        product_store=ProductRepository(session),
    )
    items = svc.get_quarantine_items(catalog_file=catalog_file)
    approved_count = 0

    for idx, item in enumerate(items):
        score = item.get("qualidade_score")
        if score is None or score >= payload.min_quality_score:
            result = svc.approve_item(
                catalog_file=catalog_file,
                item_index=idx,
                current_user=current_user,
                remember=False,
            )
            if result is not None:
                approved_count += 1

    if payload.remember and catalog_file.fornecedor_id:
        svc.save_acceptance_rule(
            user_id=current_user.id,
            fornecedor_id=catalog_file.fornecedor_id,
            min_quality_score=payload.min_quality_score,
        )

    session.commit()
    return {"aprovados": approved_count, "threshold_score": payload.min_quality_score}
