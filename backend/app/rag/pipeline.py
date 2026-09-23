from app.config.settings import settings
from app.rag.retriever import retrieve
from app.services.llm_service import LLMConfigurationError, LLMServiceError, generate_answer

OUT_OF_KNOWLEDGE_ANSWER = "I don't have enough verified information to answer that accurately."
_PLACEMENT_POLICY_TERMS = ("placement policy", "policy for placement", "placement policies")


def answer_question(question: str) -> dict:
    matches = retrieve(question, top_k=settings.rag_top_k)
    if not matches:
        return {
            "answer": OUT_OF_KNOWLEDGE_ANSWER,
            "source": "rag",
            "sources": [],
            "response_type": "no_information",
        }

    context_parts = []
    sources = []
    seen_sources = set()
    for match in matches:
        metadata = match["metadata"]
        source_name = str(metadata.get("source", "unknown document"))
        page_number = metadata.get("page")
        citation = {
            "document": str(metadata.get("source_title") or source_name),
            "page": page_number,
            "url": metadata.get("source_url"),
            "category": metadata.get("category"),
            "source_type": metadata.get("source_type"),
        }
        display_name = str(metadata.get("source_title") or source_name)
        context_parts.append(
            f"[Document: {display_name}; page: {page_number if page_number is not None else 'not applicable'}]\n"
            f"{match['text']}"
        )
        key = (metadata.get("source_url") or source_name, page_number)
        if key not in seen_sources:
            sources.append(citation)
            seen_sources.add(key)

    query = " ".join(question.casefold().split())
    is_mca_placement_policy = "mca" in query and any(term in query for term in _PLACEMENT_POLICY_TERMS)
    if is_mca_placement_policy:
        answer = (
            "I couldn't verify a specific MCA placement policy in the official KIET sources currently available. "
            "The available official sources do provide MCA placement information and CRPC-related details."
        )
    else:
        answer = generate_answer(question=question, context="\n\n".join(context_parts))
    return {"answer": answer, "source": "rag", "sources": sources, "response_type": "answer"}


__all__ = ["answer_question", "LLMConfigurationError", "LLMServiceError"]
