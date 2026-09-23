"""Fetch and extract explicitly registered official KIET pages and PDFs."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
from io import BytesIO
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from pypdf import PdfReader

from app.rag.document_loader import Document

USER_AGENT = "KIETInformationAssistantKnowledgeBot/1.0 (curated official source ingestion)"
MAX_BYTES = 20 * 1024 * 1024
_robots_cache: dict[str, RobotFileParser] = {}


def canonicalize_url(url: str) -> str:
    """Normalize a registered URL and reject anything outside kiet.edu."""
    parsed = urlsplit(url.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    if parsed.scheme.lower() != "https" or host not in {"kiet.edu", "www.kiet.edu"}:
        raise ValueError("Only HTTPS URLs on kiet.edu or www.kiet.edu are allowed")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("Credentials and non-standard ports are not allowed")
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    # Tracking and content query parameters are deliberately excluded.
    return urlunsplit(("https", "www.kiet.edu", path, "", ""))


class _AllowedRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        canonicalize_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class _TextExtractor(HTMLParser):
    _ignored = {"script", "style", "noscript", "svg", "nav", "header", "footer", "aside", "form", "button"}
    _breaks = {"address", "article", "blockquote", "br", "dd", "div", "dl", "dt", "h1", "h2", "h3", "h4", "h5", "h6", "li", "main", "ol", "p", "section", "table", "td", "th", "tr", "ul"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ignored_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self._ignored:
            self.ignored_depth += 1
        elif not self.ignored_depth and tag in self._breaks:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in self._ignored and self.ignored_depth:
            self.ignored_depth -= 1
        elif not self.ignored_depth and tag in self._breaks:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.ignored_depth:
            self.parts.append(data)


def extract_html(html: str) -> tuple[str, str | None]:
    """Return a page title and readable text, dropping common site chrome."""
    parser = _TextExtractor()
    parser.feed(html)
    text = "\n".join(
        " ".join(line.split()) for line in "".join(parser.parts).splitlines()
        if line.strip()
    )
    title_parser = _TitleExtractor()
    title_parser.feed(html)
    return text.strip(), title_parser.title.strip() or None


class _TitleExtractor(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_title = False
        self.title = ""

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag):
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def _opener():
    return build_opener(_AllowedRedirectHandler())


def _fetch(url: str, *, robots: bool = False) -> tuple[bytes, str, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/pdf,*/*"})
    with _opener().open(request, timeout=15) as response:
        final_url = canonicalize_url(response.geturl())
        content_type = response.headers.get_content_type()
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Response exceeds 20 MB limit")
    return payload, content_type, final_url


def _check_robots(url: str) -> None:
    parsed = urlsplit(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    if origin not in _robots_cache:
        robots_url = f"{origin}/robots.txt"
        try:
            payload, _, _ = _fetch(robots_url, robots=True)
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            # Fail closed when the robots policy cannot be checked.
            raise RuntimeError(f"Could not verify robots.txt: {exc}") from exc
        parser = RobotFileParser(robots_url)
        parser.parse(payload.decode("utf-8", errors="replace").splitlines())
        _robots_cache[origin] = parser
    if not _robots_cache[origin].can_fetch(USER_AGENT, url):
        raise PermissionError("robots.txt disallows this URL for the ingestion user agent")


def fetch_official_page(url: str) -> tuple[str, str]:
    """Fetch a public, robots-allowed KIET HTML page without adding it to RAG."""
    canonical_url = canonicalize_url(url)
    _check_robots(canonical_url)
    payload, content_type, final_url = _fetch(canonical_url)
    if content_type != "text/html":
        raise ValueError("The official source did not return an HTML page")
    return payload.decode("utf-8", errors="replace"), final_url


def load_web_source(source: dict) -> tuple[list[Document], str, int]:
    """Fetch one registry entry. Returns page documents, content hash, text size."""
    url = canonicalize_url(source["url"])
    _check_robots(url)
    payload, content_type, final_url = _fetch(url)
    fetched_at = datetime.now(timezone.utc).isoformat()
    is_pdf = content_type == "application/pdf" or urlsplit(final_url).path.lower().endswith(".pdf")
    metadata = {
        "source": url,
        "source_url": url,
        "source_title": source["title"],
        "category": source["category"],
        "source_type": "pdf" if is_pdf else "webpage",
        "fetched_at": fetched_at,
    }
    if source.get("programme"):
        metadata["programme"] = str(source["programme"])
    if is_pdf:
        content_hash = sha256(payload).hexdigest()
        reader = PdfReader(BytesIO(payload))
        pdf_title = getattr(reader.metadata, "title", None) if reader.metadata else None
        metadata["page_title"] = pdf_title or source.get("title")
        documents = []
        for page_num, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                documents.append(Document(text, {**metadata, "page": page_num, "content_hash": content_hash}))
        if not documents:
            raise ValueError("PDF has no extractable text")
        return documents, content_hash, sum(len(doc.page_content) for doc in documents)

    html = payload.decode("utf-8", errors="replace")
    text, page_title = extract_html(html)
    if not text:
        raise ValueError("No readable page content was extracted")
    content_hash = sha256(text.encode("utf-8")).hexdigest()
    metadata["source_type"] = "webpage"
    metadata["source_title"] = source.get("title") or page_title or url
    metadata["page_title"] = page_title or source.get("title")
    metadata["content_hash"] = content_hash
    return [Document(text, metadata)], content_hash, len(text)
