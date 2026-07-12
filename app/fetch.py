from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Final
from urllib.parse import urlparse, urlunparse

import requests
from flask import current_app


DEFAULT_HEADERS: Final[dict[str, str]] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36 CompanyLensBot/3.0"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}
HTML_HINTS: Final[tuple[str, ...]] = ("text/html", "application/xhtml+xml", "application/xml", "text/xml")


class ScraperError(RuntimeError):
    """Raised for scraper failures that should surface as application errors."""


class UnsafeTargetError(ScraperError):
    """Raised when a URL resolves to an internal or otherwise unsafe host."""


@dataclass(slots=True)
class FetchResult:
    url: str
    final_url: str
    status_code: int
    content_type: str
    text: str


class ScraperClient:
    def __init__(
        self,
        *,
        timeout: int,
        max_page_bytes: int,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.timeout = timeout
        self.max_page_bytes = max_page_bytes
        self.headers = headers or DEFAULT_HEADERS.copy()
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=1)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    @classmethod
    def from_current_app(cls) -> "ScraperClient":
        return cls(
            timeout=current_app.config["REQUEST_TIMEOUT"],
            max_page_bytes=current_app.config["MAX_PAGE_BYTES"],
        )

    def normalize_url(self, raw_url: str) -> str:
        candidate = (raw_url or "").strip()
        if not candidate:
            raise ScraperError("A company URL is required.")

        if not candidate.startswith(("http://", "https://")):
            candidate = f"https://{candidate}"

        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"}:
            raise ScraperError("Only http and https URLs are allowed.")
        if not parsed.netloc:
            raise ScraperError("Invalid URL. Please provide a full website hostname.")

        normalized = urlunparse((parsed.scheme, parsed.netloc, parsed.path or "/", "", "", ""))
        self.validate_public_target(normalized)
        return normalized

    def validate_public_target(self, url: str) -> None:
        parsed = urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            raise UnsafeTargetError("URL is missing a valid hostname.")

        if hostname.lower() in {"localhost", "0.0.0.0"}:
            raise UnsafeTargetError("Local and internal targets are blocked.")

        try:
            records = socket.getaddrinfo(hostname, None)
        except socket.gaierror as exc:
            raise ScraperError("Unable to resolve the target hostname.") from exc

        for record in records:
            ip = record[4][0]
            try:
                ip_obj = ipaddress.ip_address(ip)
            except ValueError:
                continue

            if any(
                (
                    ip_obj.is_private,
                    ip_obj.is_loopback,
                    ip_obj.is_multicast,
                    ip_obj.is_reserved,
                    ip_obj.is_link_local,
                    ip_obj.is_unspecified,
                )
            ):
                raise UnsafeTargetError("Private, loopback, or otherwise unsafe targets are blocked.")

    def fetch_html(self, url: str) -> FetchResult:
        safe_url = self.normalize_url(url)

        try:
            response = self.session.get(safe_url, timeout=self.timeout, allow_redirects=True, stream=True)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise ScraperError(f"Failed to fetch {safe_url}: {exc}") from exc

        self.validate_public_target(response.url)
        content_type = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if content_type and content_type not in HTML_HINTS:
            raise ScraperError(f"Expected HTML content but received '{content_type or 'unknown'}'.")

        body = self._read_limited_body(response)
        return FetchResult(
            url=safe_url,
            final_url=response.url,
            status_code=response.status_code,
            content_type=content_type,
            text=body,
        )

    def _read_limited_body(self, response: requests.Response) -> str:
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > self.max_page_bytes:
            raise ScraperError("Target page is too large to process safely.")

        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192, decode_unicode=False):
            if not chunk:
                continue
            total += len(chunk)
            if total > self.max_page_bytes:
                raise ScraperError("Target page exceeded the maximum allowed size.")
            chunks.append(chunk)

        raw = b"".join(chunks)
        encoding = response.encoding or response.apparent_encoding or "utf-8"
        return raw.decode(encoding, errors="replace")
