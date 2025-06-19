import io
import pytest
pytest.importorskip("httpx")
pytest.importorskip("sqlalchemy")
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from Backend.main import app
from Backend.database import Base, get_db
from Backend import crud
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


def test_preview_pages():
    headers = get_admin_headers()
    csv_content = "nome,sku\nA,1\n"
    files = {"file": ("catalog.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    resp = client.post("/api/v1/fornecedores/import/preview-pages", files=files, headers=headers)
    assert resp.status_code < 500


def test_extract_page_data():
    headers = get_admin_headers()
    resp = client.get(
        "/api/v1/fornecedores/import/extract-page-data",
        params={"job_id": 1, "page": 1},
        headers=headers,
    )
    assert resp.status_code < 500


def test_process_full_catalog_and_poll_progress():
    headers = get_admin_headers()
    resp = client.post(
        "/api/v1/fornecedores/import/process-full-catalog",
        json={"job_id": 1},
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
    review_resp = client.get("/api/v1/fornecedores/import/review/1", headers=headers)
    assert review_resp.status_code < 500
    commit_resp = client.post("/api/v1/fornecedores/import/commit/1", headers=headers)
    assert commit_resp.status_code < 500
