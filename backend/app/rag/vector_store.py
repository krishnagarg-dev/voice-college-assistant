import hashlib
from typing import Any

import chromadb

from app.config.settings import settings
from app.rag.embeddings import get_embedding_function
from app.rag.document_loader import Document

COLLECTION_NAME = "kiet_knowledge"


def get_collection():
    database_path = settings.vector_db_path
    database_path.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(database_path))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedding_function(),
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_id(document: Document) -> str:
    identity = "\0".join((
        str(document.metadata.get("source", "")),
        str(document.metadata.get("page", "")),
        str(document.metadata.get("start_index", "")),
        document.page_content,
    ))
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


def replace_sources(documents: list[Document], sources: list[str]) -> int:
    """Replace each ingested file's prior chunks, making repeat ingestion safe."""
    collection = get_collection()
    for source in sources:
        collection.delete(where={"source": source})
    if not documents:
        return 0

    ids = [_chunk_id(document) for document in documents]
    texts = [document.page_content for document in documents]
    metadatas = [
        {key: value for key, value in document.metadata.items() if value is not None}
        for document in documents
    ]
    collection.upsert(ids=ids, documents=texts, metadatas=metadatas)
    return len(ids)


def source_has_content_hash(source: str, content_hash: str) -> bool:
    """Return whether a source is already indexed with this exact source hash."""
    collection = get_collection()
    existing = collection.get(where={"source": source}, include=["metadatas"])
    return bool(existing["ids"]) and all(
        (metadata or {}).get("content_hash") == content_hash
        for metadata in existing.get("metadatas", [])
    )


def query_collection(query: str, top_k: int) -> list[dict[str, Any]]:
    collection = get_collection()
    if collection.count() == 0:
        return []
    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )
    matches: list[dict[str, Any]] = []
    for text, metadata, distance in zip(
        result["documents"][0],
        result["metadatas"][0],
        result["distances"][0],
    ):
        matches.append({"text": text, "metadata": metadata or {}, "distance": distance})
    return matches


def remove_missing_sources(present_sources: set[str]) -> None:
    """Remove stale local files without deleting separately ingested web sources."""
    collection = get_collection()
    existing = collection.get(include=["metadatas"])
    stale_ids = [
        item_id for item_id, metadata in zip(existing["ids"], existing["metadatas"])
        if (metadata or {}).get("source") not in present_sources
        and (metadata or {}).get("source_type") in (None, "file")
    ]
    if stale_ids:
        collection.delete(ids=stale_ids)
