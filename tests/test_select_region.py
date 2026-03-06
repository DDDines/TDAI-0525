import io
import subprocess
import sys
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
from Backend import schemas, models
from Backend.initial_data import InitialDataWorkflow
from Backend.core.config import settings
from Backend.infrastructure.repositories.user_repository import UserRepository

# ensure reportlab
try:
    from reportlab.pdfgen import canvas
except ImportError:  # pragma: no cover
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


class _TopLevelFunctionSurface:

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    def _create_pdf():
        buf = io.BytesIO()
        c = canvas.Canvas(buf)
        c.drawString(100, 750, "Hello")
        c.save()
        buf.seek(0)
        return buf.getvalue()

    def get_admin_headers():
        resp = client.post(
            "/api/v1/auth/token",
            data={"username": settings.FIRST_SUPERUSER_EMAIL, "password": settings.FIRST_SUPERUSER_PASSWORD},
        )
        assert resp.status_code == 200
        token = resp.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_selecionar_regiao_returns_empty_products():
        headers = get_admin_headers()
        pdf_bytes = _create_pdf()
        uploads = Path(__file__).resolve().parents[1] / "Backend" / "static" / "uploads" / "catalogs"
        uploads.mkdir(parents=True, exist_ok=True)
        stored = "test.pdf"
        (uploads / stored).write_bytes(pdf_bytes)
        with TestingSessionLocal() as db:
            admin = UserRepository(db).get_user_by_email(email=settings.FIRST_SUPERUSER_EMAIL)
            record = models.CatalogImportFile(
                user_id=admin.id,
                original_filename="test.pdf",
                stored_filename=stored,
                status="UPLOADED",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            file_id = record.id
    
        payload = {"file_id": file_id, "page": 1, "bbox": [90, 80, 200, 100]}
        resp = client.post("/api/v1/produtos/selecionar-regiao/", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["produtos"] == []

    def test_selecionar_regiao_file_not_found():
        headers = get_admin_headers()
        payload = {"file_id": 999, "page": 1, "bbox": [0, 0, 10, 10]}
        resp = client.post("/api/v1/produtos/selecionar-regiao/", json=payload, headers=headers)
        assert resp.status_code == 404

    def test_selecionar_regiao_accepts_bbox_norm_for_simple_pdf():
        headers = get_admin_headers()
        pdf_bytes = _create_pdf()
        uploads = Path(__file__).resolve().parents[1] / "Backend" / "static" / "uploads" / "catalogs"
        uploads.mkdir(parents=True, exist_ok=True)
        stored = "test_bbox_norm.pdf"
        (uploads / stored).write_bytes(pdf_bytes)
        with TestingSessionLocal() as db:
            admin = UserRepository(db).get_user_by_email(email=settings.FIRST_SUPERUSER_EMAIL)
            record = models.CatalogImportFile(
                user_id=admin.id,
                original_filename=stored,
                stored_filename=stored,
                status="UPLOADED",
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            file_id = record.id

        payload = {
            "file_id": file_id,
            "page": 1,
            "bbox": [0, 0, 10, 10],
            "bbox_norm": [0.05, 0.05, 1.02, 1.02],
        }
        resp = client.post("/api/v1/produtos/selecionar-regiao/", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data.get("produtos"), list)
        assert "preview_headers" in data
        assert "preview_rows" in data

override_get_db = _TopLevelFunctionSurface.override_get_db
_create_pdf = _TopLevelFunctionSurface._create_pdf
get_admin_headers = _TopLevelFunctionSurface.get_admin_headers
test_selecionar_regiao_returns_empty_products = _TopLevelFunctionSurface.test_selecionar_regiao_returns_empty_products
test_selecionar_regiao_file_not_found = _TopLevelFunctionSurface.test_selecionar_regiao_file_not_found
test_selecionar_regiao_accepts_bbox_norm_for_simple_pdf = _TopLevelFunctionSurface.test_selecionar_regiao_accepts_bbox_norm_for_simple_pdf


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)

initial_data_workflow = InitialDataWorkflow()

with TestingSessionLocal() as db:
    initial_data_workflow.create_initial_data(db)







