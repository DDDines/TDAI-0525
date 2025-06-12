import io
from pathlib import Path
import pytest
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud, schemas, models
from Backend.core.config import settings

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
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
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
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    with TestingSessionLocal() as db:
        pt_id = db.query(models.ProductType.id).first()[0]

    resp = client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "produtos_criados" in data
    assert len(data["produtos_criados"]) == 1

    with TestingSessionLocal() as db:
        record = db.query(models.CatalogImportFile).get(file_id)
        assert record.status == "IMPORTED"
        assert record.fornecedor_id == fornec_id
        produtos = db.query(models.Produto).all()
        assert len(produtos) == 2  # 1 de exemplo + 1 importado
        assert produtos[-1].fornecedor_id == fornec_id


def test_finalize_processes_full_file():
    headers = get_admin_headers()
    # create a csv with 8 rows so preview will return only 5 but finalize should import all 8
    rows = [f"P{i},{i}" for i in range(8)]
    csv_content = "nome,sku\n" + "\n".join(rows)
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
        pt_id = db.query(models.ProductType.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    assert resp.status_code == 200
    file_id = resp.json()["file_id"]

    resp = client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["produtos_criados"]) == 8
    with TestingSessionLocal() as db:
        produtos = db.query(models.Produto).all()
        assert len(produtos) == 10  # 2 existentes + 8 novos
        assert all(p.fornecedor_id == fornec_id for p in produtos[2:])
