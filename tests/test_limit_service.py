import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.database import Base
from Backend import models
from Backend.services import limit_service

@pytest.mark.asyncio
async def test_verificar_e_consumir_creditos_geracao_ia():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    user = models.User(email="test@example.com", hashed_password="x", limite_geracao_ia=5)
    db.add(user)
    db.commit()
    db.refresh(user)

    for _ in range(4):
        db.add(models.RegistroUsoIA(user_id=user.id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_TITULO_PRODUTO))
    db.commit()

    assert await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)

    db.add(models.RegistroUsoIA(user_id=user.id, tipo_acao=models.TipoAcaoIAEnum.CRIACAO_TITULO_PRODUTO))
    db.commit()

    assert not await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)

    db.close()
