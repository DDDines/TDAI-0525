# Backend/routers/admin_analytics.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func 
from datetime import datetime, timedelta, timezone 

import crud 
import models 
import schemas 
from database import get_db 
from auth import get_current_active_user # Importa a dependência correta

router = APIRouter()

# Dependência para garantir que o usuário é admin
async def get_current_active_admin_user(current_user: models.User = Depends(get_current_active_user)):
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado: Requer privilégios de administrador.")
    return current_user

@router.get("/counts", response_model=schemas.TotalCounts, dependencies=[Depends(get_current_active_admin_user)])
async def get_total_counts_endpoint(db: Session = Depends(get_db)): 
    """
    Retorna contagens gerais do sistema (apenas para admin).
    """
    try:
        total_usuarios = db.query(func.count(models.User.id)).scalar() or 0
        total_produtos = db.query(func.count(models.Produto.id)).scalar() or 0
        total_fornecedores = db.query(func.count(models.Fornecedor.id)).scalar() or 0
        
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Usando o modelo correto: RegistroUsoIA
        total_geracoes_ia_mes = db.query(func.count(models.RegistroUsoIA.id)).filter(
            models.RegistroUsoIA.timestamp >= start_of_month
        ).scalar() or 0
        
        total_enriquecimentos_mes = db.query(func.count(models.RegistroUsoIA.id)).filter(
            models.RegistroUsoIA.timestamp >= start_of_month,
            models.RegistroUsoIA.tipo_geracao.ilike("%enriquecimento_web%") 
        ).scalar() or 0

        return schemas.TotalCounts(
            total_usuarios=total_usuarios,
            total_produtos=total_produtos,
            total_fornecedores=total_fornecedores,
            total_geracoes_ia_mes=total_geracoes_ia_mes,
            total_enriquecimentos_mes=total_enriquecimentos_mes,
        )
    except Exception as e:
        print(f"Erro ao buscar contagens de admin: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Erro interno ao buscar estatísticas.")


@router.get("/uso-ia/por-plano", response_model=List[schemas.UsoIAPorPlano], dependencies=[Depends(get_current_active_admin_user)])
async def get_uso_ia_por_plano_endpoint(db: Session = Depends(get_db)):
    """
    Retorna o uso de IA agrupado por plano no mês corrente (apenas para admin).
    """
    planos = crud.get_planos(db, skip=0, limit=1000) 
    resultado = []
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for plano in planos:
        count = db.query(func.count(models.RegistroUsoIA.id))\
                  .join(models.User, models.RegistroUsoIA.user_id == models.User.id)\
                  .filter(models.User.plano_id == plano.id, models.RegistroUsoIA.timestamp >= start_of_month)\
                  .scalar() or 0
        resultado.append(schemas.UsoIAPorPlano(
            plano_id=plano.id, # Adicionado plano_id
            nome_plano=plano.nome,
            total_geracoes_ia_no_mes=count
        ))
    return resultado

@router.get("/uso-ia/por-tipo", response_model=List[schemas.UsoIAPorTipo], dependencies=[Depends(get_current_active_admin_user)])
async def get_uso_ia_por_tipo_endpoint(db: Session = Depends(get_db)):
    """
    Retorna o uso de IA agrupado por tipo de geração no mês corrente (apenas para admin).
    """
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    query_result = db.query(
        models.RegistroUsoIA.tipo_geracao,
        func.count(models.RegistroUsoIA.id).label("total_no_mes") # Renomeado para corresponder ao schema
    ).filter(
        models.RegistroUsoIA.timestamp >= start_of_month
    ).group_by(
        models.RegistroUsoIA.tipo_geracao
    ).all()
    
    return [schemas.UsoIAPorTipo(tipo_geracao=row.tipo_geracao, total_no_mes=row.total_no_mes) for row in query_result]


@router.get("/user-activity/", response_model=List[schemas.UserActivity], dependencies=[Depends(get_current_active_admin_user)])
async def get_user_activity_endpoint(
    db: Session = Depends(get_db), 
    skip: int = Query(0, ge=0), 
    limit: int = Query(100, ge=1, le=200)
):
    """
    Retorna uma lista de atividades de usuários (apenas para admin).
    """
    users = crud.get_users(db, skip=skip, limit=limit) 
    activities = []
    now = datetime.now(timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    for user_model in users: # Renomeado para user_model para evitar conflito com user (se fosse parâmetro)
        total_produtos_user = db.query(func.count(models.Produto.id)).filter(models.Produto.user_id == user_model.id).scalar() or 0
        total_ia_mes_user = db.query(func.count(models.RegistroUsoIA.id)).filter(
            models.RegistroUsoIA.user_id == user_model.id,
            models.RegistroUsoIA.timestamp >= start_of_month
        ).scalar() or 0
        
        activities.append(schemas.UserActivity(
            user_id=user_model.id,
            email=user_model.email, # Adicionado o campo email ao schema UserActivity
            nome_completo=user_model.nome_completo,
            total_produtos=total_produtos_user,
            total_geracoes_ia_mes_corrente=total_ia_mes_user
        ))
    return activities