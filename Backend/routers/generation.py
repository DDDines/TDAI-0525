# Backend/routers/generation.py

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime # Adicionado datetime

import crud
import models
import schemas
from database import get_db, SessionLocal # Adicionado SessionLocal
from core.config import settings
from routers import auth_utils
from services import ia_generation_service
from services import limit_service

router = APIRouter(
    prefix="/geracao",
    tags=["Geração de Conteúdo com IA"],
    dependencies=[Depends(auth_utils.get_current_active_user)],
)

# Função auxiliar adaptada do seu original para processar em background
async def _tarefa_processar_geracao_e_registrar_uso(
    db_session_factory,
    user_id: int,
    produto_id: int,
    tipo_geracao_principal: str, # "titulo" ou "descricao"
    # creditos_consumidos_pela_acao: int, # O consumo agora é feito dentro do serviço de IA
    funcao_geracao_ia_no_servico,
    **kwargs_para_funcao_servico
):
    db: Session = db_session_factory()
    db_produto: Optional[models.Produto] = None
    status_field_to_update: Optional[str] = None
    campo_produto_para_atualizar_com_resultado: Optional[str] = None
    # tipo_acao_ia_enum_para_registro: models.TipoAcaoIAEnum # O serviço de IA já sabe o tipo de ação

    if tipo_geracao_principal == "titulo":
        status_field_to_update = "status_titulo_ia"
        # Assumindo que o modelo Produto terá um campo para armazenar múltiplos títulos gerados, ex: titulos_gerados_ia (JSON List)
        # Se for para atualizar nome_chat_api com o primeiro título, ajuste aqui.
        # Por agora, vamos assumir que o serviço retorna uma lista e o produto pode armazená-la.
        # Se não, você pode querer salvar o primeiro título em `nome_chat_api`.
        campo_produto_para_atualizar_com_resultado = "nome_chat_api" # Ou um novo campo JSON para lista de títulos
    elif tipo_geracao_principal == "descricao":
        status_field_to_update = "status_descricao_ia"
        campo_produto_para_atualizar_com_resultado = "descricao_chat_api"
    else:
        print(f"Tarefa Background: Tipo de geração principal '{tipo_geracao_principal}' desconhecido.")
        db.close()
        return

    log_entry_prefix = f"IA {tipo_geracao_principal.capitalize()}"

    try:
        user = crud.get_user(db, user_id=user_id)
        if not user:
            print(f"Tarefa Background {log_entry_prefix}: Usuário {user_id} não encontrado.")
            db.close()
            return

        db_produto = crud.get_produto(db, produto_id=produto_id)
        if not db_produto:
            print(f"Tarefa Background {log_entry_prefix}: Produto {produto_id} não encontrado.")
            db.close()
            return
        
        if db_produto.user_id != user.id and not user.is_superuser:
            print(f"Tarefa Background {log_entry_prefix}: Usuário {user_id} não autorizado para produto {produto_id}.")
            db.close()
            return

        # Atualizar status para EM_PROGRESSO
        if status_field_to_update:
            update_data_progresso = {status_field_to_update: models.StatusGeracaoIAEnum.EM_PROGRESSO}
            log_atual_obj = list(db_produto.log_processamento) if db_produto.log_processamento else []
            log_atual_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Geração iniciada."})
            update_data_progresso["log_processamento"] = log_atual_obj
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_progresso))

        print(f"Tarefa Background {log_entry_prefix}: Chamando serviço de IA para produto {produto_id}.")
        
        resultado_ia = await funcao_geracao_ia_no_servico(
            db=db,
            produto_id=produto_id,
            user=user,
            **kwargs_para_funcao_servico
        )
        
        print(f"Tarefa Background {log_entry_prefix}: Resultado IA para produto {produto_id} (truncado): {str(resultado_ia)[:200]}...")

        update_data_final_dict: Dict[str, Any] = {}
        log_final_obj = list(db_produto.log_processamento) if db_produto.log_processamento else []
        
        if resultado_ia and ((isinstance(resultado_ia, str) and resultado_ia.strip()) or (isinstance(resultado_ia, list) and resultado_ia)):
            if campo_produto_para_atualizar_com_resultado:
                # Se o resultado for uma lista de títulos, pegamos o primeiro para nome_chat_api
                # ou você precisa de um campo JSON no Produto para `titulos_sugeridos_ia`
                if tipo_geracao_principal == "titulo" and isinstance(resultado_ia, list) and campo_produto_para_atualizar_com_resultado == "nome_chat_api":
                    update_data_final_dict[campo_produto_para_atualizar_com_resultado] = resultado_ia[0] if resultado_ia else db_produto.nome_chat_api
                    # Se você tiver um campo `titulos_gerados_ia: List[str]` no modelo Produto e schema:
                    # update_data_final_dict["titulos_gerados_ia"] = resultado_ia
                else:
                    update_data_final_dict[campo_produto_para_atualizar_com_resultado] = resultado_ia

            if status_field_to_update: 
                update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.CONCLUIDO
            log_final_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Geração concluída com sucesso."})
        else:
            if status_field_to_update: 
                update_data_final_dict[status_field_to_update] = models.StatusGeracaoIAEnum.FALHA
            log_final_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Falha na geração (resultado vazio ou IA não pôde gerar)."})
            print(f"Tarefa Background {log_entry_prefix}: IA não retornou resultado válido para produto {produto_id}.")
        
        update_data_final_dict["log_processamento"] = log_final_obj
        if update_data_final_dict: # Apenas atualiza se houver algo para mudar
             crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_final_dict))
        print(f"Tarefa Background {log_entry_prefix}: Produto {produto_id} atualizado com resultado e status final.")

    except HTTPException as http_exc: 
        print(f"Tarefa Background {log_entry_prefix}: HTTPException para produto {produto_id}: {http_exc.detail}")
        if db_produto and status_field_to_update:
            log_erro_obj = list(db_produto.log_processamento) if db_produto.log_processamento else []
            log_erro_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Falha ({http_exc.status_code}) - {http_exc.detail}"})
            update_data_falha_http = {
                status_field_to_update: models.StatusGeracaoIAEnum.FALHA,
                "log_processamento": log_erro_obj
            }
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_http))
    except Exception as e:
        import traceback
        print(f"Tarefa Background {log_entry_prefix}: Erro inesperado para produto {produto_id}: {traceback.format_exc()}")
        if db_produto and status_field_to_update:
            log_erro_inesperado_obj = list(db_produto.log_processamento) if db_produto.log_processamento else []
            log_erro_inesperado_obj.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"{log_entry_prefix}: Erro crítico inesperado - {str(e)}"})
            update_data_falha_critica = {
                status_field_to_update: models.StatusGeracaoIAEnum.FALHA,
                "log_processamento": log_erro_inesperado_obj
            }
            crud.update_produto(db, db_produto=db_produto, produto_update=schemas.ProdutoUpdate(**update_data_falha_critica))
    finally:
        print(f"Tarefa Background {log_entry_prefix}: Finalizando para produto ID: {produto_id}")
        db.close()


@router.post("/titulos/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED)
async def agendar_geracao_novos_titulos_openai(
    produto_id: int,
    background_tasks: BackgroundTasks, # Movido para antes dos parâmetros com default
    num_titulos: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    creditos_necessarios = settings.CREDITOS_CUSTO_GERACAO_TITULO if hasattr(settings, 'CREDITOS_CUSTO_GERACAO_TITULO') else 1
    
    if not await limit_service.verificar_creditos_disponiveis_geracao_ia(db, current_user.id, creditos_necessarios):
        log_limite = list(db_produto_check.log_processamento) if db_produto_check.log_processamento else []
        log_limite.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"IA Títulos: Falha ao agendar. Limite de uso atingido."})
        update_data_limite = {
            "status_titulo_ia": models.StatusGeracaoIAEnum.FALHA, 
            "log_processamento": log_limite
        }
        crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_limite))
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Créditos de IA insuficientes ({creditos_necessarios} necessários) para agendar geração de títulos."
        )

    log_pendente = list(db_produto_check.log_processamento) if db_produto_check.log_processamento else []
    log_pendente.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": "IA Títulos: Geração agendada. Status: PENDENTE."})
    update_data_pendente = {
        "status_titulo_ia": models.StatusGeracaoIAEnum.PENDENTE,
        "log_processamento": log_pendente
    }
    crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_pendente))
    
    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="titulo",
        # creditos_consumidos_pela_acao=creditos_necessarios, # Removido, o serviço de IA trata disso
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_titulos_com_openai,
        num_titulos=num_titulos
    )
    return {"message": f"Geração de títulos para o produto ID {produto_id} agendada."}


@router.post("/descricao/openai/{produto_id}", response_model=schemas.Msg, status_code=status.HTTP_202_ACCEPTED)
async def agendar_geracao_nova_descricao_openai(
    produto_id: int,
    background_tasks: BackgroundTasks, # Movido para antes dos parâmetros com default
    tamanho_palavras: int = Query(150, ge=50, le=500),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user)
):
    db_produto_check = crud.get_produto(db, produto_id=produto_id)
    if not db_produto_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Produto não encontrado")
    if db_produto_check.user_id != current_user.id and not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Não autorizado a gerar conteúdo para este produto")

    creditos_necessarios = settings.CREDITOS_CUSTO_GERACAO_DESCRICAO if hasattr(settings, 'CREDITOS_CUSTO_GERACAO_DESCRICAO') else 1
    if not await limit_service.verificar_creditos_disponiveis_geracao_ia(db, current_user.id, creditos_necessarios):
        log_limite = list(db_produto_check.log_processamento) if db_produto_check.log_processamento else []
        log_limite.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": f"IA Descrição: Falha ao agendar. Limite de uso atingido."})
        update_data_limite = {
            "status_descricao_ia": models.StatusGeracaoIAEnum.FALHA, 
            "log_processamento": log_limite
        }
        crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_limite))
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Créditos de IA insuficientes ({creditos_necessarios} necessários) para agendar geração de descrição."
        )
    
    log_pendente = list(db_produto_check.log_processamento) if db_produto_check.log_processamento else []
    log_pendente.append({"timestamp": datetime.utcnow().isoformat(), "actor": "system", "action": "IA Descrição: Geração agendada. Status: PENDENTE."})
    update_data_pendente = {
        "status_descricao_ia": models.StatusGeracaoIAEnum.PENDENTE,
        "log_processamento": log_pendente
    }
    crud.update_produto(db, db_produto=db_produto_check, produto_update=schemas.ProdutoUpdate(**update_data_pendente))

    background_tasks.add_task(
        _tarefa_processar_geracao_e_registrar_uso,
        db_session_factory=SessionLocal,
        user_id=current_user.id,
        produto_id=produto_id,
        tipo_geracao_principal="descricao",
        # creditos_consumidos_pela_acao=creditos_necessarios, # Removido
        funcao_geracao_ia_no_servico=ia_generation_service.gerar_descricao_com_openai,
        tamanho_palavras=tamanho_palavras
    )
    return {"message": f"Geração de descrição para o produto ID {produto_id} agendada."}


@router.post("/sugerir-atributos-gemini/{produto_id}", response_model=schemas.SugestoesAtributosResponse)
async def sugerir_atributos_para_produto_com_gemini(
    produto_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth_utils.get_current_active_user),
    # background_tasks: BackgroundTasks # Este endpoint permanece síncrono por enquanto
):
    """
    Obtém sugestões de valores para os atributos de um produto específico usando a API Gemini.
    As sugestões são baseadas nos AttributeTemplates definidos no ProductType do produto.
    Este endpoint é SÍNCRONO.
    """
    try:
        sugestoes_response = await ia_generation_service.sugerir_valores_atributos_com_gemini(
            db=db,
            produto_id=produto_id,
            user=current_user
        )
        return sugestoes_response
    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"Erro não tratado no endpoint sugerir_atributos_para_produto_com_gemini: {e}") 
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado ao processar a sugestão de atributos: {str(e)}"
        )
