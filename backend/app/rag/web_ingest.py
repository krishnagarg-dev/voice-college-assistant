"""Curated, repeatable KIET website ingestion CLI.

Run from the backend directory with: python -m app.rag.web_ingest --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from pathlib import Path

from app.config.settings import settings
from app.rag.chunker import split_documents
from app.rag.vector_store import replace_sources, source_has_content_hash
from app.rag.web_loader import canonicalize_url, load_web_source

logger = logging.getLogger("kiet_web_ingest")
REGISTRY_PATH = settings.backend_dir / "data" / "source_registry.json"


def load_registry(path: Path = REGISTRY_PATH) -> list[dict]:
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Source registry must be a JSON array")
    for entry in entries:
        for field in ("url", "title", "category", "source_type", "enabled"):
            if field not in entry:
                raise ValueError(f"Registry entry is missing required field: {field}")
    return entries


def ingest(*, dry_run: bool = False, refresh: bool = False, category: str | None = None) -> dict[str, int]:
    entries = [entry for entry in load_registry() if entry["enabled"]]
    if category:
        entries = [entry for entry in entries if entry["category"].casefold() == category.casefold()]

    counts = {"successful": 0, "failed": 0, "skipped": 0, "chunks": 0, "unchanged": 0}
    seen: set[str] = set()
    for index, entry in enumerate(entries):
        try:
            canonical_url = canonicalize_url(entry["url"])
            if canonical_url in seen:
                counts["skipped"] += 1
                print(f"SKIP duplicate {canonical_url}")
                continue
            seen.add(canonical_url)
            print(f"FETCH {canonical_url} | {entry['title']} | {entry['category']} | {entry['source_type']}")
            documents, content_hash, text_size = load_web_source(entry)
            print(f"  extracted ~{text_size} characters; title: {entry['title']}")
            counts["successful"] += 1
            if dry_run:
                continue
            if not refresh and source_has_content_hash(canonical_url, content_hash):
                counts["unchanged"] += 1
                print("  unchanged; existing chunks kept")
                continue
            chunks = split_documents(
                documents,
                chunk_size=settings.rag_chunk_size,
                chunk_overlap=settings.rag_chunk_overlap,
            )
            counts["chunks"] += replace_sources(chunks, [canonical_url])
        except Exception as exc:
            counts["failed"] += 1
            logger.error("Failed to ingest registered KIET source %s: %s", entry.get("url"), exc)
            print(f"  FAILED {entry.get('url')}: {exc}")
        if index + 1 < len(entries):
            time.sleep(1.0)

    print("\nIngestion summary")
    print(f"  successful sources: {counts['successful']}")
    print(f"  failed sources: {counts['failed']}")
    print(f"  skipped sources: {counts['skipped']}")
    print(f"  chunks created/updated: {counts['chunks']}")
    print(f"  unchanged sources: {counts['unchanged']}")
    if dry_run:
        print("  dry-run: ChromaDB was not modified")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest curated official KIET pages and PDFs into the existing RAG collection")
    parser.add_argument("--dry-run", action="store_true", help="fetch and extract sources without writing ChromaDB")
    parser.add_argument("--refresh", action="store_true", help="replace stored chunks even when source content is unchanged")
    parser.add_argument("--category", help="only ingest sources in this registry category")
    args = parser.parse_args()
    ingest(dry_run=args.dry_run, refresh=args.refresh, category=args.category)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    main()
