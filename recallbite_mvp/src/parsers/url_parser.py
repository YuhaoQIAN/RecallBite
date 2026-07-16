"""Fetch and parse public URLs into structured material."""

from __future__ import annotations

import ipaddress
import re
from urllib.parse import urlparse

from src.parsers.text_parser import MaterialDocument


MAX_URL_CONTENT_LENGTH = 50_000
REQUEST_TIMEOUT = 15

# IPv4 private/link-local ranges (CIDR not supported by ipaddress for partial,
# so we match by prefix patterns)
_PRIVATE_IPV4_PATTERNS = [
    re.compile(r"^127\.", re.I),
    re.compile(r"^10\.", re.I),
    re.compile(r"^172\.(1[6-9]|2[0-9]|3[01])\.", re.I),
    re.compile(r"^192\.168\.", re.I),
    re.compile(r"^169\.254\.", re.I),
    re.compile(r"^0\.", re.I),
    re.compile(r"^255\.", re.I),
]


def _is_private_or_localhost(hostname: str) -> bool:
    """Block localhost, private IPs, and link-local addresses."""
    h = hostname.lower()
    if h in {"localhost", "::1", "0:0:0:0:0:0:0:1"}:
        return True
    # IPv6 loopback / private prefixes
    if h.startswith("fc") or h.startswith("fd") or h == "::1":
        return True
    # Try to parse as IPv4
    try:
        ipaddress.IPv4Address(h)
        # It's a valid IPv4 address; block if it matches private patterns
        for pat in _PRIVATE_IPV4_PATTERNS:
            if pat.match(h):
                return True
        # Also block any raw IP for safety in public URL fetching
        return True
    except ValueError:
        pass
    # Hostname patterns that look like internal/local
    if ".local" in h or ".internal" in h or ".lan" in h or ".intranet" in h:
        return True
    return False


def _is_safe_url(url: str) -> tuple[bool, str]:
    """Return (is_safe, reason) blocking internal/private URLs."""
    parsed = urlparse(url.strip())
    hostname = parsed.hostname or ""
    if _is_private_or_localhost(hostname):
        return False, "Blocked: local or private addresses are not allowed."
    # No file://, ftp://, etc.
    if parsed.scheme not in {"http", "https"}:
        return False, "Blocked: only http and https URLs are allowed."
    return True, ""


def is_valid_url(url: str) -> bool:
    """Check if a string looks like a valid HTTP/HTTPS URL."""
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def parse_url(url: str) -> MaterialDocument:
    """Fetch a public URL and extract the main article text."""
    if not is_valid_url(url):
        raise ValueError("Invalid URL. Must start with http:// or https://")

    safe, reason = _is_safe_url(url)
    if not safe:
        raise ValueError(reason)

    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise ImportError(
            "URL fetching requires 'requests' and 'beautifulsoup4'. "
            "Install: pip install requests beautifulsoup4"
        ) from exc

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    }

    try:
        response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except requests.exceptions.Timeout:
        raise ValueError("Request timed out. The page may be slow or unreachable.")
    except requests.exceptions.HTTPError as exc:
        if exc.response.status_code == 403:
            raise ValueError("Access forbidden (403). The site may block automated requests.")
        if exc.response.status_code == 404:
            raise ValueError("Page not found (404).")
        raise ValueError(f"HTTP error {exc.response.status_code}")
    except requests.exceptions.RequestException as exc:
        raise ValueError(f"Could not fetch URL: {exc}")

    # Content-Type safety check
    content_type = response.headers.get("Content-Type", "").lower()
    if content_type:
        # Reject non-HTML binary or explicit file downloads
        if any(
            bad in content_type
            for bad in [
                "application/octet-stream",
                "application/zip",
                "application/pdf",
                "application/msword",
                "application/vnd.openxmlformats",
                "audio/",
                "video/",
                "image/",
                "executable",
                "binary",
            ]
        ):
            raise ValueError(
                "Blocked: URL points to a non-webpage file type. "
                "Only HTML pages are allowed."
            )

    soup = BeautifulSoup(response.text, "html.parser")

    # Remove non-content elements
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Try to find main content
    main_text = ""
    for selector in ["main", "article", '[role="main"]', ".content", ".post", ".entry"]:
        elem = soup.select_one(selector)
        if elem:
            main_text = elem.get_text(separator="\n", strip=True)
            break

    if not main_text:
        main_text = soup.get_text(separator="\n", strip=True)

    # Limit length
    if len(main_text) > MAX_URL_CONTENT_LENGTH:
        main_text = main_text[:MAX_URL_CONTENT_LENGTH] + "\n\n[Content truncated due to length]"

    if not main_text.strip():
        raise ValueError("Could not extract readable content from the page.")

    return MaterialDocument(
        text=main_text.strip(),
        source_kind="public_url",
        source_title=title,
        source_reference=url,
    )
