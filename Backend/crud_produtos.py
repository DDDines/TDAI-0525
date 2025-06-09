import logging
import json
import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy import func, or_, desc, asc
from sqlalchemy.orm import Session, selectinload

from Backend.core.config import settings
from Backend.models import Produto, Fornecedor, ProductType, StatusEnriquecimentoEnum, StatusGeracaoIAEnum
from fastapi import UploadFile
from Backend import schemas

logger = logging.getLogger(__name__)

# --- Produto CRUD ---
def create_produto(db: Session, produto: schemas.ProdutoCreate, user_id: int) -> Produto:
    produto_data = produto.model_dump(exclude_unset=True)
    
    # Assegura que campos JSON estejam como dicts
    if 'dynamic_attributes' in produto_data and isinstance(produto_data['dynamic_attributes'], str):
        try:
            produto_data['dynamic_attributes'] = json.loads(produto_data['dynamic_attributes'])
        except json.JSONDecodeError:
            raise ValueError("dynamic_attributes não é um JSON string válido.")

    if 'dados_brutos_web' in produto_data and isinstance(produto_data['dados_brutos_web'], str):
        try:
            produto_data['dados_brutos_web'] = json.loads(produto_data['dados_brutos_web'])
        except json.JSONDecodeError:
            raise ValueError("dados_brutos_web não é um JSON string válido.")

    if 'log_enriquecimento_web' in produto_data and isinstance(produto_data['log_enriquecimento_web'], str):
        try:
            produto_data['log_enriquecimento_web'] = json.loads(produto_data['log_enriquecimento_web'])
        except json.JSONDecodeError:
            raise ValueError("log_enriquecimento_web não é um JSON string válido.")

    db_produto = Produto(**produto_data, user_id=user_id)
    db.add(db_produto)
    db.commit()
    db.refresh(db_produto)
    return db_produto


def create_produtos_bulk(db: Session, produtos: List[schemas.ProdutoCreate], user_id: int) -> List[Produto]:
    """Cria múltiplos produtos em uma única transação."""
    db_produtos: List[Produto] = []
    for produto_schema in produtos:
        db_produto = Produto(**produto_schema.model_dump(exclude_unset=True), user_id=user_id)
        db.add(db_produto)
        db_produtos.append(db_produto)
    db.commit()
    for p in db_produtos:
        db.refresh(p)
    return db_produtos


def get_produto(db: Session, produto_id: int) -> Optional[Produto]:
    # Usar selectinload para carregar relacionamentos de forma eficiente se sempre forem acessados
    return db.query(Produto).options(
        selectinload(Produto.fornecedor),
        selectinload(Produto.product_type).selectinload(ProductType.attribute_templates)
    ).filter(Produto.id == produto_id).first()


def get_produtos_by_user(
    db: Session,
    user_id: Optional[int], # Se None e is_admin=True, busca todos. Se user_id e is_admin=False, busca do usuário.
    is_admin: bool,
    skip: int = 0,
    limit: int = 10,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc",
    search: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    categoria: Optional[str] = None, # Adicionado
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None, # Adicionado
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None, # Adicionado
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None # Adicionado
) -> List[Produto]:
    query = db.query(Produto).options(
        selectinload(Produto.fornecedor),
        selectinload(Produto.product_type) # Carrega product_type, mas não seus atributos aqui para a lista
    )

    if not is_admin:
        if user_id is None: # Não deveria acontecer se não for admin e não tiver user_id
            return []
        query = query.filter(Produto.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Produto.nome_base).ilike(search_term),
                func.lower(Produto.nome_chat_api).ilike(search_term),
                func.lower(Produto.descricao_original).ilike(search_term),
                func.lower(Produto.descricao_chat_api).ilike(search_term),
                func.lower(Produto.sku).ilike(search_term),
                func.lower(Produto.ean).ilike(search_term),
                func.lower(Produto.marca).ilike(search_term),
                func.lower(Produto.modelo).ilike(search_term)
            )
        )
    
    if fornecedor_id is not None:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if product_type_id is not None:
        query = query.filter(Produto.product_type_id == product_type_id)
    if categoria:
        query = query.filter(func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%")) # Ou categoria_mapeada
    if status_enriquecimento_web:
        query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(Produto.status_descricao_ia == status_descricao_ia)

    if sort_by:
        column_to_sort = getattr(Produto, sort_by, None)
        if column_to_sort:
            if sort_order.lower() == "desc":
                query = query.order_by(desc(column_to_sort))
            else:
                query = query.order_by(asc(column_to_sort))
        else: # Fallback ou log de erro se sort_by for inválido
            query = query.order_by(Produto.id) 
    else:
        query = query.order_by(Produto.id) # Ordenação padrão

    return query.offset(skip).limit(limit).all()


def count_produtos_by_user(
    db: Session,
    user_id: Optional[int],
    is_admin: bool,
    search: Optional[str] = None,
    fornecedor_id: Optional[int] = None,
    product_type_id: Optional[int] = None,
    categoria: Optional[str] = None,
    status_enriquecimento_web: Optional[StatusEnriquecimentoEnum] = None,
    status_titulo_ia: Optional[StatusGeracaoIAEnum] = None,
    status_descricao_ia: Optional[StatusGeracaoIAEnum] = None
) -> int:
    query = db.query(func.count(Produto.id))

    if not is_admin:
        if user_id is None:
            return 0
        query = query.filter(Produto.user_id == user_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(
            or_(
                func.lower(Produto.nome_base).ilike(search_term),
                func.lower(Produto.nome_chat_api).ilike(search_term),
                func.lower(Produto.descricao_original).ilike(search_term),
                func.lower(Produto.descricao_chat_api).ilike(search_term),
                func.lower(Produto.sku).ilike(search_term),
                func.lower(Produto.ean).ilike(search_term),
                func.lower(Produto.marca).ilike(search_term),
                func.lower(Produto.modelo).ilike(search_term)
            )
        )
    if fornecedor_id is not None:
        query = query.filter(Produto.fornecedor_id == fornecedor_id)
    if product_type_id is not None:
        query = query.filter(Produto.product_type_id == product_type_id)
    if categoria:
        query = query.filter(func.lower(Produto.categoria_original).ilike(f"%{categoria.lower()}%"))
    if status_enriquecimento_web:
        query = query.filter(Produto.status_enriquecimento_web == status_enriquecimento_web)
    if status_titulo_ia:
        query = query.filter(Produto.status_titulo_ia == status_titulo_ia)
    if status_descricao_ia:
        query = query.filter(Produto.status_descricao_ia == status_descricao_ia)
        
    count = query.scalar()
    return count if count is not None else 0

def update_produto(db: Session, db_produto: Produto, produto_update: schemas.ProdutoUpdate) -> Produto:
    update_data = produto_update.model_dump(exclude_unset=True)


    # Lógica para campos JSON (dynamic_attributes, dados_brutos_web, log_enriquecimento_web, imagens_secundarias_urls)
    # Pydantic deve entregar dict/list se o schema estiver correto (não Json[Type])
    # O modelo SQLAlchemy aceita dict/list para colunas JSON.
    for field in ['dynamic_attributes', 'dados_brutos_web', 'log_enriquecimento_web', 'imagens_secundarias_urls']:
        if field in update_data and update_data[field] is not None:
            # Se o schema já garante o tipo correto (dict/list), apenas atribua
            # Se o schema ainda for Json[Type] e vier uma string, precisa de json.loads aqui
            # Assumindo que o schema.ProdutoUpdate terá Dict/List para esses campos:
            pass # setattr abaixo cuidará disso
          
    for key, value in update_data.items():
        setattr(db_produto, key, value)
    
    db.commit()
    db.refresh(db_produto)
    # Recarregar relacionamentos se forem modificados ou para garantir consistência na resposta
    db.refresh(db_produto, attribute_names=['fornecedor', 'product_type'])
    if db_produto.product_type: # Para garantir que os atributos do tipo também sejam carregados se product_type for acessado
        db.refresh(db_produto.product_type, attribute_names=['attribute_templates'])
    return db_produto


def delete_produto(db: Session, db_produto: Produto) -> Produto:
    # Antes de deletar, pode ser necessário limpar referências em RegistroUsoIA se não houver cascade
    # No seu modelo, RegistroUsoIA tem cascade="all, delete-orphan" para produto, então está OK.
    db.delete(db_produto)
    db.commit()
    return db_produto


async def save_produto_image(db: Session, produto_id: int, file: UploadFile) -> str:
    """Salva a imagem enviada para um produto e retorna o caminho relativo."""
    if not file.filename:
        raise ValueError("Nome do arquivo não fornecido.")

    upload_dir = Path(settings.UPLOAD_DIRECTORY)
    if not upload_dir.is_absolute():
        upload_dir = Path(__file__).resolve().parent / upload_dir
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_extension = Path(file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    file_path = upload_dir / unique_filename

    try:
        content = await file.read()
        with open(file_path, "wb") as f_out:
            f_out.write(content)
    except Exception as e:
        raise IOError(f"Não foi possível salvar o arquivo: {e}")
    finally:
        await file.close()

    relative = Path(settings.UPLOAD_DIRECTORY) / unique_filename
    return f"/{relative.as_posix()}"

