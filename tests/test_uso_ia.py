import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, crud_users, crud_produtos, schemas, models
from Backend.main import create_new_user
from Backend.core.config import settings

# disable heavy startup events
app.router.on_startup.clear()

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    crud.create_initial_data(db)
    user_in = schemas.UserCreate(
        email="user@example.com",
        password="secret",
        nome_completo="Normal User",
    )
    normal_user = create_new_user(user_in=user_in, db=db)
    produto = crud_produtos.create_produto(db, schemas.ProdutoCreate(nome_base="TesteProd"), user_id=normal_user.id)
    crud.create_registro_uso_ia(
        db,
        schemas.RegistroUsoIACreate(
            user_id=normal_user.id,
            produto_id=produto.id,
            tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
        ),
    )
    # create extra registros for pagination tests
    for i in range(15):
        crud.create_registro_uso_ia(
            db,
            schemas.RegistroUsoIACreate(
                user_id=normal_user.id,
                produto_id=produto.id,
                tipo_acao=models.TipoAcaoEnum.CRIACAO_TITULO_PRODUTO,
            ),
        )


def get_admin_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def get_user_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "user@example.com", "password": "secret"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_admin_can_view_usos_ia_of_other_user_product():
    headers = get_admin_headers()
    # get product id created earlier
    with TestingSessionLocal() as db:
        produto = db.query(models.Produto).filter(models.Produto.nome_base == "TesteProd").first()
    resp = client.get(f"/api/v1/uso-ia/por-produto/{produto.id}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["produto_id"] == produto.id


def test_product_creation_creates_uso_ia_record():
    headers = get_user_headers()
    resp = client.post(
        "/api/v1/produtos/",
        json={"nome_base": "Novo Produto"},
        headers=headers,
    )
    assert resp.status_code == 201
    produto_id = resp.json()["id"]
    with TestingSessionLocal() as db:
        registros = (
            db.query(models.RegistroUsoIA)
            .filter(
                models.RegistroUsoIA.produto_id == produto_id,
                models.RegistroUsoIA.tipo_acao == models.TipoAcaoEnum.CRIACAO_PRODUTO,
            )
            .all()
        )
        assert len(registros) == 1


def test_pagination_returns_1_based_page_for_uso_ia():
    headers = get_user_headers()
    resp = client.get("/api/v1/uso-ia", params={"skip": 0, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1

    resp = client.get("/api/v1/uso-ia", params={"skip": 10, "limit": 10}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2


def test_first_page_number_for_uso_ia():
    headers = get_user_headers()
    resp = client.get("/api/v1/uso-ia", params={"skip": 0, "limit": 5}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 1
