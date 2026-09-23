"""Helpers for fetching explicitly approved public KIET pages."""

from datetime import datetime, timezone
from urllib.parse import urlsplit

from app.rag.web_loader import fetch_official_page


def fetch_page(url: str) -> tuple[str, str, str]:
    """Fetch HTML, canonical URL, and UTC retrieval time through RAG's safe loader."""
    html, final_url = fetch_official_page(url)
    if urlsplit(final_url).hostname not in {"www.kiet.edu", "kiet.edu"}:
        raise ValueError("Official source redirected outside kiet.edu")
    return html, final_url, datetime.now(timezone.utc).isoformat()
