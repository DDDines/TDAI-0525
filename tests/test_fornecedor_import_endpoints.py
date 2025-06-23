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
from Backend import crud, models
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
        data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _upload_preview_pdf(headers):
    pdf_path = (
        Path(__file__).resolve().parents[1]
        / "Backend"
        / "tests"
        / "test_assets"
        / "scanned.pdf"
    )
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    with open(pdf_path, "rb") as f:
        files = {"file": ("scanned.pdf", f, "application/pdf")}
        resp = client.post(
            f"/api/v1/fornecedores/{fornec_id}/preview-pdf",
            files=files,
            headers=headers,
        )
def test_preview_pages():
    headers = get_admin_headers()
    csv_content = "nome,sku\nA,1\n"
    files = {"file": ("catalog.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/v1/fornecedores/1/preview-pdf", files=files, headers=headers)
    assert resp.status_code < 500
    data = resp.json()
    assert "import_file_id" in data
    return fornec_id, data["import_file_id"]


def test_preview_pdf():
    headers = get_admin_headers()
    _, import_file_id = _upload_preview_pdf(headers)
    assert isinstance(import_file_id, int)


def test_extract_page_data():
    headers = get_admin_headers()
    _, import_file_id = _upload_preview_pdf(headers)
    resp = client.get(
        "/api/v1/fornecedores/import/extract-page-data",
        params={"file_id": import_file_id, "page_number": 1},
        headers=headers,
    )
    assert resp.status_code < 500


def test_process_full_catalog_and_poll_progress():
    headers = get_admin_headers()
    fornec_id, import_file_id = _upload_preview_pdf(headers)
    with TestingSessionLocal() as db:
        pt_id = db.query(models.ProductType.id).first()[0]
    resp = client.post(
        "/api/v1/fornecedores/import/process-full-catalog",
        json={
            "file_id": import_file_id,
            "fornecedor_id": fornec_id,
            "tipo_produto_id": pt_id,
        },
        headers=headers,
    )
    assert resp.status_code < 500
    if resp.headers.get("content-type", "").startswith("application/json"):
        job = resp.json().get("job_id", 1)
    else:
        job = 1
    status_resp = client.get(f"/api/v1/fornecedores/import/status/{job}", headers=headers)
    assert status_resp.status_code < 500


def test_review_and_commit_flow():
    headers = get_admin_headers()
    fornec_id, import_file_id = _upload_preview_pdf(headers)
    with TestingSessionLocal() as db:
        pt_id = db.query(models.ProductType.id).first()[0]
    resp = client.post(
        "/api/v1/fornecedores/import/process-full-catalog",
        json={
            "file_id": import_file_id,
            "fornecedor_id": fornec_id,
            "tipo_produto_id": pt_id,
        },
        headers=headers,
    )
    if resp.headers.get("content-type", "").startswith("application/json"):
        job = resp.json().get("job_id", 1)
    else:
        job = 1

    review_resp = client.get(f"/api/v1/fornecedores/import/review/{job}", headers=headers)
    assert review_resp.status_code < 500
    commit_resp = client.post(f"/api/v1/fornecedores/import/commit/{job}", headers=headers)
    assert commit_resp.status_code < 500
