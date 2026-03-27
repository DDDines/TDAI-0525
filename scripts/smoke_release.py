"""Smoke checks for a freshly deployed CommerceFolio release."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class SmokeFailure(RuntimeError):
    """Raised when a release smoke check fails."""


def _read_json(
    url: str,
    *,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    data: Optional[bytes] = None,
    timeout: float = 30.0,
) -> Any:
    request = Request(url=url, method=method, headers=headers or {}, data=data)
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        payload = response.read().decode(charset)
        return json.loads(payload)


def _check_health(base_url: str, timeout: float) -> None:
    health = _read_json(f"{base_url}/health", timeout=timeout)
    if health.get("status") != "ok":
      raise SmokeFailure(f"Health endpoint returned unexpected payload: {health!r}")


def _check_root(base_url: str, timeout: float) -> None:
    payload = _read_json(base_url, timeout=timeout)
    if "message" not in payload:
        raise SmokeFailure(f"Root endpoint returned unexpected payload: {payload!r}")


def _fetch_access_token(
    base_url: str,
    api_prefix: str,
    *,
    email: str,
    password: str,
    timeout: float,
) -> str:
    body = urlencode(
        {
            "username": email,
            "password": password,
        }
    ).encode("utf-8")
    payload = _read_json(
        f"{base_url}{api_prefix}/auth/token",
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data=body,
        timeout=timeout,
    )
    token = payload.get("access_token")
    if not token:
        raise SmokeFailure("Auth token endpoint did not return access_token.")
    return token


def _check_authenticated_endpoints(
    base_url: str,
    api_prefix: str,
    *,
    token: str,
    timeout: float,
) -> None:
    headers = {"Authorization": f"Bearer {token}"}
    produtos = _read_json(
        f"{base_url}{api_prefix}/produtos/?skip=0&limit=1",
        headers=headers,
        timeout=timeout,
    )
    if not isinstance(produtos, dict) or "items" not in produtos:
        raise SmokeFailure(f"Produtos endpoint returned unexpected payload: {produtos!r}")

    product_types = _read_json(
        f"{base_url}{api_prefix}/product-types/?skip=0&limit=1",
        headers=headers,
        timeout=timeout,
    )
    if not isinstance(product_types, list):
        raise SmokeFailure(
            f"Product types endpoint returned unexpected payload: {product_types!r}"
        )


def run_smoke(
    *,
    base_url: str,
    api_prefix: str,
    timeout: float,
    email: Optional[str],
    password: Optional[str],
) -> None:
    normalized_base_url = base_url.rstrip("/")
    normalized_api_prefix = "/" + api_prefix.strip("/")

    _check_health(normalized_base_url, timeout)
    _check_root(normalized_base_url, timeout)

    if email and password:
        token = _fetch_access_token(
            normalized_base_url,
            normalized_api_prefix,
            email=email,
            password=password,
            timeout=timeout,
        )
        _check_authenticated_endpoints(
            normalized_base_url,
            normalized_api_prefix,
            token=token,
            timeout=timeout,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run smoke checks against a CommerceFolio release.")
    parser.add_argument("--base-url", required=True, help="Base URL of the deployed API.")
    parser.add_argument("--api-prefix", default="/api/v1", help="API prefix used by the backend.")
    parser.add_argument("--timeout", type=float, default=30.0, help="Timeout per request in seconds.")
    parser.add_argument("--email", default="", help="Optional admin email for authenticated smoke checks.")
    parser.add_argument(
        "--password",
        default="",
        help="Optional admin password for authenticated smoke checks.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        run_smoke(
            base_url=args.base_url,
            api_prefix=args.api_prefix,
            timeout=args.timeout,
            email=args.email or None,
            password=args.password or None,
        )
    except (HTTPError, URLError, TimeoutError, SmokeFailure, json.JSONDecodeError) as exc:
        print(f"Smoke check failed: {exc}", file=sys.stderr)
        return 1
    print("Smoke check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
