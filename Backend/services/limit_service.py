# tdai_project/Backend/services/limit_service.py
from fastapi import HTTPException, status # Removido Depends se não for usado diretamente
from sqlalchemy.orm import Session

# CORREÇÕES DOS IMPORTS:
# Como 'run_backend.py' coloca 'Backend/' no sys.path e define como CWD,
# 'crud' e 'models' (que estão em Backend/) são importados diretamente.
import crud #
import models #
# Se 'database.py' fosse necessário, seria: from database import get_db

def verificar_limite_uso(
    db: Session,
    user: models.User,
    tipo_geracao_principal: str # "descricao" ou "titulo"
) -> bool:
    """
    Verifica se o usuário atingiu o limite de uso para o tipo de geração no mês corrente,
    baseado no seu plano. Lança HTTPException se o limite foi atingido.
    """
    if not user.plano:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Funcionalidade não disponível. Usuário não possui um plano de assinatura ativo ou configurado."
        )

    limite_atingido = False
    mensagem_limite = "Limite mensal de uso atingido para este tipo de geração."
    limite_mensal = 0

    if tipo_geracao_principal == "descricao":
        limite_mensal = user.plano.max_descricoes_mes
        tipo_geracao_prefix_db = "descricao"
        
    elif tipo_geracao_principal == "titulo":
        limite_mensal = user.plano.max_titulos_mes
        tipo_geracao_prefix_db = "titulo"
    else:
        print(f"AVISO: Tentativa de verificar limite para tipo de geração desconhecido: {tipo_geracao_principal}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de geração '{tipo_geracao_principal}' não é válido para verificação de limite."
        )

    if limite_mensal is None or limite_mensal <= 0: # Considera 0 ou None como ilimitado
        return True

    usos_no_mes = crud.count_usos_ia_by_user_and_type_no_mes_corrente(
        db, user_id=user.id, tipo_geracao_prefix=tipo_geracao_prefix_db
    )
    
    if usos_no_mes >= limite_mensal:
        limite_atingido = True
        if tipo_geracao_principal == "descricao":
            mensagem_limite = f"Limite mensal de {limite_mensal} descrições atingido ({usos_no_mes} já utilizadas)."
        elif tipo_geracao_principal == "titulo":
            mensagem_limite = f"Limite mensal de {limite_mensal} títulos atingido ({usos_no_mes} já utilizados)."

    if limite_atingido:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=mensagem_limite
        )
    
    print(f"INFO: Verificação de limite para usuário {user.id} ({tipo_geracao_principal}): {usos_no_mes}/{limite_mensal} usos.")
    return True
