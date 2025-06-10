from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, crud_fornecedores, schemas
from Backend.core.config import settings

# disable heavy startup events
app.router.on_startup.clear()

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    # create extra suppliers for pagination
    for i in range(15):
        crud_fornecedores.create_fornecedor(db, schemas.FornecedorCreate(nome=f"F{i}"), user_id=admin.id)


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
    resp = client.get("/api/v1/fornecedores", params={"skip": 0, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1

    resp = client.get("/api/v1/fornecedores", params={"skip": 10, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
