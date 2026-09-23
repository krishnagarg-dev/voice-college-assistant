from app.rag.document_loader import Document


def split_documents(
    documents: list[Document], chunk_size: int, chunk_overlap: int
) -> list[Document]:
    if chunk_size <= 0:
        raise ValueError("RAG_CHUNK_SIZE must be greater than zero.")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("RAG_CHUNK_OVERLAP must be at least zero and smaller than chunk size.")
    chunks = []
    for document in documents:
        text = document.page_content.strip()
        cursor = 0
        while cursor < len(text):
            proposed_end = min(cursor + chunk_size, len(text))
            end = proposed_end
            if proposed_end < len(text):
                # Prefer a paragraph, line, then word boundary in the latter half.
                for separator in ("\n\n", "\n", " "):
                    boundary = text.rfind(separator, cursor + chunk_size // 2, proposed_end)
                    if boundary > cursor:
                        end = boundary
                        break
            chunk_text = text[cursor:end].strip()
            if chunk_text:
                metadata = dict(document.metadata)
                metadata["start_index"] = cursor
                chunks.append(Document(page_content=chunk_text, metadata=metadata))
            if end >= len(text):
                break
            cursor = max(end - chunk_overlap, cursor + 1)
    return chunks
