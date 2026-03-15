from __future__ import annotations

import pytest
from fastapi import HTTPException

from Backend.application.services.fornecedor_logo_service import FornecedorLogoService
from Backend.routers import fornecedores as fornecedores_module


def test_fornecedor_logo_service_prefers_logo_like_images_over_other_candidates():
    html = """
    <html>
      <head>
        <meta property="og:image" content="/hero.jpg" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>
        <img class="header-logo brand" src="/assets/logo.svg" alt="Logo oficial" />
      </body>
    </html>
    """

    resolved = FornecedorLogoService._resolve_from_html(
        html=html,
        page_url="https://empresa.example/home",
    )

    assert resolved is not None
    assert resolved.url == "https://empresa.example/assets/logo.svg"
    assert resolved.source == "img-logo"


def test_fornecedor_logo_service_prefers_css_logo_over_meta_and_favicon(monkeypatch):
    html = """
    <html>
      <head>
        <link rel="stylesheet" href="/assets/site.css" />
        <meta property="og:image" content="/hero.jpg" />
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>
        <h1><a class="logo ir" href="/">Empresa</a></h1>
      </body>
    </html>
    """

    class _Response:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class _Client:
        def get(self, url: str):
            assert url == "https://empresa.example/assets/site.css"
            return _Response("h1 a.logo { background: url(images/logo.png) no-repeat; }")

    resolved = FornecedorLogoService._resolve_from_html(
        html=html,
        page_url="https://empresa.example/home",
        client=_Client(),
    )

    assert resolved is not None
    assert resolved.url == "https://empresa.example/assets/images/logo.png"
    assert resolved.source == "css-logo"


def test_fornecedor_logo_service_falls_back_to_favicon_when_no_signal_exists(monkeypatch):
    monkeypatch.setattr(
        FornecedorLogoService,
        "_fetch_site",
        classmethod(
            lambda cls, *, client, site_url: (site_url, "<html><body>sem logo</body></html>")
        ),
    )

    resolved = FornecedorLogoService.resolve_logo("empresa.example")

    assert resolved["logo_url"] == "https://empresa.example/favicon.ico"
    assert resolved["resolved_site_url"] == "https://empresa.example"
    assert resolved["source"] == "favicon-default"


def test_fornecedores_endpoint_handler_resolve_logo_maps_runtime_failures(monkeypatch):
    monkeypatch.setattr(
        fornecedores_module.FornecedorLogoService,
        "resolve_logo",
        lambda site_url: (_ for _ in ()).throw(RuntimeError(f"falha em {site_url}")),
    )

    with pytest.raises(HTTPException) as exc:
        fornecedores_module._EndpointHandlers.resolve_supplier_logo(
            request=fornecedores_module.schemas.FornecedorLogoResolveRequest(
                site_url="empresa.example"
            ),
            current_user=object(),
        )

    assert exc.value.status_code == 502
    assert exc.value.detail == "falha em empresa.example"
