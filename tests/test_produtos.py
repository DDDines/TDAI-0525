import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import schemas
from Backend.crud_produtos import get_produto_crud_workflow
from Backend.crud_users import get_user_crud_workflow
from Backend.initial_data import get_initial_data_workflow
from Backend.core.config import settings

# disable heavy startup events
app.router.on_startup.clear()

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = get_initial_data_workflow()
user_crud_workflow = get_user_crud_workflow()
produto_crud_workflow = get_produto_crud_workflow()

# setup initial data
with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)
    admin = user_crud_workflow.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    for i in range(15):
        produto_crud_workflow.create_produto(
            db,
            schemas.ProdutoCreate(nome_base=f"P{i}"),
            user_id=admin.id,
        )


def get_admin_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_pagination_returns_1_based_page():
    headers = get_admin_headers()
    resp = client.get("/api/v1/produtos", params={"skip": 0, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1

    # intermediate skip values should still report page 1
    resp = client.get("/api/v1/produtos", params={"skip": 5, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1

    resp = client.get("/api/v1/produtos", params={"skip": 10, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
