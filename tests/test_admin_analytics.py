import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import schemas, models
from Backend.crud_historico import get_historico_crud_workflow
from Backend.crud_produtos import get_produto_crud_workflow
from Backend.crud_registros_uso_ia import get_registro_uso_ia_crud_workflow
from Backend.crud_users import get_user_crud_workflow
from Backend.initial_data import get_initial_data_workflow
from Backend.core.config import settings

# disable heavy startup events
app.router.on_startup.clear()

initial_data_workflow = get_initial_data_workflow()
user_crud_workflow = get_user_crud_workflow()
produto_crud_workflow = get_produto_crud_workflow()
historico_crud_workflow = get_historico_crud_workflow()
uso_ia_crud_workflow = get_registro_uso_ia_crud_workflow()

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
    admin = user_crud_workflow.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    produto_crud_workflow.create_produto(db, schemas.ProdutoCreate(nome_base="Teste"), user_id=admin.id)
    uso_ia_crud_workflow.create_registro_uso_ia(
        db,
        schemas.RegistroUsoIACreate(user_id=admin.id, tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO),
    )
    for i in range(7):
        historico_crud_workflow.create_registro_historico(
            db,
            schemas.RegistroHistoricoCreate(
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
