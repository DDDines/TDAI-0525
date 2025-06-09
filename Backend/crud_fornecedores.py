import logging
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from Backend.models import Fornecedor
from Backend import schemas

logger = logging.getLogger(__name__)

# --- Fornecedor CRUD ---
def create_fornecedor(db: Session, fornecedor: schemas.FornecedorCreate, user_id: int) -> Fornecedor:
    fornecedor_data = fornecedor.model_dump()
    if fornecedor_data.get("site_url"):
        fornecedor_data["site_url"] = str(fornecedor_data["site_url"])
    if fornecedor_data.get("link_busca_padrao"):
        fornecedor_data["link_busca_padrao"] = str(fornecedor_data["link_busca_padrao"])

    db_fornecedor = Fornecedor(**fornecedor_data, user_id=user_id)
    db.add(db_fornecedor)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def get_fornecedor(db: Session, fornecedor_id: int) -> Optional[Fornecedor]:
    return db.query(Fornecedor).filter(Fornecedor.id == fornecedor_id).first()

def get_fornecedores_by_user(
    db: Session,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    skip: int = 0,
    limit: int = 10,
    search: Optional[str] = None,
) -> List[Fornecedor]:
    query = db.query(Fornecedor)
    if not is_admin and user_id:
        query = query.filter(Fornecedor.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Fornecedor.nome).ilike(search_term),
                func.lower(Fornecedor.email_contato).ilike(search_term),
                func.lower(Fornecedor.contato_principal).ilike(search_term),
            )
        )
    return query.order_by(Fornecedor.nome).offset(skip).limit(limit).all()

def count_fornecedores_by_user(
    db: Session,
    user_id: Optional[int] = None,
    is_admin: bool = False,
    search: Optional[str] = None,
) -> int:
    query = db.query(func.count(Fornecedor.id))
    if not is_admin and user_id:
        query = query.filter(Fornecedor.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Fornecedor.nome).ilike(search_term),
                func.lower(Fornecedor.email_contato).ilike(search_term),
                func.lower(Fornecedor.contato_principal).ilike(search_term),
            )
        )
    return query.scalar() or 0

def update_fornecedor(db: Session, db_fornecedor: Fornecedor, fornecedor_update: schemas.FornecedorUpdate) -> Fornecedor:
    update_data = fornecedor_update.model_dump(exclude_unset=True)

    if "site_url" in update_data and update_data["site_url"] is not None:
        update_data["site_url"] = str(update_data["site_url"])
    if "link_busca_padrao" in update_data and update_data["link_busca_padrao"] is not None:
        update_data["link_busca_padrao"] = str(update_data["link_busca_padrao"])

    for key, value in update_data.items():
        setattr(db_fornecedor, key, value)
    db.commit()
    db.refresh(db_fornecedor)
    return db_fornecedor

def delete_fornecedor(db: Session, db_fornecedor: Fornecedor) -> Fornecedor:
    db.delete(db_fornecedor)
    db.commit()
    return db_fornecedor
