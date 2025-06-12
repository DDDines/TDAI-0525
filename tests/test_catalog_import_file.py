import io
from pathlib import Path
import pytest
import subprocess
import sys
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

# ensure reportlab for PDF generation
try:
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover - install at runtime
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.pdfgen import canvas

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


def _create_pdf(pages: int = 1):
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(pages):
        c.drawString(100, 750, f"Page {i+1}")
        if i < pages - 1:
            c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


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
        assert record.fornecedor_id == fornec_id
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
    assert resp.status_code == 202
    assert resp.json()["status"] == "PROCESSING"
    assert resp.json()["status"] == "PROCESSING"

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
    assert resp.status_code == 202
    with TestingSessionLocal() as db:
        produtos = db.query(models.Produto).all()
        assert len(produtos) == 10  # 2 existentes + 8 novos
        assert all(p.fornecedor_id == fornec_id for p in produtos[2:])


def test_status_endpoint_returns_progress():
    headers = get_admin_headers()
    csv_content = "nome,sku\nC,3\n"
    files = {"file": ("catalogo.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
def test_preview_pdf_respects_page_count():
    headers = get_admin_headers()
    pdf_bytes = _create_pdf(3)
    files = {"file": ("catalogo.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/?page_count=2",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    file_id = resp.json()["file_id"]
    status_resp = client.get(
        f"/api/v1/produtos/importar-catalogo-status/{file_id}/",
        headers=headers,
    )
    assert status_resp.status_code == 200
    assert status_resp.json()["status"] == "UPLOADED"
    with TestingSessionLocal() as db:
        pt_id = db.query(models.ProductType.id).first()[0]
    client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    status_resp = client.get(
        f"/api/v1/produtos/importar-catalogo-status/{file_id}/",
        headers=headers,
    )
    assert status_resp.json()["status"] == "IMPORTED"
    assert resp.status_code == 200
    data = resp.json()
    assert "preview_images" in data
    assert len(data["preview_images"]) == 2
