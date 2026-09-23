from app.config.settings import settings
from app.rag.chunker import split_documents
from app.rag.document_loader import find_documents, load_documents
from app.rag.vector_store import remove_missing_sources, replace_sources


def main() -> None:
    paths = find_documents(settings.documents_path)
    print(f"Documents found: {len(paths)}")

    documents, errors = load_documents(paths)
    valid_sources = {
        str(document.metadata.get("source"))
        for document in documents
        if document.metadata.get("source")
    }
    remove_missing_sources(valid_sources)

    chunks = split_documents(
        documents,
        chunk_size=settings.rag_chunk_size,
        chunk_overlap=settings.rag_chunk_overlap,
    ) if documents else []

    # Replace file chunks before reporting success. Repeated ingestion remains idempotent.
    stored = replace_sources(chunks, sorted(valid_sources))
    print(f"Documents processed: {len(valid_sources)}")
    print(f"Chunks created: {len(chunks)}")
    print(f"Vectors stored: {stored}")
    for error in errors:
        print(f"Skipped {error['source']}: {error['error']}")


if __name__ == "__main__":
    main()
