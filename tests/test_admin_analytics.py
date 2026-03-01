import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import schemas, models
from Backend.initial_data import get_initial_data_workflow
from Backend.core.config import settings
from Backend.infrastructure.repositories.historico_repository import HistoricoRepository
from Backend.infrastructure.repositories.product_repository import ProductRepository
from Backend.infrastructure.repositories.registro_uso_ia_repository import (
    RegistroUsoIARepository,
)
from Backend.infrastructure.repositories.user_repository import UserRepository

# disable heavy startup events
app.router.on_startup.clear()

initial_data_workflow = get_initial_data_workflow()

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)

# override dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

# setup initial data
with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    admin = UserRepository(db).get_user_by_email(email=settings.FIRST_SUPERUSER_EMAIL)
    ProductRepository(db).create_produto(
        produto=schemas.ProdutoCreate(nome_base="Teste"),
        user_id=admin.id,
    )
    RegistroUsoIARepository(db).create_registro_uso_ia(
        registro_uso=schemas.RegistroUsoIACreate(
            user_id=admin.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        ),
    )
    for i in range(7):
        HistoricoRepository(db).create_registro_historico(
            registro_in=schemas.RegistroHistoricoCreate(
                user_id=admin.id,
                entidade="Teste",
                acao=models.TipoAcaoSistemaEnum.CRIACAO,
                entity_id=i,
            ),
        )

def get_auth_headers():
    resp = client.post("/api/v1/auth/token", data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD})
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_product_status_counts_endpoint():
    headers = get_auth_headers()
    resp = client.get("/api/v1/admin/analytics/product-status-counts", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_recent_activities_endpoint():
    headers = get_auth_headers()
    resp = client.get("/api/v1/admin/analytics/recent-activities", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_recent_historico_endpoint_limit():
    headers = get_auth_headers()
    resp = client.get("/api/v1/admin/analytics/recent-historico?limit=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 5
