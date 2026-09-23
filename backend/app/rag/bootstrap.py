"""Create the curated knowledge index when a fresh runtime has no index."""

import logging

from app.rag.vector_store import get_collection

logger = logging.getLogger(__name__)


def ensure_knowledge_index() -> int:
    """Reuse a populated collection or seed an empty one from the KIET registry.

    This runs during application startup. Chroma and the ONNX model cache share
    VECTOR_DB_PATH, so the existing collection and model are reused whenever
    the runtime filesystem still contains them.
    """
    collection = get_collection()
    existing_count = collection.count()
    if existing_count:
        logger.info("Reusing existing KIET Chroma index (%d chunks)", existing_count)
        return existing_count

    logger.info("KIET Chroma index is empty; ingesting registered official sources")
    # Import only for an empty collection; a normal restart avoids the network
    # ingestion code path entirely.
    from app.rag.web_ingest import ingest

    summary = ingest()
    final_count = get_collection().count()
    if summary["failed"]:
        logger.warning(
            "KIET index initialization finished with %d unavailable source(s); %d chunks are available",
            summary["failed"],
            final_count,
        )
    elif final_count:
        logger.info("KIET index initialization complete (%d chunks)", final_count)
    else:
        logger.warning("KIET index initialization produced no chunks; RAG answers will be unavailable")
    return final_count
