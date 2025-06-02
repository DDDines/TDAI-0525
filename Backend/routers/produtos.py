# Backend/routers/produtos.py

from typing import List, Optional, Union

from fastapi import (APIRouter, Depends, HTTPException, Query, BackgroundTasks,
                     status, UploadFile, File, Form)
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

import crud
import models
import schemas
import database
from . import auth_utils
from core import config # Adicionado para settings_dependency
# A importação problemática de services.ia_generation_service foi removida.

router = APIRouter(
    prefix="/produtos",
    tags=["produtos"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)


@router.post("/", response_model=schemas.Produto, status_code=status.HTTP_201_CREATED)
def create_produto(
    produto: schemas.ProdutoCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    """
    Cria um novo produto para o usuário logado.
    """
    # Verifica se o fornecedor pertence ao usuário atual
    if produto.fornecedor_id:
        fornecedor = crud.get_fornecedor(db, fornecedor_id=produto.fornecedor_id)
        if not fornecedor or fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Fornecedor com ID {produto.fornecedor_id} não encontrado ou não pertence ao usuário.")

    # Validação do tipo de produto, se fornecido
    if produto.product_type_id:
        product_type = crud.get_product_type(db, product_type_id=produto.product_type_id)
        if not product_type:
            raise HTTPException(status_code=404, detail=f"Tipo de Produto com ID {produto.product_type_id} não encontrado.")
        # Poderia adicionar validação se o tipo de produto é global ou pertence ao usuário, se aplicável.

    produto_db = crud.create_user_produto(db=db, produto=produto, user_id=current_user.id)
    
    # Atualiza o nome_chat_api se não foi fornecido explicitamente no payload
    # A lógica para nome_chat_api agora está no crud.create_user_produto
    
    return produto_db


@router.get("/{produto_id}", response_model=schemas.Produto)
def read_produto(
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Obtém os detalhes de um produto específico.
    """
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado a visualizar este produto")
    return db_produto


@router.get("/", response_model=schemas.ProdutoPage)
def read_produtos(
    db: Session = Depends(database.get_db),
    skip: int = Query(0, ge=0, description="Número de itens para pular"),
    limit: int = Query(10, ge=1, le=200, description="Número máximo de itens por página"),
    sort_by: Optional[str] = Query(None, description="Campo para ordenação (ex: nome_original, preco_venda)"),
    sort_order: Optional[str] = Query("asc", description="Ordem da ordenação (asc ou desc)"),
    search: Optional[str] = Query(None, description="Termo de busca para nome, descrição, SKU, EAN"),
    fornecedor_id: Optional[int] = Query(None, description="ID do fornecedor para filtrar produtos"),
    categoria: Optional[str] = Query(None, description="Categoria para filtrar produtos"),
    status_enriquecimento_web: Optional[models.StatusEnriquecimento] = Query(None, description="Filtrar por status de enriquecimento web"),
    status_titulo_ia: Optional[models.StatusIA] = Query(None, description="Filtrar por status de geração de título por IA"),
    status_descricao_ia: Optional[models.StatusIA] = Query(None, description="Filtrar por status de geração de descrição por IA"),
    product_type_id: Optional[int] = Query(None, description="ID do Tipo de Produto para filtrar produtos"),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Lista produtos com paginação, filtros e ordenação.
    - Administradores podem ver todos os produtos.
    - Usuários normais veem apenas seus próprios produtos.
    """
    user_id_filter = None if current_user.is_superuser else current_user.id

    produtos_db = crud.get_produtos_paginados_filtrados_ordenados(
        db,
        user_id=user_id_filter, # Passa o ID do usuário ou None se for admin
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
        search=search,
        fornecedor_id=fornecedor_id,
        categoria=categoria,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
        product_type_id=product_type_id,
        is_admin=current_user.is_superuser # Informa se o usuário é admin para lógica interna do CRUD
    )
    total_items = crud.count_produtos_filtrados(
        db,
        user_id=user_id_filter, # Passa o ID do usuário ou None se for admin
        search=search,
        fornecedor_id=fornecedor_id,
        categoria=categoria,
        status_enriquecimento_web=status_enriquecimento_web,
        status_titulo_ia=status_titulo_ia,
        status_descricao_ia=status_descricao_ia,
        product_type_id=product_type_id,
        is_admin=current_user.is_superuser # Informa se o usuário é admin para lógica interna do CRUD
    )
    return {"items": produtos_db, "total_items": total_items, "page": skip // limit, "limit": limit}


@router.put("/{produto_id}", response_model=schemas.Produto)
def update_produto(
    produto_id: int,
    produto: schemas.ProdutoUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Atualiza um produto existente.
    """
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado a modificar este produto")

    # Verifica se o fornecedor pertence ao usuário atual, se fornecedor_id for alterado
    if produto.fornecedor_id is not None and produto.fornecedor_id != db_produto.fornecedor_id:
        fornecedor = crud.get_fornecedor(db, fornecedor_id=produto.fornecedor_id)
        if not fornecedor or fornecedor.user_id != current_user.id:
            raise HTTPException(status_code=404, detail=f"Fornecedor com ID {produto.fornecedor_id} não encontrado ou não pertence ao usuário.")

    # Validação do tipo de produto, se fornecido e alterado
    if produto.product_type_id is not None and produto.product_type_id != db_produto.product_type_id:
        product_type = crud.get_product_type(db, product_type_id=produto.product_type_id)
        if not product_type: # Adicionar verificação se o tipo é global ou do usuário aqui se necessário
            raise HTTPException(status_code=404, detail=f"Tipo de Produto com ID {produto.product_type_id} não encontrado.")

    updated_produto = crud.update_produto(db=db, produto_id=produto_id, produto_update_data=produto)
    return updated_produto


@router.delete("/{produto_id}", response_model=schemas.Produto)
def delete_produto(
    produto_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Deleta um produto.
    """
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if db_produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado a deletar este produto")
    
    crud.delete_produto(db=db, produto_id=produto_id)
    return db_produto


@router.post("/batch-delete/", response_model=List[schemas.Produto])
def batch_delete_produtos(
    produto_ids: List[int],
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Deleta múltiplos produtos em lote.
    Apenas o proprietário dos produtos ou um superusuário pode deletá-los.
    """
    deleted_produtos = []
    not_found_ids = []
    not_authorized_ids = []

    for produto_id in produto_ids:
        db_produto = crud.get_produto(db, produto_id=produto_id)
        if db_produto is None:
            not_found_ids.append(produto_id)
            continue
        
        if not current_user.is_superuser and db_produto.user_id != current_user.id:
            not_authorized_ids.append(produto_id)
            continue
        
        crud.delete_produto(db=db, produto_id=produto_id)
        deleted_produtos.append(schemas.Produto.from_orm(db_produto)) # Converte o objeto ORM para o schema Pydantic

    if not_found_ids or not_authorized_ids:
        error_detail = []
        if not_found_ids:
            error_detail.append(f"Produtos não encontrados: IDs {not_found_ids}.")
        if not_authorized_ids:
            error_detail.append(f"Não autorizado a deletar produtos: IDs {not_authorized_ids}.")
        
        # Se nenhum produto foi deletado com sucesso e houve erros, levanta uma exceção geral.
        # Se alguns foram deletados, pode-se optar por retornar os deletados com um aviso parcial.
        # Por simplicidade aqui, se houver qualquer erro, levanta exceção.
        # Uma abordagem mais granular poderia retornar um JSON com "sucessos" e "falhas".
        if not deleted_produtos:
             raise HTTPException(status_code=404, detail=" ".join(error_detail))
        else:
            # Se alguns foram deletados, mas outros não, ainda retorna os deletados
            # e o cliente pode ser informado sobre as falhas através de uma mensagem customizada ou logs.
            # Para este exemplo, vamos focar em retornar os que foram deletados.
            # O frontend pode precisar de uma forma de saber quais falharam.
            # Considerar adicionar um campo `warnings` ou `errors` na resposta.
            pass # Continua para retornar os deleted_produtos

    if not deleted_produtos and not (not_found_ids or not_authorized_ids):
         raise HTTPException(status_code=400, detail="Nenhum ID de produto fornecido ou lista de IDs vazia.")

    return deleted_produtos


@router.post("/upload-image/{produto_id}", response_model=schemas.Produto)
async def upload_produto_image(
    produto_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    """
    Faz upload de uma imagem para um produto e a define como imagem principal.
    A imagem é salva no diretório `static/product_images` e o caminho relativo é
    armazenado no campo `imagem_principal_url` do produto.
    """
    db_produto = crud.get_produto(db, produto_id=produto_id)
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    if not current_user.is_superuser and db_produto.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Não autorizado a modificar este produto")

    # Salva o arquivo e obtém o caminho
    try:
        file_path = await crud.save_produto_image(db, produto_id, file)
    except ValueError as e: # Captura erro se o formato do arquivo não for permitido
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e: # Outras exceções ao salvar
        # Logar o erro 'e' aqui seria uma boa prática
        raise HTTPException(status_code=500, detail=f"Não foi possível salvar a imagem: {str(e)}")


    # Atualiza o produto com o caminho da imagem
    produto_update_data = schemas.ProdutoUpdate(imagem_principal_url=file_path)
    updated_produto = crud.update_produto(db=db, produto_id=produto_id, produto_update_data=produto_update_data)
    
    return updated_produto

# O endpoint que causava o ImportError foi removido daqui.
# A funcionalidade de gerar descrição via IA deve ser acessada por /api/v1/geracao/descricao/{produto_id}