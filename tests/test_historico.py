from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app, create_new_user
from Backend.database import Base, get_db
from Backend import crud, crud_produtos, schemas, models
from Backend.core.config import settings

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

with TestingSessionLocal() as db:
    crud.create_initial_data(db)
    user_in = schemas.UserCreate(email="user2@example.com", password="secret", nome_completo="Normal User")
    normal_user = create_new_user(user_in=user_in, db=db)


def get_user_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={"username": "user2@example.com", "password": "secret"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_historico_created_on_product_crud():
    headers = get_user_headers()
    # create
    resp = client.post("/api/v1/produtos/", json={"nome_base": "HistProd"}, headers=headers)
    assert resp.status_code == 201
    produto_id = resp.json()["id"]
    # update
    resp = client.put(f"/api/v1/produtos/{produto_id}", json={"nome_base": "HistProd2"}, headers=headers)
    assert resp.status_code == 200
    # delete
    resp = client.delete(f"/api/v1/produtos/{produto_id}", headers=headers)
    assert resp.status_code == 200
    with TestingSessionLocal() as db:
        logs = db.query(models.RegistroHistorico).filter(models.RegistroHistorico.entity_id == produto_id).all()
        actions = [log.acao for log in logs]
        assert models.TipoAcaoSistemaEnum.CRIACAO in actions
        assert models.TipoAcaoSistemaEnum.ATUALIZACAO in actions
        assert models.TipoAcaoSistemaEnum.DELECAO in actions
