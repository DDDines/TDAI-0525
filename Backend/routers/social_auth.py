# tdai_project/Backend/routers/admin_analytics.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, extract, and_ 
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone

# CORREÇÕES DOS IMPORTS:
# Como 'run_backend.py' coloca 'Backend/' no sys.path e define como CWD,
# podemos tratar módulos em 'Backend/' como se fossem de nível superior.
import crud #
import models #
import Project.Backend.schemas as schemas #
from database import get_db #

# '.' refere-se ao diretório atual ('routers')
from .auth_utils import get_current_active_superuser #

router = APIRouter(
    prefix="/admin/analytics",
    tags=["Admin Analytics"],
    dependencies=[Depends(get_current_active_superuser)]
)

@router.get("/counts", response_model=schemas.TotalCounts)
async def get_total_counts(db: Session = Depends(get_db)):
    total_users = db.query(func.count(models.User.id)).scalar() or 0
    total_produtos = db.query(func.count(models.Produto.id)).scalar() or 0
    total_fornecedores = db.query(func.count(models.Fornecedor.id)).scalar() or 0
    total_usos_ia = db.query(func.count(models.UsoIA.id)).scalar() or 0
    
    return schemas.TotalCounts(
        total_users=total_users,
        total_produtos=total_produtos,
        total_fornecedores=total_fornecedores,
        total_usos_ia=total_usos_ia
    )

@router.get("/uso-ia/por-plano", response_model=List[schemas.UsoIAPorPlano])
async def get_uso_ia_por_plano(
    db: Session = Depends(get_db),
    data_inicio: Optional[datetime] = Query(None, description="Data de início (YYYY-MM-DD ou ISO format) para filtrar usos da IA"),
    data_fim: Optional[datetime] = Query(None, description="Data de fim (YYYY-MM-DD ou ISO format) para filtrar usos da IA")
):
    query = (
        db.query(
            models.Plano.name.label("plano_nome"),
            func.count(models.UsoIA.id).label("total_usos")
        )
        .select_from(models.UsoIA)
        .join(models.User, models.UsoIA.user_id == models.User.id)
        .outerjoin(models.Plano, models.User.plano_id == models.Plano.id)
    )
    
    if data_inicio:
        query = query.filter(models.UsoIA.timestamp >= data_inicio)
    if data_fim:
        query = query.filter(models.UsoIA.timestamp < (data_fim + timedelta(days=1)))
        
    results = query.group_by(models.Plano.name).all()
    
    return [schemas.UsoIAPorPlano(plano_nome=(nome if nome else "Sem Plano"), total_usos=contagem) for nome, contagem in results]

@router.get("/uso-ia/por-tipo", response_model=List[schemas.UsoIAPorTipo])
async def get_uso_ia_por_tipo(
    db: Session = Depends(get_db),
    data_inicio: Optional[datetime] = Query(None),
    data_fim: Optional[datetime] = Query(None)
):
    query = db.query(models.UsoIA.tipo_geracao, func.count(models.UsoIA.id).label("total_usos"))
    
    if data_inicio:
        query = query.filter(models.UsoIA.timestamp >= data_inicio)
    if data_fim:
        query = query.filter(models.UsoIA.timestamp < (data_fim + timedelta(days=1)))
        
    results = query.group_by(models.UsoIA.tipo_geracao).order_by(models.UsoIA.tipo_geracao).all()
    
    return [schemas.UsoIAPorTipo(tipo_geracao=tipo, total_usos=contagem) for tipo, contagem in results]

@router.get("/user-activity/", response_model=List[schemas.UserActivity])
async def get_user_activity_summary(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    min_usos_mes: Optional[int] = Query(None, ge=0, description="[Admin] Filtrar usuários com no mínimo X usos da IA no mês corrente")
):
    hoje_utc = datetime.now(timezone.utc)
    inicio_mes_corrente_utc = hoje_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    subquery_usos_mes = (
        db.query(
            models.UsoIA.user_id.label("sq_user_id"),
            func.count(models.UsoIA.id).label("usos_no_mes")
        )
        .filter(models.UsoIA.timestamp >= inicio_mes_corrente_utc)
        .group_by(models.UsoIA.user_id)
        .subquery('usos_mes_subquery')
    )

    query = (
        db.query(
            models.User.id,
            models.User.email,
            models.Plano.name.label("plano_nome"),
            func.coalesce(subquery_usos_mes.c.usos_no_mes, 0).label("usos_ia_mes_corrente_calc")
        )
        .outerjoin(models.Plano, models.User.plano_id == models.Plano.id)
        .outerjoin(subquery_usos_mes, models.User.id == subquery_usos_mes.c.sq_user_id)
        .order_by(models.User.id)
    )

    if min_usos_mes is not None:
        query = query.filter(func.coalesce(subquery_usos_mes.c.usos_no_mes, 0) >= min_usos_mes)

    results = query.offset(skip).limit(limit).all()
    
    user_activities = []
    for user_id_res, email_res, plano_nome_res, usos_ia_mes_res in results:
        user_activities.append(
            schemas.UserActivity(
                user_id=user_id_res,
                user_email=email_res,
                plano_nome=plano_nome_res if plano_nome_res else "Sem Plano",
                usos_ia_mes_corrente=usos_ia_mes_res
            )
        )
    return user_activities