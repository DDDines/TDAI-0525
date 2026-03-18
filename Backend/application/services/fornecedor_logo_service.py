"""Resolucao de logo de fornecedor a partir do site informado."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class _FornecedorLogoHelpers:
    """Static helper utilities for URL and text validation in logo resolution."""

    @staticmethod
    def _normalize_site_url(site_url: str) -> list[str]:
        """Normalize a supplier site URL into a list of candidate absolute URLs to try."""
        raw = str(site_url or "").strip()
        if not raw:
            raise ValueError("Site do fornecedor nao informado.")

        if raw.startswith(("http://", "https://")):
            return [raw]

        host = raw.lstrip("/")
        return [f"https://{host}", f"http://{host}"]

    @staticmethod
    def _valid_absolute_url(url: str) -> bool:
        """Return True if the URL is an absolute HTTP/HTTPS URL with a netloc component."""
        parsed = urlparse(str(url or "").strip())
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _looks_like_logo_text(value: Optional[str]) -> bool:
        """Return True if the text contains common logo indicator keywords."""
        if not value:
            return False
        normalized = value.strip().lower()
        indicators = ("logo", "brand", "marca", "header-logo", "site-logo")
        return any(token in normalized for token in indicators)


_normalize_site_url = _FornecedorLogoHelpers._normalize_site_url
_valid_absolute_url = _FornecedorLogoHelpers._valid_absolute_url
_looks_like_logo_text = _FornecedorLogoHelpers._looks_like_logo_text


@dataclass(frozen=True)
class _LogoCandidate:
    """Represent a resolved logo URL candidate with its provenance and relevance score."""

    url: str
    source: str
    score: int


class FornecedorLogoService:
    """Resolve logo candidates from a supplier homepage."""

    REQUEST_TIMEOUT = 8.0
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    )
    CSS_RULE_PATTERN = re.compile(r"(?P<selectors>[^{}]+)\{(?P<body>[^{}]+)\}", re.IGNORECASE | re.DOTALL)
    CSS_BACKGROUND_URL_PATTERN = re.compile(
        r"background(?:-image)?\s*:\s*[^;{}]*url\((?P<url>[^)]+)\)",
        re.IGNORECASE,
    )

    @classmethod
    def resolve_logo(cls, site_url: str) -> dict:
        """Resolve the best logo candidate for a supplier website."""
        attempted_urls = _normalize_site_url(site_url)
        last_error: Exception | None = None

        with httpx.Client(
            timeout=cls.REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": cls.USER_AGENT},
        ) as client:
            for candidate_url in attempted_urls:
                try:
                    resolved_site_url, response_text = cls._fetch_site(
                        client=client,
                        site_url=candidate_url,
                    )
                    logo = cls._resolve_from_html(
                        html=response_text,
                        page_url=resolved_site_url,
                        client=client,
                    )
                    if logo:
                        return {
                            "logo_url": logo.url,
                            "resolved_site_url": resolved_site_url,
                            "source": logo.source,
                        }
                    return {
                        "logo_url": cls._build_favicon_url(resolved_site_url),
                        "resolved_site_url": resolved_site_url,
                        "source": "favicon-default",
                    }
                except Exception as exc:
                    last_error = exc

        if last_error is not None:
            raise RuntimeError(
                "Nao foi possivel acessar o site informado para localizar o logo."
            ) from last_error
        raise RuntimeError("Nao foi possivel localizar o logo do fornecedor.")

    @classmethod
    def _fetch_site(cls, *, client: httpx.Client, site_url: str) -> tuple[str, str]:
        """Fetch the site HTML and return the resolved URL together with the response text."""
        response = client.get(site_url)
        response.raise_for_status()
        return str(response.url), response.text

    @classmethod
    def _resolve_from_html(
        cls,
        *,
        html: str,
        page_url: str,
        client: httpx.Client | None = None,
    ) -> Optional[_LogoCandidate]:
        """Parse HTML and return the highest-scored logo candidate found, or None."""
        soup = BeautifulSoup(html or "", "html.parser")
        candidates = list(cls._iter_candidates(soup=soup, page_url=page_url, client=client))
        if not candidates:
            return None
        candidates.sort(
            key=lambda item: (item.score, cls._candidate_tiebreak(item)),
            reverse=True,
        )
        return candidates[0]

    @classmethod
    def _iter_candidates(
        cls,
        *,
        soup: BeautifulSoup,
        page_url: str,
        client: httpx.Client | None = None,
    ) -> Iterable[_LogoCandidate]:
        """Yield deduplicated logo candidates from all supported HTML sources."""
        seen: set[str] = set()

        def push(url: Optional[str], source: str, score: int):
            """Resolve and yield a deduplicated logo candidate if the URL is valid and unseen."""
            resolved = cls._resolve_candidate_url(page_url=page_url, raw_url=url)
            if not resolved or resolved in seen:
                return
            seen.add(resolved)
            yield _LogoCandidate(url=resolved, source=source, score=score)

        for img in soup.find_all("img"):
            attributes = " ".join(
                filter(
                    None,
                    [
                        img.get("alt"),
                        img.get("class") and " ".join(img.get("class")),
                        img.get("id"),
                        img.get("src"),
                    ],
                )
            )
            if _looks_like_logo_text(attributes):
                yield from push(img.get("src"), "img-logo", 100)

        for element in soup.find_all(True):
            element_descriptor = " ".join(
                filter(
                    None,
                    [
                        element.get("id"),
                        element.get("class") and " ".join(element.get("class")),
                        element.name,
                    ],
                )
            )
            if not _looks_like_logo_text(element_descriptor):
                continue
            style = element.get("style") or ""
            inline_match = cls.CSS_BACKGROUND_URL_PATTERN.search(style)
            if inline_match:
                yield from push(
                    cls._clean_css_url(inline_match.group("url")),
                    "inline-logo",
                    108,
                )

        if client is not None:
            for css_candidate in cls._iter_stylesheet_logo_candidates(
                soup=soup,
                page_url=page_url,
                client=client,
            ):
                if css_candidate.url not in seen:
                    seen.add(css_candidate.url)
                    yield css_candidate

        meta_selectors = (
            ("property", "og:image"),
            ("name", "og:image"),
            ("name", "twitter:image"),
            ("property", "twitter:image"),
        )
        for attr_name, attr_value in meta_selectors:
            tag = soup.find("meta", attrs={attr_name: attr_value})
            if tag:
                yield from push(tag.get("content"), "meta-image", 78)

        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel") or []).lower()
            href = link.get("href")
            if "apple-touch-icon" in rel:
                yield from push(href, "link-icon", 52)
                continue
            if any(token in rel for token in ("icon", "shortcut icon", "mask-icon")):
                score = 28
                if href and "favicon" not in href.lower() and not href.lower().endswith(".ico"):
                    score = 38
                yield from push(href, "link-icon", score)

        yield _LogoCandidate(
            url=cls._build_favicon_url(page_url),
            source="favicon-default",
            score=12,
        )

    @classmethod
    def _iter_stylesheet_logo_candidates(
        cls,
        *,
        soup: BeautifulSoup,
        page_url: str,
        client: httpx.Client,
    ) -> Iterable[_LogoCandidate]:
        """Yield logo candidates found in same-host stylesheets via CSS background-image rules."""
        seen_stylesheets: set[str] = set()
        page_host = urlparse(page_url).netloc.lower()
        stylesheet_urls: list[str] = []

        for link in soup.find_all("link"):
            rel = " ".join(link.get("rel") or []).lower()
            if "stylesheet" not in rel:
                continue
            href = cls._resolve_candidate_url(page_url=page_url, raw_url=link.get("href"))
            if not href or href in seen_stylesheets:
                continue
            if urlparse(href).netloc.lower() != page_host:
                continue
            seen_stylesheets.add(href)
            stylesheet_urls.append(href)

        for stylesheet_url in stylesheet_urls[:4]:
            try:
                response = client.get(stylesheet_url)
                response.raise_for_status()
            except Exception:
                continue

            for match in cls.CSS_RULE_PATTERN.finditer(response.text or ""):
                selectors = " ".join(match.group("selectors").split())
                if not cls._looks_like_logo_selector(selectors):
                    continue
                body = match.group("body") or ""
                for url_match in cls.CSS_BACKGROUND_URL_PATTERN.finditer(body):
                    raw_url = cls._clean_css_url(url_match.group("url"))
                    resolved = cls._resolve_candidate_url(
                        page_url=stylesheet_url,
                        raw_url=raw_url,
                    )
                    if not resolved:
                        continue
                    score = 112
                    lowered_selectors = selectors.lower()
                    if "header" in lowered_selectors or "site-logo" in lowered_selectors:
                        score += 4
                    yield _LogoCandidate(url=resolved, source="css-logo", score=score)

    @staticmethod
    def _clean_css_url(value: str) -> str:
        """Strip quotes and whitespace from a CSS url() value."""
        return str(value or "").strip().strip("\"'")

    @staticmethod
    def _looks_like_logo_selector(selector: str) -> bool:
        """Return True if the CSS selector string contains a logo-related keyword."""
        normalized = str(selector or "").strip().lower()
        if not normalized:
            return False
        indicators = ("logo", "brand", "marca", "header-logo", "site-logo")
        return any(token in normalized for token in indicators)

    @staticmethod
    def _candidate_tiebreak(candidate: _LogoCandidate) -> int:
        """Return a secondary sort key preferring SVG/PNG and penalising favicon/ICO URLs."""
        lowered = candidate.url.lower()
        if lowered.endswith(".svg"):
            return 12
        if lowered.endswith(".png"):
            return 10
        if lowered.endswith((".webp", ".jpg", ".jpeg")):
            return 8
        if lowered.endswith(".ico") or "favicon" in lowered:
            return -20
        return 0

    @staticmethod
    def _resolve_candidate_url(*, page_url: str, raw_url: Optional[str]) -> Optional[str]:
        """Resolve a potentially relative URL against page_url and validate the result."""
        if not raw_url:
            return None
        value = str(raw_url).strip()
        if not value or value.startswith("data:"):
            return None
        resolved = urljoin(page_url, value)
        return resolved if _valid_absolute_url(resolved) else None

    @staticmethod
    def _build_favicon_url(page_url: str) -> str:
        """Build the conventional /favicon.ico URL for the given page origin."""
        parsed = urlparse(page_url)
        return f"{parsed.scheme}://{parsed.netloc}/favicon.ico"
