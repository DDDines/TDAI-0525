import pytest
pytest.importorskip("sqlalchemy")
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.database import Base
from Backend import models
from Backend.services import limit_service

@pytest.mark.asyncio
async def test_verificar_e_consumir_creditos_geracao_ia():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = Session()

    user = models.User(email="test@example.com", hashed_password="x", limite_geracao_ia=5)
    db.add(user)
    db.commit()
    db.refresh(user)

    for _ in range(4):
        db.add(models.RegistroUsoIA(user_id=user.id, tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO))
    db.commit()

    assert await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)

    db.add(models.RegistroUsoIA(user_id=user.id, tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO))
    db.commit()

    assert not await limit_service.verificar_e_consumir_creditos_geracao_ia(db, user.id, 1)

    db.close()

import sys
from pathlib import Path
import importlib.util
import types

import pytest
from fastapi import HTTPException, status

ROOT = Path(__file__).resolve().parents[1]
module_path = ROOT / "Backend" / "services" / "limit_service.py"

# --- Prepare stub modules so limit_service can be imported without dependencies ---
stub_sqlalchemy = types.ModuleType("sqlalchemy")
orm_stub = types.ModuleType("sqlalchemy.orm")
stub_sqlalchemy.orm = orm_stub
orm_stub.Session = object

stub_models = types.ModuleType("models")
stub_models.User = object

stub_crud = types.ModuleType("crud")
stub_crud.count_usos_ia_by_user_and_type_no_mes_corrente = lambda *a, **kw: 0

sys.modules.setdefault("sqlalchemy", stub_sqlalchemy)
sys.modules.setdefault("sqlalchemy.orm", orm_stub)
sys.modules.setdefault("models", stub_models)
sys.modules.setdefault("crud", stub_crud)

spec = importlib.util.spec_from_file_location("limit_service", module_path)
limit_service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(limit_service)

class DummyPlan:
    def __init__(self, limite_geracao_ia=5):
        self.limite_geracao_ia = limite_geracao_ia

class DummyUser:
    def __init__(self, id=1, plano=None):
        self.id = id
        self.plano = plano


def test_verificar_limite_uso_abaixo_limite(monkeypatch):
    user = DummyUser(plano=DummyPlan(limite_geracao_ia=5))

    def mock_count(db, user_id, tipo_geracao_prefix):
        return 3
    monkeypatch.setattr(limit_service.crud, "count_usos_ia_by_user_and_type_no_mes_corrente", mock_count)

    remaining = limit_service.verificar_limite_uso(None, user, "descricao")
    assert remaining == 2


def test_verificar_limite_uso_acima_limite(monkeypatch):
    user = DummyUser(plano=DummyPlan(limite_geracao_ia=5))

    def mock_count(db, user_id, tipo_geracao_prefix):
        return 5
    monkeypatch.setattr(limit_service.crud, "count_usos_ia_by_user_and_type_no_mes_corrente", mock_count)

    with pytest.raises(HTTPException) as exc:
        limit_service.verificar_limite_uso(None, user, "descricao")
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert "descrições" in exc.value.detail

