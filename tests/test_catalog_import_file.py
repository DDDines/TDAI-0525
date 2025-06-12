import io
from pathlib import Path
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, schemas, models
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


def get_admin_headers():
    resp = client.post(
        "/api/v1/auth/token",
        data={
            "username": settings.FIRST_SUPERUSER_EMAIL,
            "password": settings.FIRST_SUPERUSER_PASSWORD,
        },
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_preview_saves_file_and_record():
    headers = get_admin_headers()
    csv_content = "nome,sku\nA,1\n"
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/", files=files, headers=headers
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "file_id" in data
    file_id = data["file_id"]

    with TestingSessionLocal() as db:
        record = db.query(models.CatalogImportFile).get(file_id)
        assert record is not None
        assert record.status == "UPLOADED"
        path = (
            Path(__file__).resolve().parents[1]
            / "Backend"
            / "static"
            / "uploads"
            / "catalogs"
            / record.stored_filename
        )
        assert path.exists()


def test_finalize_updates_status():
    headers = get_admin_headers()
    csv_content = "nome,sku\nB,2\n"
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/", files=files, headers=headers
    )
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    with TestingSessionLocal() as db:
        pt_id = db.query(models.ProductType.id).first()[0]

    resp = client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "produtos_criados" in data
    assert len(data["produtos_criados"]) == 1

    with TestingSessionLocal() as db:
        record = db.query(models.CatalogImportFile).get(file_id)
        assert record.status == "IMPORTED"
        produtos = db.query(models.Produto).all()
        assert len(produtos) == 1
