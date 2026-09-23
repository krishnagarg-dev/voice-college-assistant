"""Conservative extraction of clearly labelled records from official HTML."""

from __future__ import annotations

import re
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from app.tools.base import ToolItem

_DATE = re.compile(
    r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2}|"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|"
    r"Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|"
    r"Dec(?:ember)?)\s+\d{1,2},?\s+\d{4})\b",
    re.IGNORECASE,
)


class _RecordParser(HTMLParser):
    """Only reads explicit notice, event, or calendar card containers."""

    CARD_NAMES = {"notice-item", "notice-card", "event-item", "event-card", "calendar-item"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.depth = 0
        self.current: dict | None = None
        self.heading_depth = 0
        self.link_depth = 0
        self.records: list[dict] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set((attrs.get("class") or "").split())
        if self.current is None and classes & self.CARD_NAMES:
            self.current = {"text": [], "title": [], "url": None, "document_url": None}
            self.depth = 1
        elif self.current is not None and tag not in self.VOID_TAGS:
            self.depth += 1
        if self.current is None:
            return
        if tag in {"h1", "h2", "h3", "h4"}:
            self.heading_depth += 1
        if tag == "a":
            href = attrs.get("href")
            if href:
                absolute = urljoin(self.base_url, href)
                parts = urlsplit(absolute)
                if parts.scheme == "https" and parts.hostname in {"www.kiet.edu", "kiet.edu"}:
                    self.current["url"] = absolute
                    if parts.path.lower().endswith(".pdf"):
                        self.current["document_url"] = absolute
            self.link_depth += 1

    def handle_endtag(self, tag):
        if self.current is None:
            return
        if tag in {"h1", "h2", "h3", "h4"} and self.heading_depth:
            self.heading_depth -= 1
        if tag == "a" and self.link_depth:
            self.link_depth -= 1
        self.depth -= 1
        if self.depth <= 0:
            record = self.current
            text = " ".join(" ".join(record["text"]).split())
            title = " ".join(" ".join(record["title"]).split())
            match = _DATE.search(text)
            if title:
                record.update(title=title, date=match.group(0) if match else None)
                self.records.append(record)
            self.current = None
            self.depth = 0

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"].append(data)
            if self.heading_depth:
                self.current["title"].append(data)


def extract_records(html: str, base_url: str) -> list[ToolItem]:
    parser = _RecordParser(base_url)
    parser.feed(html)
    return [ToolItem(**record) for record in parser.records]


def parse_date(value: str) -> date | None:
    for fmt in ("%B %d, %Y", "%b %d, %Y", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None
