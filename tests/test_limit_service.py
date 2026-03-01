import pytest

pytest.importorskip("sqlalchemy")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend import models
from Backend.database import Base
from Backend.infrastructure.runtime_services.limit_runtime_service import (
    LimitRuntimeService,
)


@pytest.mark.asyncio
async def test_verificar_e_consumir_creditos_geracao_ia():
    limit_runtime_service = LimitRuntimeService()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()

    user = models.User(email="test@example.com", hashed_password="x", limite_geracao_ia=5)
    db.add(user)
    db.commit()
    db.refresh(user)

    for _ in range(4):
        db.add(
            models.RegistroUsoIA(
                user_id=user.id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            )
        )
    db.commit()

    assert await limit_runtime_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)

    db.add(
        models.RegistroUsoIA(
            user_id=user.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        )
    )
    db.commit()

    assert not await limit_runtime_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)
    db.close()


def test_verificar_limite_uso_retorna_saldo():
    limit_runtime_service = LimitRuntimeService()
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    session_factory = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = session_factory()

    plano = models.Plano(
        nome="Plano Teste",
        preco_mensal=0.0,
        limite_produtos=10,
        limite_enriquecimento_web=10,
        limite_geracao_ia=3,
        permite_api_externa=False,
        suporte_prioritario=False,
    )
    user = models.User(email="limit@example.com", hashed_password="x", limite_geracao_ia=3, plano=plano)
    db.add(plano)
    db.add(user)
    db.commit()
    db.refresh(user)

    db.add(
        models.RegistroUsoIA(
            user_id=user.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        )
    )
    db.commit()

    remaining = limit_runtime_service.verificar_limite_uso(db, user, "titulo")
    assert remaining == 3
    db.close()
