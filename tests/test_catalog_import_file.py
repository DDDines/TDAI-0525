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
from Backend import crud, crud_produtos, schemas, models
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


def _create_pdf_region():
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    for i in range(2):
        c.drawString(100, 750, f"Nome: P{i}")
        c.drawString(100, 730, f"Marca: M{i}")
        if i < 1:
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

    result_resp = client.get(
        f"/api/v1/produtos/importar-catalogo-result/{file_id}/",
        headers=headers,
    )
    assert result_resp.status_code == 200
    result = result_resp.json()
    assert len(result["created"]) >= 1


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


def test_import_updates_existing_product():
    headers = get_admin_headers()
    csv_content = "nome,sku\nNovo,999\n"
    files = {"file": ("cat.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with TestingSessionLocal() as db:
        admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
        existing = crud_produtos.create_produto(
            db, schemas.ProdutoCreate(nome_base="Antigo", sku="999"), user_id=admin.id
        )
        fornec_id = db.query(models.Fornecedor.id).first()[0]
        pt_id = db.query(models.ProductType.id).first()[0]

    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    file_id = resp.json()["file_id"]

    resp = client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    assert resp.status_code == 202

    result_resp = client.get(
        f"/api/v1/produtos/importar-catalogo-result/{file_id}/",
        headers=headers,
    )
    assert result_resp.status_code == 200
    data = result_resp.json()
    assert any(item["id"] == existing.id for item in data["updated"])

    with TestingSessionLocal() as db:
        refreshed = db.query(models.Produto).get(existing.id)
        assert refreshed.nome_base == "Novo"


def test_list_catalog_files_pagination():
    headers = get_admin_headers()
    with TestingSessionLocal() as db:
        admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
        fornec_id = db.query(models.Fornecedor.id).first()[0]
        for i in range(15):
            db.add(
                models.CatalogImportFile(
                    user_id=admin.id,
                    fornecedor_id=fornec_id,
                    original_filename=f"file{i}.csv",
                    stored_filename=f"stored{i}.csv",
                )
            )
        db.commit()

    resp = client.get(
        "/api/v1/produtos/catalog-import-files/",
        params={"skip": 10, "limit": 10},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["page"] == 2
    assert data["limit"] == 10


def test_list_catalog_files_filter_by_fornecedor():
    headers = get_admin_headers()
    with TestingSessionLocal() as db:
        admin = crud.get_user_by_email(db, settings.FIRST_SUPERUSER_EMAIL)
        fornec_base = db.query(models.Fornecedor).first()
        new_forn = crud.create_fornecedor(db, schemas.FornecedorCreate(nome="F2"), user_id=admin.id)
        new_forn_id = new_forn.id
        db.add(
            models.CatalogImportFile(
                user_id=admin.id,
                fornecedor_id=new_forn_id,
                original_filename="f.csv",
                stored_filename="s.csv",
            )
        )
        db.add(
            models.CatalogImportFile(
                user_id=admin.id,
                fornecedor_id=fornec_base.id,
                original_filename="b.csv",
                stored_filename="b.csv",
            )
        )
        db.commit()

    resp = client.get(
        "/api/v1/produtos/catalog-import-files/",
        params={"fornecedor_id": new_forn_id},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert all(item["fornecedor_id"] == new_forn_id for item in data["items"])
def test_status_endpoint_returns_progress():
    headers = get_admin_headers()
    csv_content = "nome,sku\nC,3\n"
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
    status_resp = client.get(
        f"/api/v1/produtos/importar-catalogo-status/{file_id}/",
        headers=headers,
    )
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "UPLOADED"
    assert data["pages_processed"] == 0


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
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert data["status"] == "IMPORTED"
    assert data["pages_processed"] == data["total_pages"]
    assert data["total_pages"] >= 1

def test_preview_pdf_respects_page_count():
    headers = get_admin_headers()
    pdf_bytes = _create_pdf(3)
    files = {"file": ("catalogo.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id, "page_count": 2},
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
    assert all("page" in img for img in data["preview_images"])


def test_region_selection_endpoint():
    headers = get_admin_headers()
    pdf_bytes = _create_pdf_region()
    files = {"file": ("catalogo.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
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
    region_resp = client.post(
        "/api/v1/produtos/selecionar-regiao/",
        headers=headers,
        json={"file_id": file_id, "page": 1, "bbox": [90, 720, 200, 760]},
    )
    assert region_resp.status_code == 200
    data = region_resp.json()
    assert len(data["produtos"]) == 2
    assert data["produtos"][0]["nome_base"] == "P0"
    assert data["produtos"][1]["marca"] == "M1"


def test_delete_catalog_import_file_removes_file_and_record():
    headers = get_admin_headers()
    csv_content = "nome,sku\nX,10\n"
    files = {"file": ("cat.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    file_id = resp.json()["file_id"]
    with TestingSessionLocal() as db:
        record = db.query(models.CatalogImportFile).get(file_id)
        stored = record.stored_filename
    uploads = (
        Path(__file__).resolve().parents[1]
        / "Backend"
        / "static"
        / "uploads"
        / "catalogs"
    )
    file_path = uploads / stored
    assert file_path.exists()

    del_resp = client.delete(
        f"/api/v1/produtos/catalog-import-files/{file_id}/",
        headers=headers,
    )
    assert del_resp.status_code == 200
    assert not file_path.exists()
    with TestingSessionLocal() as db:
        assert db.query(models.CatalogImportFile).get(file_id) is None


def test_reprocess_catalog_import_file_creates_again():
    headers = get_admin_headers()
    csv_content = "nome,sku\nY,11\n"
    files = {"file": ("cat.csv", io.BytesIO(csv_content.encode()), "text/csv")}
    with TestingSessionLocal() as db:
        fornec_id = db.query(models.Fornecedor.id).first()[0]
        pt_id = db.query(models.ProductType.id).first()[0]

    resp = client.post(
        "/api/v1/produtos/importar-catalogo-preview/",
        files=files,
        data={"fornecedor_id": fornec_id},
        headers=headers,
    )
    file_id = resp.json()["file_id"]

    client.post(
        f"/api/v1/produtos/importar-catalogo-finalizar/{file_id}/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    with TestingSessionLocal() as db:
        initial_count = db.query(models.Produto).count()

    resp = client.post(
        f"/api/v1/produtos/catalog-import-files/{file_id}/reprocess/",
        headers=headers,
        json={"product_type_id": pt_id, "fornecedor_id": fornec_id},
    )
    assert resp.status_code == 202
    with TestingSessionLocal() as db:
        assert db.query(models.Produto).count() >= initial_count
        record = db.query(models.CatalogImportFile).get(file_id)
        assert record.status == "IMPORTED"
