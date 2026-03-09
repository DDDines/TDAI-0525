"""Validate a real public catalog import and local LLM generation end-to-end."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Sequence

import httpx

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Backend.core.config import settings  # noqa: E402


DEFAULT_CATALOG_URL = "https://www.demdaco.com/content/pdfs/2019_PriceIncreaseList.pdf"
DEFAULT_SUPPLIER_NAME = "Smoke DEMDACO Catalog"
DEFAULT_SUPPLIER_SITE = "https://www.demdaco.com"
TERMINAL_IMPORT_STATUSES = {"IMPORTED", "DONE", "FAILED", "PARTIAL"}
SUCCESS_GENERATION_STATUS = "CONCLUIDO"
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d\s()./-]{7,}\d)")
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", re.IGNORECASE)
URL_PATTERN = re.compile(r"\b(?:https?://|www\.)\S+\b", re.IGNORECASE)
GENERIC_COMMERCE_PATTERNS = (
    re.compile(r"\bwhats(?:app)?\b", re.IGNORECASE),
    re.compile(r"\bcompra\s+online\b", re.IGNORECASE),
    re.compile(r"\bpolitica\s+de\b", re.IGNORECASE),
)


class CatalogValidationFailure(Exception):
    """Signal a deterministic validation failure for the real catalog workflow."""


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the real catalog validator."""
    parser = argparse.ArgumentParser(
        description="Validate a real public catalog import and local LLM generation end-to-end."
    )
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Backend base URL without /api/v1.")
    parser.add_argument("--api-prefix", default=settings.API_V1_STR, help="API prefix.")
    parser.add_argument("--admin-email", default=settings.ADMIN_EMAIL, help="Admin user email.")
    parser.add_argument("--admin-password", default=settings.ADMIN_PASSWORD, help="Admin user password.")
    parser.add_argument("--catalog-url", default=DEFAULT_CATALOG_URL, help="Public catalog URL to download.")
    parser.add_argument(
        "--catalog-path",
        default=str(PROJECT_ROOT / ".runtime" / "real-catalog-validation.pdf"),
        help="Local path used to cache the downloaded catalog.",
    )
    parser.add_argument("--supplier-name", default=DEFAULT_SUPPLIER_NAME, help="Disposable supplier base name.")
    parser.add_argument("--supplier-site-url", default=DEFAULT_SUPPLIER_SITE, help="Disposable supplier site URL.")
    parser.add_argument(
        "--product-type-id",
        type=int,
        default=None,
        help="Explicit product type ID. Falls back to a type without attribute templates when available.",
    )
    parser.add_argument("--start-page", type=int, default=1, help="Preview/import start page.")
    parser.add_argument(
        "--sample-products",
        type=int,
        default=3,
        help="How many imported products to push through title+description generation.",
    )
    parser.add_argument(
        "--import-timeout-seconds",
        type=int,
        default=240,
        help="Maximum wait time for catalog import to reach a terminal status.",
    )
    parser.add_argument(
        "--generation-timeout-seconds",
        type=int,
        default=180,
        help="Maximum wait time for title/description generation to reach terminal status per product.",
    )
    parser.add_argument(
        "--report-path",
        default=str(PROJECT_ROOT / ".runtime" / "real-catalog-validation-report.json"),
        help="Path to write the JSON validation report.",
    )
    parser.add_argument(
        "--keep-import",
        action="store_true",
        help="Keep the disposable supplier and imported products instead of deleting them.",
    )
    return parser.parse_args()


def pick_product_type_id(product_types: Sequence[Dict[str, Any]], requested_id: int | None) -> int:
    """Resolve the most convenient product type for smoke imports."""
    if requested_id is not None:
        return requested_id

    for item in product_types:
        if not item.get("attribute_templates"):
            return int(item["id"])
    if product_types:
        return int(product_types[0]["id"])
    raise CatalogValidationFailure("Nenhum product type disponivel para o smoke de catalogo real.")


def extract_created_items(result_summary: Any) -> List[Dict[str, Any]]:
    """Normalize result_summary payloads to the created product list."""
    if isinstance(result_summary, dict):
        created = result_summary.get("created")
        if isinstance(created, list):
            return [item for item in created if isinstance(item, dict)]
    return []


def validate_generated_product_snapshot(snapshot: Dict[str, Any]) -> List[str]:
    """Apply deterministic checks to a generated product snapshot."""
    issues: List[str] = []
    titles = snapshot.get("titulos") or []
    description = str(snapshot.get("descricao") or "").strip()

    if snapshot.get("status_titulo_ia") != SUCCESS_GENERATION_STATUS:
        issues.append("status de titulo nao concluiu")
    if snapshot.get("status_descricao_ia") != SUCCESS_GENERATION_STATUS:
        issues.append("status de descricao nao concluiu")
    if len([title for title in titles if str(title or "").strip()]) < 1:
        issues.append("nenhum titulo sugerido foi salvo")
    if len([title for title in titles if str(title or "").strip()]) < 3:
        issues.append("menos de 3 titulos sugeridos")
    if len(description.split()) < 20:
        issues.append("descricao curta demais")
    if PHONE_PATTERN.search(description):
        issues.append("descricao com telefone suspeito")
    if EMAIL_PATTERN.search(description):
        issues.append("descricao com email")
    if URL_PATTERN.search(description):
        issues.append("descricao com url")
    for pattern in GENERIC_COMMERCE_PATTERNS:
        if pattern.search(description):
            issues.append(f"descricao com boilerplate comercial: {pattern.pattern}")

    return issues


class RealCatalogPipelineValidator:
    """Drive the real catalog import workflow through the public API."""

    def __init__(self, args: argparse.Namespace) -> None:
        self._args = args
        self._base_url = args.base_url.rstrip("/")
        self._api_prefix = args.api_prefix.rstrip("/")
        self._report_path = Path(args.report_path)
        self._report_path.parent.mkdir(parents=True, exist_ok=True)
        self._catalog_path = Path(args.catalog_path)
        self._catalog_path.parent.mkdir(parents=True, exist_ok=True)
        self._client = httpx.Client(timeout=60.0)
        self._token: str | None = None
        self._supplier_id: int | None = None
        self._imported_product_ids: List[int] = []
        self._import_file_id: int | None = None

    def _api_url(self, path: str) -> str:
        return f"{self._base_url}{self._api_prefix}{path}"

    def _headers(self) -> Dict[str, str]:
        if not self._token:
            raise CatalogValidationFailure("Token de autenticacao ausente.")
        return {"Authorization": f"Bearer {self._token}"}

    def ensure_backend_health(self) -> Dict[str, Any]:
        response = self._client.get(f"{self._base_url}/health")
        response.raise_for_status()
        return response.json()

    def login(self) -> None:
        response = self._client.post(
            self._api_url("/auth/token"),
            data={"username": self._args.admin_email, "password": self._args.admin_password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        response.raise_for_status()
        token = str(response.json().get("access_token") or "").strip()
        if not token:
            raise CatalogValidationFailure("Falha ao autenticar no backend local.")
        self._token = token

    def fetch_product_types(self) -> List[Dict[str, Any]]:
        response = self._client.get(
            self._api_url("/product-types/"),
            headers=self._headers(),
            params={"skip": 0, "limit": 100},
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise CatalogValidationFailure("A listagem de product types retornou payload invalido.")
        return [item for item in payload if isinstance(item, dict)]

    def download_catalog(self) -> Path:
        if self._catalog_path.exists() and self._catalog_path.stat().st_size > 0:
            return self._catalog_path

        with httpx.stream("GET", self._args.catalog_url, timeout=120.0, follow_redirects=True) as response:
            response.raise_for_status()
            with self._catalog_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    if chunk:
                        handle.write(chunk)
        return self._catalog_path

    def create_supplier(self) -> Dict[str, Any]:
        payload = {
            "nome": f"{self._args.supplier_name} {int(time.time())}",
            "site_url": self._args.supplier_site_url,
        }
        response = self._client.post(self._api_url("/fornecedores/"), headers=self._headers(), json=payload)
        response.raise_for_status()
        supplier = response.json()
        self._supplier_id = int(supplier["id"])
        return supplier

    def preview_catalog(self, *, supplier_id: int, catalog_path: Path) -> Dict[str, Any]:
        with catalog_path.open("rb") as handle:
            files = {"file": (catalog_path.name, handle, "application/pdf")}
            data = {
                "fornecedor_id": str(supplier_id),
                "start_page": str(self._args.start_page),
                "page_count": "3",
                "dpi": "72",
            }
            response = self._client.post(
                self._api_url("/produtos/importar-catalogo-preview/"),
                headers=self._headers(),
                data=data,
                files=files,
            )
        response.raise_for_status()
        payload = response.json()
        file_id = payload.get("file_id")
        if not file_id:
            raise CatalogValidationFailure("Preview do catalogo nao retornou file_id.")
        self._import_file_id = int(file_id)
        return payload

    def start_import(self, *, file_id: int, supplier_id: int, product_type_id: int) -> Dict[str, Any]:
        response = self._client.post(
            self._api_url(f"/produtos/importar-catalogo-finalizar/{file_id}/"),
            headers=self._headers(),
            json={
                "product_type_id": product_type_id,
                "fornecedor_id": supplier_id,
                "mapping": None,
                "pages": None,
                "region": None,
                "extraction_mode": "ocr",
            },
        )
        response.raise_for_status()
        return response.json()

    def wait_for_import(self, *, file_id: int) -> Dict[str, Any]:
        deadline = time.time() + self._args.import_timeout_seconds
        while time.time() < deadline:
            response = self._client.get(
                self._api_url(f"/produtos/importar-catalogo-status/{file_id}/"),
                headers=self._headers(),
            )
            response.raise_for_status()
            payload = response.json()
            if str(payload.get("status") or "").upper() in TERMINAL_IMPORT_STATUSES:
                return payload
            time.sleep(2)
        raise CatalogValidationFailure(
            f"Importacao do catalogo nao atingiu status terminal em {self._args.import_timeout_seconds}s."
        )

    def fetch_imported_products(self, *, supplier_id: int, limit: int) -> List[Dict[str, Any]]:
        page_size = min(max(limit, 1), 200)
        skip = 0
        results: List[Dict[str, Any]] = []
        while len(results) < limit:
            response = self._client.get(
                self._api_url("/produtos/"),
                headers=self._headers(),
                params={
                    "fornecedor_id": supplier_id,
                    "limit": min(page_size, limit - len(results)),
                    "skip": skip,
                    "sort_by": "id",
                    "sort_order": "asc",
                },
            )
            response.raise_for_status()
            payload = response.json()
            items = payload.get("items") or []
            if not isinstance(items, list):
                raise CatalogValidationFailure("Listagem de produtos importados retornou payload invalido.")
            batch = [item for item in items if isinstance(item, dict)]
            results.extend(batch)
            if len(batch) < min(page_size, limit - len(results) + len(batch)):
                break
            skip += len(batch)
        return results

    def trigger_generation(self, product_id: int) -> None:
        for route in (f"/geracao/titulos/openai/{product_id}", f"/geracao/descricao/openai/{product_id}"):
            response = self._client.post(self._api_url(route), headers=self._headers())
            response.raise_for_status()

    def wait_for_generated_product(self, product_id: int) -> Dict[str, Any]:
        deadline = time.time() + self._args.generation_timeout_seconds
        while time.time() < deadline:
            response = self._client.get(self._api_url(f"/produtos/{product_id}"), headers=self._headers())
            response.raise_for_status()
            payload = response.json()
            if (
                str(payload.get("status_titulo_ia") or "").upper() == SUCCESS_GENERATION_STATUS
                and str(payload.get("status_descricao_ia") or "").upper() == SUCCESS_GENERATION_STATUS
            ):
                return payload
            time.sleep(2)
        raise CatalogValidationFailure(
            f"Produto {product_id} nao concluiu geracao em {self._args.generation_timeout_seconds}s."
        )

    def cleanup(self) -> None:
        if self._args.keep_import or not self._supplier_id:
            return
        try:
            products = self.fetch_imported_products(supplier_id=self._supplier_id, limit=1000)
        except Exception:
            products = []

        product_ids = [int(item["id"]) for item in products if isinstance(item.get("id"), int)]
        for index in range(0, len(product_ids), 100):
            chunk = product_ids[index : index + 100]
            if not chunk:
                continue
            try:
                self._client.post(
                    self._api_url("/produtos/batch-delete/"),
                    headers=self._headers(),
                    json=chunk,
                ).raise_for_status()
            except Exception:
                pass

        if self._import_file_id:
            try:
                self._client.delete(
                    self._api_url(f"/produtos/catalog-import-files/{self._import_file_id}/"),
                    headers=self._headers(),
                ).raise_for_status()
            except Exception:
                pass

        try:
            self._client.delete(self._api_url(f"/fornecedores/{self._supplier_id}"), headers=self._headers()).raise_for_status()
        except Exception:
            pass

    def close(self) -> None:
        self._client.close()

    def run(self) -> Dict[str, Any]:
        self.ensure_backend_health()
        self.login()
        product_types = self.fetch_product_types()
        product_type_id = pick_product_type_id(product_types, self._args.product_type_id)
        catalog_path = self.download_catalog()
        supplier = self.create_supplier()
        preview = self.preview_catalog(supplier_id=int(supplier["id"]), catalog_path=catalog_path)
        import_start = self.start_import(
            file_id=int(preview["file_id"]),
            supplier_id=int(supplier["id"]),
            product_type_id=product_type_id,
        )
        import_status = self.wait_for_import(file_id=int(preview["file_id"]))
        created_items = extract_created_items(import_status.get("result_summary"))
        imported_products = self.fetch_imported_products(
            supplier_id=int(supplier["id"]),
            limit=max(self._args.sample_products, len(created_items) or self._args.sample_products),
        )
        self._imported_product_ids = [int(item["id"]) for item in imported_products if isinstance(item.get("id"), int)]

        if not imported_products:
            raise CatalogValidationFailure("Nenhum produto foi criado a partir do catalogo real.")

        snapshots: List[Dict[str, Any]] = []
        for product in imported_products[: self._args.sample_products]:
            product_id = int(product["id"])
            self.trigger_generation(product_id)
            generated = self.wait_for_generated_product(product_id)
            snapshot = {
                "id": product_id,
                "nome_base": generated.get("nome_base"),
                "status_titulo_ia": generated.get("status_titulo_ia"),
                "status_descricao_ia": generated.get("status_descricao_ia"),
                "titulos": list((generated.get("dados_brutos_web") or {}).get("titulos_sugeridos_gerados") or []),
                "descricao": generated.get("descricao_chat_api"),
                "issues": [],
            }
            snapshot["issues"] = validate_generated_product_snapshot(snapshot)
            snapshots.append(snapshot)

        report = {
            "ok": all(not item["issues"] for item in snapshots),
            "catalog_url": self._args.catalog_url,
            "catalog_path": str(catalog_path),
            "supplier": supplier,
            "product_type_id": product_type_id,
            "preview": {
                "file_id": preview.get("file_id"),
                "num_pages": preview.get("num_pages"),
                "table_pages": preview.get("table_pages"),
            },
            "import_start": import_start,
            "import_status": {
                "status": import_status.get("status"),
                "total_pages": import_status.get("total_pages"),
                "pages_processed": import_status.get("pages_processed"),
                "created_count": len(created_items),
            },
            "sample_products": snapshots,
        }

        self._report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

        if not report["ok"]:
            raise CatalogValidationFailure(
                "Validacao do catalogo real concluiu com issues: "
                + "; ".join(
                    f"produto {item['id']}: {', '.join(item['issues'])}"
                    for item in snapshots
                    if item["issues"]
                )
            )

        return report


def main() -> int:
    args = parse_args()
    validator = RealCatalogPipelineValidator(args)
    try:
        report = validator.run()
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except CatalogValidationFailure as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    finally:
        try:
            validator.cleanup()
        finally:
            validator.close()


if __name__ == "__main__":
    raise SystemExit(main())
