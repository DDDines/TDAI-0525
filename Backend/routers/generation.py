# tdai_project/Backend/routers/generation.py
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional

# Imports de módulos no mesmo nível de Backend/ ou subpastas de Backend/
import crud #
import models #
import schemas #
from database import get_db, SessionLocal #
from core.config import settings #

# Import de módulo no mesmo diretório (routers/)
from .auth_utils import get_current_active_user #

# CORREÇÃO APLICADA:
# 'services' é uma subpasta de 'Backend/'. Como o CWD é 'Backend/',
# podemos importar 'services' diretamente como um pacote de nível superior nesse contexto.
from services import ia_generation_service, limit_service #


router = APIRouter(
    prefix="/geracao",
    tags=["Geração de Conteúdo com IA"],
    dependencies=[Depends(get_current_active_user)]
)

async def _tarefa_processar_geracao_e_registrar_uso(
    db_session_factory,
    user_id: int,
    produto_id: int,
    tipo_geracao_principal: str,
    tipo_geracao_registro_uso: str,
    modelo_ia_usado_base: str,
    funcao_geracao_ia,
    **kwargs_geracao
):
    db: Session = db_session_factory()
    db_produto: Optional[models.Produto] = None
    try:
        user = crud.get_user(db, user_id)
        if not user:
            print(f"Tarefa de Geração: Usuário {user_id} não encontrado.")
            return

        db_produto = crud.get_produto(db, produto_id=produto_id)
        if not db_produto:
            print(f"Tarefa de Geração: Produto {produto_id} não encontrado.")
            return
        
        if db_produto.user_id != user.id and not user.is_superuser:
            print(f"Tarefa de Geração: Usuário {user_id} não autorizado para produto {produto_id}.")
            return

        dados_produto_prompt = {
            "nome_base": db_produto.nome_base,
            "marca": db_produto.marca,
            "categoria_original": db_produto.categoria_original,
            "dados_brutos": db_produto.dados_brutos
        }
        
        api_key_para_usar = user.chave_openai_pessoal or settings.OPENAI_API_KEY
        modelo_ia_final = modelo_ia_usado_base
        
        if "openai" in modelo_ia_usado_base.lower() and not api_key_para_usar:
            print(f"Tarefa de Geração: Chave API OpenAI não disponível para usuário {user_id} para produto {produto_id}.")
            if db_produto:
                 log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
                 if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
                 log_atual["historico_mensagens"].append(f"ERRO_IA_GERACAO: Chave API OpenAI não configurada.")
                 crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(log_enriquecimento_web=log_atual))
            return

        print(f"Tarefa de Geração: Chamando IA para produto {produto_id}, tipo: {tipo_geracao_principal}")
        resultado_ia = await funcao_geracao_ia(
            dados_produto=dados_produto_prompt,
            user_api_key=api_key_para_usar,
            idioma=user.idioma_preferido or "pt-BR",
            **kwargs_geracao
        )
        print(f"Tarefa de Geração: Resultado IA para produto {produto_id} (truncado): {str(resultado_ia)[:200]}...")

        uso_ia_schema_data = {
            "produto_id": produto_id,
            "tipo_geracao": tipo_geracao_registro_uso,
            "modelo_ia_usado": modelo_ia_final,
            "resultado_gerado": str(resultado_ia),
            "prompt_utilizado": kwargs_geracao.get("prompt_completo_debug")
        }
        
        uso_ia_obj_para_criar = schemas.UsoIACreate(**uso_ia_schema_data)
        crud.create_uso_ia(db=db, uso_ia=uso_ia_obj_para_criar, user_id=user.id)

        update_data_dict: Dict[str, Any] = {}
        if tipo_geracao_principal == "titulo" and isinstance(resultado_ia, list):
            update_data_dict["titulos_sugeridos"] = {f"titulo_{i+1}": titulo for i, titulo in enumerate(resultado_ia)}
        elif tipo_geracao_principal == "descricao" and isinstance(resultado_ia, str):
            update_data_dict["descricao_principal_gerada"] = resultado_ia
        
        if update_data_dict and db_produto:
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_dict))
        
        print(f"Tarefa de Geração: Produto {produto_id} atualizado com resultado da IA.")

    except ValueError as ve:
        print(f"Tarefa de Geração: Erro de valor para produto {produto_id}: {ve}")
        if db_produto:
             log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
             if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
             log_atual["historico_mensagens"].append(f"ERRO_IA_GERACAO_VALUE_ERROR: {str(ve)}")
             crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(log_enriquecimento_web=log_atual))
    except Exception as e:
        import traceback
        print(f"Tarefa de Geração: Erro inesperado para produto {produto_id}: {traceback.format_exc()}")
        if db_produto:
             log_atual = db_produto.log_enriquecimento_web or {"historico_mensagens": []}
             if not isinstance(log_atual.get("historico_mensagens"), list): log_atual["historico_mensagens"] = []
             log_atual["historico_mensagens"].append(f"ERRO_CRITICO_IA_GERACAO: {str(e)}")
             crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(log_enriquecimento_web=log_atual))
    finally:
        print(f"Finalizando tarefa de geração IA para produto ID: {produto_id}")
        db.close()


@router.post("/titulos/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, summary="Gerar Títulos com OpenAI (Background)")
async def agendar_geracao_novos_titulos_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    try:
        limit_service.verificar_limite_uso(db=db, user=current_user, tipo_geracao_principal="titulo")
    except HTTPException as e_limit:
        raise e_limit

    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="titulo",
        tipo_geracao_registro_uso="titulo_openai_produto",
        modelo_ia_usado_base="openai_gpt-3.5-turbo",
        funcao_geracao_ia=ia_generation_service.gerar_titulos_produto_openai,
        quantidade=5
    )
    return {"message": f"Geração de títulos para o produto ID {produto_id} agendada."}


@router.post("/descricao/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED, summary="Gerar Descrição com OpenAI (Background)")
async def agendar_geracao_nova_descricao_openai(
    produto_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    try:
        limit_service.verificar_limite_uso(db=db, user=current_user, tipo_geracao_principal="descricao")
    except HTTPException as e_limit:
        raise e_limit

    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="descricao",
        tipo_geracao_registro_uso="descricao_openai_produto",
        modelo_ia_usado_base="openai_gpt-3.5-turbo",
        funcao_geracao_ia=ia_generation_service.gerar_descricao_produto_openai
    )
    return {"message": f"Geração de descrição para o produto ID {produto_id} agendada."}