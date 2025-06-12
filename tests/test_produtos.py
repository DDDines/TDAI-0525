import pytest
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, crud_produtos, schemas
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

# setup initial data
with TestingSessionLocal() as db:
    crud.create_initial_data(db)
    admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
    for i in range(15):
        crud_produtos.create_produto(db, schemas.ProdutoCreate(nome_base=f"P{i}"), user_id=admin.id)


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
