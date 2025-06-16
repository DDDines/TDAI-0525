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
from Backend import crud, models
from Backend.core.config import settings

try:
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
except ImportError:  # pragma: no cover - install at runtime
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak, Paragraph
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet

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


def _create_pdf_with_table():
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph("Page 1", styles["Normal"]), PageBreak()]
    table = Table([["A", "B"], ["1", "2"]])
    table.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 1, colors.black)]))
    story.append(table)
    doc.build(story)
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


def test_extrair_pagina_unica_returns_data():
    headers = get_admin_headers()
    pdf_bytes = _create_pdf_with_table()
    uploads = Path(__file__).resolve().parents[1] / "Backend" / "static" / "uploads" / "catalogs"
    uploads.mkdir(parents=True, exist_ok=True)
    stored = "single.pdf"
    (uploads / stored).write_bytes(pdf_bytes)
    with TestingSessionLocal() as db:
        admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
        record = models.CatalogImportFile(
            user_id=admin.id,
            original_filename="single.pdf",
            stored_filename=stored,
            status="UPLOADED",
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        file_id = record.id

    payload = {"file_id": file_id, "page_number": 2}
    resp = client.post("/api/v1/produtos/extrair-pagina-unica/", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["image"].startswith("data:image/png;base64,")
    assert "A" in data["text"] or "B" in data["text"]
    assert data["table"] == [["A", "B"], ["1", "2"]]


def test_extrair_pagina_unica_file_not_found():
    headers = get_admin_headers()
    payload = {"file_id": 9999, "page_number": 1}
    resp = client.post("/api/v1/produtos/extrair-pagina-unica/", json=payload, headers=headers)
    assert resp.status_code == 404
