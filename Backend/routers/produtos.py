# Backend/routers/produtos.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

import schemas
import models
import crud
from database import get_db
from routers import auth_utils

# Corrigindo NOMES das funções importadas para corresponder aos arquivos de serviço
from services.web_data_extractor_service import extract_relevant_data_from_url 
from services.ia_generation_service import (
    gerar_descricao_produto_openai, # Nome corrigido
    gerar_titulos_produto_openai    # Nome corrigido
)


router = APIRouter(
    prefix="/produtos", 
    tags=["Produtos"],
    responses={404: {"description": "Not found"}},
)

@router.post("/", response_model=schemas.Produto, status_code=status.HTTP_201_CREATED)
def create_user_produto(
    produto: schemas.ProdutoCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    if produto.fornecedor_id:
        db_fornecedor = crud.get_fornecedor(db, fornecedor_id=produto.fornecedor_id, user_id=current_user.id)
        if not db_fornecedor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fornecedor com id {produto.fornecedor_id} não encontrado ou não pertence ao usuário."
            )
    return crud.create_produto(db=db, produto=produto, user_id=current_user.id)

@router.get("/", response_model=schemas.ProdutoPage)
def read_user_produtos(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, min_length=1, max_length=100, description="Busca por nome_base, marca ou sku_original"),
    status_enriquecimento: Optional[str] = Query(None, description="Filtro por status de enriquecimento web (PENDENTE, EM_PROGRESSO, CONCLUIDO_SUCESSO, FALHOU)"),
    status_titulo: Optional[str] = Query(None, description="Filtro por status de geração de título IA"),
    status_descricao: Optional[str] = Query(None, description="Filtro por status de geração de descrição IA"),
    fornecedor_id: Optional[int] = Query(None, description="Filtro por ID do fornecedor"),
    sort_by: Optional[str] = Query("created_at", description="Campo para ordenação (ex: nome_base, created_at)"),
    sort_order: Optional[str] = Query("desc", description="Ordem da ordenação (asc ou desc)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    produtos_page_data = crud.get_produtos(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
        search_term=search,
        status_enriquecimento_web=status_enriquecimento,
        status_titulo_ia=status_titulo,
        status_descricao_ia=status_descricao,
        fornecedor_id=fornecedor_id,
        sort_by=sort_by,
        sort_order=sort_order
    )
    return produtos_page_data

@router.get("/{produto_id}", response_model=schemas.Produto)
def read_user_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado ou não pertence ao usuário")
    return db_produto

@router.put("/{produto_id}", response_model=schemas.Produto)
def update_user_produto(
    produto_id: int,
    produto_update: schemas.ProdutoUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado ou não pertence ao usuário para atualização")

    if produto_update.fornecedor_id is not None:
        if produto_update.fornecedor_id == 0: 
            produto_update.fornecedor_id = None
        else:
            db_fornecedor = crud.get_fornecedor(db, fornecedor_id=produto_update.fornecedor_id, user_id=current_user.id)
            if not db_fornecedor:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Fornecedor com id {produto_update.fornecedor_id} não encontrado ou não pertence ao usuário."
                )
    return crud.update_produto(db=db, db_produto=db_produto, produto_update=produto_update)

@router.delete("/{produto_id}", response_model=schemas.Msg)
def delete_user_produto(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if db_produto is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado ou não pertence ao usuário para deleção")
    
    crud.delete_produto(db=db, db_produto=db_produto)
    return {"message": f"Produto {produto_id} deletado com sucesso."}


@router.post("/batch-update-status/", response_model=List[schemas.Produto])
async def batch_update_produto_status(
    produto_ids: List[int],
    status_field: str = Query(..., description="Campo de status a ser atualizado (ex: status_titulo_ia)"),
    new_status: str = Query(..., description="Novo valor para o status (ex: EM_PROGRESSO)"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    updated_produtos = []
    allowed_status_fields = {
        "status_enriquecimento_web": models.StatusEnriquecimentoEnum,
        "status_titulo_ia": models.StatusGeracaoIAEnum,
        "status_descricao_ia": models.StatusGeracaoIAEnum
    }
    if status_field not in allowed_status_fields:
        raise HTTPException(status_code=400, detail=f"Campo de status '{status_field}' não é permitido para atualização em lote.")

    status_enum_class = allowed_status_fields[status_field]
    try:
        status_enum_value = status_enum_class[new_status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail=f"Valor de status '{new_status}' inválido para o campo '{status_field}'. Valores permitidos: {', '.join([e.name for e in status_enum_class])}")

    produtos_to_update = crud.get_produtos_by_ids(db, produto_ids=produto_ids, user_id=current_user.id)
    
    if len(produtos_to_update) != len(set(produto_ids)): 
        found_ids = {p.id for p in produtos_to_update}
        missing_ids = [pid for pid in set(produto_ids) if pid not in found_ids]
        if missing_ids: 
            print(f"AVISO: Produtos não encontrados ou não pertencentes ao usuário para batch update: {missing_ids}")

    for produto in produtos_to_update:
        setattr(produto, status_field, status_enum_value)
        db.add(produto)
        updated_produtos.append(produto)
    
    if updated_produtos:
        db.commit()
        for produto in updated_produtos: 
            db.refresh(produto)
            db.refresh(produto, attribute_names=['fornecedor']) 
            
    return updated_produtos


# --- Endpoints relacionados a serviços específicos ---

@router.post("/{produto_id}/extract-data-from-url/", response_model=schemas.Produto)
async def extract_data_from_url_endpoint( 
    produto_id: int, 
    url: schemas.HttpUrl, 
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")
    try:
        # Usando o nome correto da função importada: extract_relevant_data_from_url
        updated_produto_data = await extract_relevant_data_from_url(db, str(url), db_produto) 
        return updated_produto_data 
    except Exception as e:
        print(f"Erro ao extrair dados da URL para o produto {produto_id}: {e}")
        db_produto.status_enriquecimento_web = models.StatusEnriquecimentoEnum.FALHOU
        log_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": f"Falha ao extrair dados da URL {url}: {str(e)}"}
        if isinstance(db_produto.log_enriquecimento_web, list):
            db_produto.log_enriquecimento_web.append(log_entry)
        elif db_produto.log_enriquecimento_web is None:
            db_produto.log_enriquecimento_web = [log_entry]
        else: 
            try:
                current_log = list(db_produto.log_enriquecimento_web) if hasattr(db_produto.log_enriquecimento_web, '__iter__') else []
                current_log.append(log_entry)
                db_produto.log_enriquecimento_web = current_log
            except TypeError: 
                 db_produto.log_enriquecimento_web = [log_entry]
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        raise HTTPException(status_code=500, detail=f"Erro ao processar extração da URL: {str(e)}")


@router.post("/{produto_id}/generate-description/", response_model=schemas.Produto)
async def generate_description_endpoint(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    try:
        # Corrigindo a chamada para o nome correto da função no serviço
        updated_produto = await gerar_descricao_produto_openai( 
            dados_produto=db_produto.to_dict_for_ia(), # Supondo que você tenha um método para converter
            user_api_key=current_user.chave_openai_pessoal or settings.OPENAI_API_KEY 
        )
        # Precisamos atualizar o db_produto com a resposta do serviço
        if isinstance(updated_produto, str): # Se a função retorna apenas a string da descrição
            db_produto.descricao_principal_gerada = updated_produto
            db_produto.status_descricao_ia = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        elif isinstance(updated_produto, models.Produto): # Se a função já retorna o objeto produto atualizado
             db_produto = updated_produto
        # (Se a função de serviço já salva no DB e retorna o objeto Produto atualizado,
        #  então podemos apenas retornar 'updated_produto' diretamente.
        #  A função 'gerar_descricao_produto_openai' que você me mostrou retorna uma string)
        
        # Se gerar_descricao_produto_openai retorna apenas a string da descrição:
        # db_produto.descricao_principal_gerada = updated_produto # 'updated_produto' aqui seria a string da descrição
        # db_produto.status_descricao_ia = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        # db.add(db_produto)
        # db.commit()
        # db.refresh(db_produto)
        # return db_produto

        # Ajuste baseado na sua função `gerar_descricao_produto_openai` que retorna uma string:
        descricao_gerada_str = await gerar_descricao_produto_openai(
            # O serviço espera um Dict, precisamos converter o db_produto.
            # Adicione um método ao seu modelo Produto: to_dict_for_ia() ou passe os campos individualmente.
            # Exemplo simplificado:
            dados_produto={
                "nome_base": db_produto.nome_base,
                "marca": db_produto.marca,
                "categoria_original": db_produto.categoria_original,
                "dados_brutos": db_produto.dados_brutos
            },
            user_api_key=current_user.chave_openai_pessoal or settings.OPENAI_API_KEY
        )
        db_produto.descricao_principal_gerada = descricao_gerada_str
        db_produto.status_descricao_ia = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        return db_produto

    except ValueError as ve: 
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Erro ao gerar descrição para produto {produto_id}: {e}")
        db_produto.status_descricao_ia = models.StatusGeracaoIAEnum.FALHOU
        log_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": f"Falha ao gerar descrição com IA: {str(e)}"}
        # (lógica de log omitida por brevidade, mas deve ser igual à do endpoint extract_data)
        if isinstance(db_produto.log_enriquecimento_web, list): db_produto.log_enriquecimento_web.append(log_entry)
        elif db_produto.log_enriquecimento_web is None: db_produto.log_enriquecimento_web = [log_entry]
        else: db_produto.log_enriquecimento_web = [log_entry] # Simplificado
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar descrição: {str(e)}")


@router.post("/{produto_id}/generate-titles/", response_model=schemas.Produto)
async def generate_titles_endpoint(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_produto = crud.get_produto(db, produto_id=produto_id, user_id=current_user.id)
    if not db_produto:
        raise HTTPException(status_code=404, detail="Produto não encontrado")

    try:
        # Corrigindo a chamada para o nome correto da função no serviço
        # E ajustando os dados passados para o serviço
        titulos_gerados_list = await gerar_titulos_produto_openai(
            dados_produto={ # Passar um dicionário conforme o serviço espera
                "nome_base": db_produto.nome_base,
                "marca": db_produto.marca,
                "categoria_original": db_produto.categoria_original,
                "dados_brutos": db_produto.dados_brutos 
            },
            user_api_key=current_user.chave_openai_pessoal or settings.OPENAI_API_KEY,
            # 'idioma' e 'quantidade' usarão os defaults do serviço se não especificados aqui
        )
        db_produto.titulos_sugeridos = titulos_gerados_list
        db_produto.status_titulo_ia = models.StatusGeracaoIAEnum.CONCLUIDO_SUCESSO
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        return db_produto
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        print(f"Erro ao gerar títulos para produto {produto_id}: {e}")
        db_produto.status_titulo_ia = models.StatusGeracaoIAEnum.FALHOU
        log_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "ERROR", "message": f"Falha ao gerar títulos com IA: {str(e)}"}
        # (lógica de log omitida por brevidade)
        if isinstance(db_produto.log_enriquecimento_web, list): db_produto.log_enriquecimento_web.append(log_entry)
        elif db_produto.log_enriquecimento_web is None: db_produto.log_enriquecimento_web = [log_entry]
        else: db_produto.log_enriquecimento_web = [log_entry] # Simplificado
        db.add(db_produto)
        db.commit()
        db.refresh(db_produto)
        raise HTTPException(status_code=500, detail=f"Erro ao gerar títulos: {str(e)}")